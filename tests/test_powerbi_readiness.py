"""Milestone A fixtures are entirely synthetic; no departmental amounts or records."""
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_repair_financial import raw_report
from report_samples import service_csv, tma_xlsx
from equipment_data_manager.monthly import Workspace, export_review_packet
from equipment_data_manager.powerbi_pilot import assemble, read_snapshot, validate_snapshot
from equipment_data_manager.powerbi_readiness import (
    EXPECTATION_COLUMNS, SOURCE_COLUMNS, assess, template, write_assessment,
)
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest, ReportType
from equipment_data_manager.processing.repair_financial import powerbi_coordinator

MONTHS = ['2026-01', '2026-02']
# Independently stated truths for three invented $10 repairs/month, not observed-data autofill.
EXPECTED = {'repairs': {'record_count': '3', 'reported_total_cost': '30', 'missing_reported_cost_count': '0'},
    'service_orders': {'record_count': '3'}, 'tma_work_orders': {'record_count': '3'},
    'repair_financial_summary': {'reported_repair_count': '3', 'reported_parts_cost': '25',
                                'reported_labor_cost': '5', 'reported_total_cost': '30'}}


def csv_write(path, columns, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader(); writer.writerows(rows)


def build(tmp_path, *, v1=False, raw_factory=raw_report, service_factory=service_csv):
    workspace = Workspace(tmp_path/'raw',tmp_path/'candidates',tmp_path/'reserved-approved')
    if v1:
        from equipment_data_manager.processing.powerbi import powerbi_coordinator as factory
    else:
        factory = powerbi_coordinator
    engine = factory(workspace.candidate_folder)
    packets, sources = [], []
    for month,period in enumerate(MONTHS,1):
        for kind,raw,ext in [('repairs',raw_factory(month),'csv'),('service_orders',service_factory(month,3),'csv'),
                             ('tma_work_orders',tma_xlsx(month,3),'xlsx')]:
            path = workspace.raw_folder/period/kind/f'raw.{ext}'
            path.parent.mkdir(parents=True);path.write_bytes(raw)
            result = engine.process(ProcessingRequest(kind,period,input_path=path))
            assert result.status == 'success'
            sources.append(dict(report_type=kind,period=period,path=str(path.relative_to(tmp_path))))
        packets.append(export_review_packet(workspace,engine,period))
    snapshot = assemble(packets,MONTHS,tmp_path/'pilot')
    index = tmp_path/'sources.csv';csv_write(index,SOURCE_COLUMNS,sources)
    baseline = tmp_path/'expectations.csv'
    rows = [dict(period=period,report_type=kind,metric=metric,
                 expected=str(int(value)*(2 if period=='ALL' else 1)),tolerance='0',evidence='Invented independent fixture')
            for period in [*MONTHS,'ALL'] for kind,metrics in EXPECTED.items() for metric,value in metrics.items()]
    csv_write(baseline,EXPECTATION_COLUMNS,rows)
    return workspace,snapshot,index,baseline,packets


@pytest.fixture
def ready(tmp_path):
    return build(tmp_path)


def test_complete_four_table_assessment_and_independent_monthly_combined_expectations(ready,tmp_path):
    workspace,snapshot,index,baseline,_ = ready
    before = {p:p.read_bytes() for p in snapshot.rglob('*') if p.is_file()}
    review = assess(snapshot,MONTHS,expectations=baseline,source_index=index)
    assert review.status['structural_checks_passed']
    assert review.status['reported_financials_reconcile'] and review.status['expected_totals_match']
    assert review.status['source_bytes_verified']
    assert review.status['production_ready'] is review.status['approval_record_created'] is False
    assert review.status['requires_manual_power_bi_test'] is True
    assert len(review.files)==8 and len(review.sources)==6
    lookup = {(r['period'],r['report_type'],r['metric']):r for r in review.controls}
    assert lookup['ALL','repairs','record_count']['value']==6
    assert lookup['ALL','repairs','reported_total_cost']['value']==60
    assert lookup['ALL','repair_financial_summary','reported_parts_cost']['value']==50
    assert lookup['ALL','repair_financial_summary','reported_labor_cost']['value']==10
    assert lookup['2026-01','repairs','leading_zero_identifier_count']['value']==3
    assert lookup['2026-01','tma_work_orders','leading_zero_identifier_count']['value']==3
    write_assessment(review,snapshot,tmp_path/'private-report')
    assert (tmp_path/'private-report/comparisons.csv').exists()
    assert before=={p:p.read_bytes() for p in before}
    assert not workspace.approved_folder.exists()
    assert 'controls=' not in repr(review) and 'source_sha256=' not in repr(review)


def test_blank_observations_and_optional_raw_bytes_are_not_claimed_verified(ready,tmp_path):
    _,snapshot,_,_,_ = ready
    blank = tmp_path/'blank.csv';template(snapshot,MONTHS,blank)
    review = assess(snapshot,MONTHS,expectations=blank)
    assert not review.status['expected_totals_match'] and not review.status['source_bytes_verified']
    assert {r['comparison'] for r in review.comparisons}=={'not_supplied'}
    assert {r['source_integrity'] for r in review.sources}=={'raw_bytes_not_supplied'}
    with pytest.raises(FileExistsError):template(snapshot,MONTHS,blank)
    with pytest.raises(ProcessingError,match='outside_snapshot'):
        template(snapshot,MONTHS,snapshot/'observations.csv')


def test_schema_v1_is_compatible_but_explicit_readiness_requires_v2(tmp_path):
    _,snapshot,_,_,packets = build(tmp_path,v1=True)
    assert validate_snapshot(snapshot)
    with pytest.raises(ProcessingError,match='requires_repair_schema_v2'):
        assess(snapshot,MONTHS)
    target = tmp_path/'v2-only'
    with pytest.raises(ProcessingError,match='requires_repair_schema_v2'):
        assemble(packets,MONTHS,target,require_repair_v2=True)
    assert not target.exists()


@pytest.mark.parametrize('periods', [['2026-01'], ['2026-01','2026-03'], ['2026-01','2026-01']])
def test_missing_unexpected_or_duplicate_periods_fail_closed(ready,periods):
    with pytest.raises(ProcessingError):assess(ready[1],periods)


def rewrite_main(snapshot, change, period='2026-01'):
    path = next((snapshot/'tables/repairs').glob(f'*_{period}.csv'))
    rows = list(csv.DictReader(StringIO(path.read_text())))
    change(rows)
    csv_write(path,list(rows[0]),rows)
    manifest = snapshot/'snapshot.json';data=json.loads(manifest.read_text())
    for entry in data['files']:
        if entry['file']=='repairs/'+path.name:entry['sha256']=sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(data))


def rewrite_summary(snapshot, change):
    path = next((snapshot/'tables/repair_financial_summary').glob('*_2026-01.csv'))
    rows = list(csv.DictReader(StringIO(path.read_text())));change(rows[0])
    csv_write(path,list(rows[0]),rows)
    digest = sha256(path.read_bytes()).hexdigest()
    rewrite_main(snapshot,lambda rows:[r.update(FinancialSummarySHA256=digest) for r in rows])
    manifest=snapshot/'snapshot.json';data=json.loads(manifest.read_text())
    for entry in data['financial_summaries']:
        if entry['period']=='2026-01':entry['sha256']=digest
    manifest.write_text(json.dumps(data))


@pytest.mark.parametrize('change', [dict(ReportedTotalCost='31'),dict(KnownRepairTotalCost='99'),
    dict(RetainedRepairCount='9'),dict(UnavailableRepairCostCount='1'),dict(RepairTotalDifference='8'),
    dict(SummaryComponentsDifference='1'),dict(ReconciliationStatus='source_summary_unavailable')])
def test_self_consistent_file_hashes_do_not_make_false_financial_controls_true(ready,change):
    snapshot=ready[1];rewrite_summary(snapshot,lambda row:row.update(change))
    assert validate_snapshot(snapshot)  # Structurally intact but semantically inconsistent.
    with pytest.raises(ProcessingError,match='financial_summary_inconsistent'):
        assess(snapshot,MONTHS)


@pytest.mark.parametrize('change', [dict(SourceFileSHA256='0'*64),dict(SourceFileName='different.csv'),
    dict(CandidateRecordNumber='99'),dict(RecordId='invalid-hash')])
def test_row_provenance_and_occurrence_metadata_must_be_consistent(ready,change):
    snapshot=ready[1];rewrite_main(snapshot,lambda rows:rows[1].update(change))
    with pytest.raises(ProcessingError,match='source_provenance_rejected'):
        assess(snapshot,MONTHS)


def test_summary_selected_revision_must_match_fact_revision(ready):
    snapshot=ready[1];path=snapshot/'snapshot.json';data=json.loads(path.read_text())
    data['financial_summaries'][0]['revision']='0'*32;path.write_text(json.dumps(data))
    with pytest.raises(ProcessingError,match='summary_revision_mismatch'):assess(snapshot,MONTHS)


def test_snapshot_data_is_parsed_once_from_hash_checked_bytes(ready,monkeypatch):
    snapshot=ready[1];calls={p:0 for p in (snapshot/'tables').rglob('*.csv')}
    original=Path.read_bytes
    def read(path):
        if path in calls:calls[path]+=1
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',read)
    assess(snapshot,MONTHS)
    assert set(calls.values())=={1}


@pytest.mark.parametrize('problem', ['changed','missing','duplicate','incomplete','bad_header'])
def test_original_file_and_source_index_failures_are_explicit(ready,problem):
    workspace,snapshot,index,baseline,_=ready
    rows=list(csv.DictReader(index.open()))
    if problem in ('changed','missing'):
        source=workspace.raw_folder/'2026-01/repairs/raw.csv'
        if problem=='changed':source.write_bytes(b'changed')
        else:source.unlink()
    elif problem=='duplicate':rows.append(rows[0]);csv_write(index,SOURCE_COLUMNS,rows)
    elif problem=='incomplete':csv_write(index,SOURCE_COLUMNS,rows[:-1])
    else:index.write_text('wrong\n')
    with pytest.raises(ProcessingError):assess(snapshot,MONTHS,source_index=index,expectations=baseline)


@pytest.mark.parametrize('changes', [dict(expected='NaN'),dict(tolerance='-1'),dict(expected='1',evidence=''),
    dict(metric='unknown'),dict(period='2026-03')])
def test_invalid_observations_fail_instead_of_becoming_unknown(ready,changes):
    _,snapshot,_,baseline,_=ready
    rows=list(csv.DictReader(baseline.open()));rows[0].update(changes)
    csv_write(baseline,EXPECTATION_COLUMNS,rows)
    with pytest.raises(ProcessingError,match='expectations_rejected'):
        assess(snapshot,MONTHS,expectations=baseline)


def test_monthly_and_combined_disagreements_and_missing_values_stay_visible(ready):
    _,snapshot,_,baseline,_=ready
    rows=list(csv.DictReader(baseline.open()));rows[0]['expected']='4'
    rows[-1]['expected']='61';csv_write(baseline,EXPECTATION_COLUMNS,rows)
    review=assess(snapshot,MONTHS,expectations=baseline)
    assert not review.status['expected_totals_match']
    assert sum(r['comparison']=='difference' for r in review.comparisons)==2


@pytest.mark.parametrize('incomplete', [False,True])
def test_valid_financial_difference_or_missing_amount_produces_review_not_approval(tmp_path,incomplete):
    factory=(lambda m:raw_report(m,costs=['','$10.00','$20.00'])) if incomplete else (
        lambda m:raw_report(m,reported_total='31.00',parts='26.00'))
    _,snapshot,_,baseline,_=build(tmp_path,raw_factory=factory)
    review=assess(snapshot,MONTHS,expectations=baseline)
    assert not review.status['reported_financials_reconcile']
    assert review.status['validation_status']=='CandidateUnverified'
    assert review.status['production_ready'] is False
    if incomplete:
        assert any(r['comparison']=='missing_values' for r in review.comparisons)


def test_reports_are_exclusive_outside_snapshot_and_cleanup_failed_writes(ready,tmp_path,monkeypatch):
    snapshot=ready[1];review=assess(snapshot,MONTHS)
    with pytest.raises(ProcessingError):write_assessment(review,snapshot,snapshot/'report')
    alias=snapshot.parent/'unrelated'/'..'/snapshot.name/'alias-report'
    with pytest.raises(ProcessingError):write_assessment(review,snapshot,alias)
    assert not (snapshot/'alias-report').exists() and not (snapshot.parent/'unrelated').exists()
    target=tmp_path/'report';write_assessment(review,snapshot,target)
    before={p:p.read_bytes() for p in target.iterdir()}
    with pytest.raises(FileExistsError):write_assessment(review,snapshot,target)
    assert before=={p:p.read_bytes() for p in before}
    original=Path.write_text
    def fail(path,*args,**kwargs):
        if path.name=='assessment.json':raise OSError('synthetic full disk')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',fail)
    with pytest.raises(OSError):write_assessment(review,snapshot,tmp_path/'failed-report')
    assert not (tmp_path/'failed-report').exists()


def test_cli_exit_codes_and_no_financial_values_in_stdout(ready,tmp_path):
    _,snapshot,index,baseline,_=ready
    command=[sys.executable,'-m','equipment_data_manager.powerbi_readiness','assess',str(snapshot),
             '--month','2026-01','--month','2026-02']
    success=subprocess.run([*command,'--expectations',str(baseline),'--sources',str(index),
        '--output',str(tmp_path/'successful')],capture_output=True,text=True)
    assert success.returncode==0 and 'remain unapproved' in success.stdout
    assert '30' not in success.stdout and '000439' not in success.stdout
    pending=subprocess.run([*command,'--output',str(tmp_path/'pending')],capture_output=True,text=True)
    assert pending.returncode==2 and (tmp_path/'pending/assessment.json').exists()
    rejected=subprocess.run([*command,'--output',str(snapshot/'report')],capture_output=True,text=True)
    assert rejected.returncode==1 and not (snapshot/'report').exists()


def test_power_query_v2_uses_shared_periods_and_aggregates_before_summary_join():
    for file in ['PilotRepairsV2.pq','PilotRepairFinancialSummary.pq','PilotServiceOrdersV2.pq','PilotTmaWorkOrdersV2.pq']:
        assert 'true, PilotMonths)' in (Path('powerquery')/file).read_text()
    text=Path('powerquery/PilotReconciliationV2.pq').read_text()
    assert text.index('Table.Group(PilotRepairsV2') < text.index('Table.NestedJoin(Repairs')
    assert 'CalculatedRepairTotalDifference' in text and 'CandidateUnverified' in text
    assert 'EstimatedLaborCost' in text  # separate estimate, never added to reported total


def test_january_february_record_shape_with_independently_invented_finances(tmp_path):
    def factory(month):
        count=29 if month==1 else 5
        return raw_report(month,count,reported_total=str(count*10)+'.00',
                          labor=str(count*2)+'.00',parts=str(count*8)+'.00')
    _,snapshot,_,baseline,_=build(tmp_path,raw_factory=factory)
    amounts={'2026-01': {'count':'29','cost':'290','parts':'232','labor':'58'},
             '2026-02': {'count':'5','cost':'50','parts':'40','labor':'10'},
             'ALL': {'count':'34','cost':'340','parts':'272','labor':'68'}}
    rows=list(csv.DictReader(baseline.open()))
    for row in rows:
        values=amounts[row['period']]
        if row['report_type']=='repairs':
            row['expected']={'record_count':values['count'],'reported_total_cost':values['cost'],
                             'missing_reported_cost_count':'0'}[row['metric']]
        elif row['report_type']=='repair_financial_summary':
            row['expected']={'reported_repair_count':values['count'],'reported_parts_cost':values['parts'],
                             'reported_labor_cost':values['labor'],'reported_total_cost':values['cost']}[row['metric']]
    csv_write(baseline,EXPECTATION_COLUMNS,rows)
    review=assess(snapshot,MONTHS,expectations=baseline)
    assert review.status['reported_financials_reconcile'] and review.status['expected_totals_match']
    assert next(r['value'] for r in review.controls if r['period']=='ALL' and r['report_type']=='repairs'
                and r['metric']=='record_count')==34


def test_complete_synthetic_walkthrough_is_reproducible_and_not_an_approval(tmp_path):
    from test_powerbi_pilot import demo
    root=tmp_path/'complete-demo'
    snapshot=demo.create_demo(root,financial_v2=True,complete_financial=True)
    report=json.loads((root/'readiness-report/assessment.json').read_text())
    assert report['reported_financials_reconcile'] and report['expected_totals_match'] and report['source_bytes_verified']
    assert report['production_ready'] is False
    review=assess(snapshot,MONTHS,expectations=root/'readiness-expectations.csv',source_index=root/'source-index.csv')
    assert all(r['comparison']=='arithmetic_match' for r in review.comparisons)


@pytest.mark.parametrize('changes', [dict(CompletedDate='2026-03-15'),
    dict(RawTextbox38='$11.00'),dict(RawTextbox16='$30.00'),
    dict(ReportedTotalCostStatus='field_relationship_unverified')])
def test_existing_record_date_and_source_cost_contracts_are_checked_without_recleaning(ready,changes):
    snapshot=ready[1];rewrite_main(snapshot,lambda rows:rows[1].update(changes))
    with pytest.raises(ProcessingError,match='readiness_(record_period|reported_cost_contract)_rejected'):
        assess(snapshot,MONTHS)


def test_existing_cross_month_service_completed_or_scheduled_rule_remains_valid(tmp_path):
    def service(month,count):
        raw=service_csv(month,count)
        earlier=b'12/31/2025' if month==1 else b'1/31/2026'
        return raw.replace(f'{month}/15/2026'.encode(),earlier)
    _,snapshot,_,baseline,_=build(tmp_path,service_factory=service)
    review=assess(snapshot,MONTHS,expectations=baseline)
    assert review.status['expected_totals_match']


def test_assembly_destination_alias_cannot_create_outputs_inside_source_packet(ready):
    packet=ready[4][0]
    alias=packet.parent/'unrelated'/'..'/packet.name/'side-output'
    with pytest.raises(ProcessingError,match='destination_overlaps_packets'):
        assemble(ready[4],MONTHS,alias,require_repair_v2=True)
    assert not (packet/'side-output').exists() and not (packet.parent/'unrelated').exists()
