"""January/February-shaped synthetic records; all financial values are invented."""
import csv
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from threading import Event

import pytest
from report_samples import REPAIR_HEADERS, csv_bytes, repair_csv, service_csv, tma_xlsx
from equipment_data_manager.processing.models import ProcessingRequest, ReportType, ProcessingError
from equipment_data_manager.processing.repair_financial import (
    RepairFinancialCleaner, SUMMARY_COLUMNS, money, powerbi_coordinator, read_summary, schema, summary_name,
)
from equipment_data_manager.processing.cleaners import LegacyCsvCleaner
from equipment_data_manager.processing.powerbi import powerbi_coordinator as v1
from equipment_data_manager.powerquery_contract import read_table, read_folder
from equipment_data_manager.monthly import Workspace, export_review_packet
from equipment_data_manager.powerbi_pilot import assemble, validate_snapshot, baseline_template, reconcile


def raw_report(month=1, count=3, costs=None, reported_total=None, labor='5.00', parts='25.00', group_values=None):
    costs = ['$10.00'] * count if costs is None else costs
    reported_total = '30.00' if reported_total is None else reported_total
    rows = []
    for i, cost in enumerate(costs):
        rows.append(['Synthetic Account', 'Equip. Name: Synthetic Machine', 'Equipment Id: 000439',
            'Service Vendor: Synthetic Vendor', 'Location: Synthetic Room', f'{month}/15/2026',
            cost, 'Synthetic repair, repeated legitimately', '2 hours',
            cost if group_values is None else group_values[i], f'Total Labor: ${labor}',
            f'Total Parts: ${parts}', f'Total Cost: ${reported_total}', f'# of Repairs: {count}'])
    return csv_bytes(REPAIR_HEADERS, rows)


def clean(raw, month=1):
    return RepairFinancialCleaner(LegacyCsvCleaner('repairs')).clean(raw, source_name='synthetic.csv', period=f'2026-{month:02d}')


def records(result):
    return list(csv.DictReader(StringIO(result.output_bytes.decode())))


@pytest.mark.parametrize('month,count,total,labor,parts', [(1,29,'290.00','90.00','200.00'),(2,5,'50.00','15.00','35.00')])
def test_synthetic_monthly_aggregates_reconcile_without_allocating_source_costs(month,count,total,labor,parts):
    # Completely invented line values, not reconstructions of departmental rows.
    costs = ['$10.00'] * (count-1) + [str(Decimal(total)-Decimal(10)*(count-1))]
    raw = raw_report(month,count,costs,total,labor,parts)
    result = clean(raw,month)
    rows = records(result)
    summary = read_summary(result.supplemental_outputs[0][1])
    assert len(rows) == count and len({r['RecordId'] for r in rows}) == count
    assert summary['ReconciliationStatus'] == 'arithmetic_match'
    assert summary['ReportedTotalCost'] == Decimal(total)
    assert summary['ReportedLaborCost'] == Decimal(labor)
    assert summary['ReportedPartsCost'] == Decimal(parts)
    assert summary['ReportedRepairCount'] == count
    assert summary['RepairTotalDifference'] == summary['SummaryComponentsDifference'] == 0
    assert sum(Decimal(r['ReportedTotalCost']) for r in rows) == Decimal(total)
    assert all(r['EquipmentId'] == '000439' and r['SchemaVersion'] == '2' for r in rows)
    assert all(Decimal(r['EstimatedLaborCost']) == Decimal(r['LegacyLaborCost']) == 25 for r in rows)
    assert not {'PartsCost','LaborCost','EstimatedTotalCost','RawPartsCost'} & set(rows[0])
    assert summary['SourceFileSHA256'] == sha256(raw).hexdigest()
    assert {r['FinancialSummarySHA256'] for r in rows} == {sha256(result.supplemental_outputs[0][1]).hexdigest()}
    assert 'CandidateUnverified' == summary['ValidationStatus']
    assert all(r['RawTextbox38'] == r['RawTextbox16'] for r in rows)


def test_grouped_unequal_fields_are_not_guessed_or_deduplicated():
    result = clean(raw_report(costs=['$10.00','$20.00','$0.00'], group_values=['$30.00','$30.00','$0.00']))
    rows = records(result)
    assert len(rows) == 3
    assert [r['ReportedTotalCost'] for r in rows] == ['', '', '0.00']
    assert [r['ReportedTotalCostStatus'] for r in rows] == ['field_relationship_unverified']*2 + ['source_fields_agree']
    summary = read_summary(result.supplemental_outputs[0][1])
    assert summary['UnavailableRepairCostCount'] == 2
    assert summary['RepairTotalDifference'] is None
    assert summary['ReconciliationStatus'] == 'incomplete_repair_costs_or_excluded_records'
    assert rows[0]['RawTextbox16'] == '$30.00' and rows[0]['RawTextbox38'] == '$10.00'


@pytest.mark.parametrize('value', ['', 'not-money', '$1,2.00', 'NaN'])
def test_missing_or_malformed_cost_remains_unknown(value):
    result = clean(raw_report(costs=[value,'$10.00','$20.00']))
    assert records(result)[0]['ReportedTotalCost'] == ''
    summary = read_summary(result.supplemental_outputs[0][1])
    assert summary['UnavailableRepairCostCount'] == 1
    assert summary['RepairTotalDifference'] is None
    assert summary['KnownRepairTotalCost'] == 30


def test_zero_repeated_transactions_are_kept_and_repeated_summaries_count_once():
    result = clean(raw_report(costs=['$0.00']*3, reported_total='0.00',labor='0.00',parts='0.00'))
    assert len(records(result)) == 3
    summary = read_summary(result.supplemental_outputs[0][1])
    assert summary['ReconciliationStatus'] == 'arithmetic_match'
    assert summary['KnownRepairTotalCost'] == 0
    assert summary['UnavailableRepairCostCount'] == 0


@pytest.mark.parametrize('total,labor,parts', [('31.00','5.00','26.00'), ('30.00','6.00','25.00')])
def test_discrepancies_flag_without_changing_values(total,labor,parts):
    result = clean(raw_report(reported_total=total,labor=labor,parts=parts))
    summary = read_summary(result.supplemental_outputs[0][1])
    assert summary['ReconciliationStatus'] == 'difference'
    assert sum(Decimal(r['ReportedTotalCost']) for r in records(result)) == 30
    assert summary['ReportedTotalCost'] == Decimal(total)


def test_excluded_rows_prevent_full_month_reconciliation():
    raw = raw_report().replace(b'1/15/2026',b'invalid',1)
    result = clean(raw)
    summary = read_summary(result.supplemental_outputs[0][1])
    assert result.output_rows == 2 and summary['SourceRecordCount'] == 3
    assert summary['RetainedRepairCount'] == 2 and summary['RepairTotalDifference'] is None
    assert summary['ReconciliationStatus'] == 'incomplete_repair_costs_or_excluded_records'


def test_unverified_flat_layout_preserves_legacy_but_does_not_assert_source_cost():
    raw = Path('tests/fixtures/synthetic/repairs_input.csv').read_bytes()
    result = clean(raw,9)
    assert {r['ReportedTotalCostStatus'] for r in records(result)} == {'layout_unverified'}
    assert read_summary(result.supplemental_outputs[0][1])['ReconciliationStatus'] == 'source_summary_unavailable'
    assert read_summary(result.supplemental_outputs[0][1])['KnownRepairTotalCost'] is None
    assert 'Known reported repair total' not in {m.name for m in result.reconciliation_metrics}


def test_legacy_output_unchanged_and_v1_upgrade_requires_review(tmp_path):
    from equipment_data_manager.processing.coordinator import ProcessingCoordinator
    raw = raw_report()
    request = ProcessingRequest('repairs','2026-01',raw_bytes=raw,source_name='raw.csv')
    old = ProcessingCoordinator(tmp_path/'legacy').process(request)
    prior = v1(tmp_path/'out').process(request)
    engine = powerbi_coordinator(tmp_path/'out')
    review = engine.preview(request)
    assert review.status == 'needs_review'
    assert engine.process(request).status == 'needs_review'
    result = engine.process(replace(request,replacement_token=review.replacement_token))
    assert result.status == 'success'
    assert old.output_location.read_bytes() == old.cleaned.output_bytes
    assert prior.output_location.read_bytes() == prior.cleaned.output_bytes
    assert engine.process(request).status == 'skipped'
    for oldrow,newrow in zip(records(prior.cleaned),records(result.cleaned)):
        assert newrow['LegacyPartsCost'] == oldrow['LegacyPartsCost']
        assert newrow['LegacyEstimatedTotalCost'] == oldrow['LegacyEstimatedTotalCost']
        assert newrow['LegacyLaborCost'] == newrow['EstimatedLaborCost'] == oldrow['LaborCost']
        assert newrow['Description'] == oldrow['Description']
        assert newrow['CompletedDate'] == oldrow['CompletedDate']


def test_preview_is_write_free_and_missing_or_tampered_summary_blocks_skip(tmp_path):
    request = ProcessingRequest('repairs','2026-01',raw_bytes=raw_report(),source_name='raw.csv')
    engine = powerbi_coordinator(tmp_path/'out')
    assert engine.preview(request).status == 'success'
    assert not (tmp_path/'out').exists()
    saved = engine.process(request)
    summary = saved.output_location.parent / summary_name('2026-01')
    original = summary.read_bytes()
    summary.write_bytes(b'tampered')
    assert engine.process(request).code == 'financial_summary_hash_mismatch'
    summary.write_bytes(original)
    summary.unlink()
    assert engine.process(request).code == 'financial_summary_missing_or_unreadable'


def test_failed_summary_write_keeps_prior_selection(tmp_path,monkeypatch):
    engine = powerbi_coordinator(tmp_path/'out')
    request = ProcessingRequest('repairs','2026-01',raw_bytes=raw_report(),source_name='raw.csv')
    first = engine.process(request)
    changed = replace(request,raw_bytes=raw_report(reported_total='31.00'))
    review = engine.preview(changed)
    real = Path.open
    def fail(path,*args,**kwargs):
        if path.name.endswith('Summary_2026-01.csv.part'):
            raise OSError('synthetic failure')
        return real(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',fail)
    failed = engine.process(replace(changed,replacement_token=review.replacement_token))
    assert failed.status == 'failure'
    assert engine.process(request).artifact == first.artifact
    assert len(engine.store.history()) == 1


def test_v2_packet_and_multi_month_pilot_keep_summary_separate(tmp_path):
    workspace = Workspace(tmp_path/'raw',tmp_path/'out',tmp_path/'approved')
    engine = powerbi_coordinator(workspace.candidate_folder)
    packets = []
    for month in (1,2):
        period = f'2026-{month:02d}'
        for kind,raw,name in [('repairs',raw_report(month),'r.csv'),('service_orders',service_csv(month,3),'s.csv'),
                              ('tma_work_orders',tma_xlsx(month,3),'t.xlsx')]:
            assert engine.process(ProcessingRequest(kind,period,raw_bytes=raw,source_name=name)).status == 'success'
        packet = export_review_packet(workspace,engine,period)
        assert len(json.loads((packet/'packet.json').read_text())['supplemental_files']) == 1
        packets.append(packet)
    snapshot = assemble(packets,['2026-01','2026-02'],tmp_path/'pilot')
    rows = validate_snapshot(snapshot)
    assert len(rows[ReportType.REPAIRS]) == 6
    assert len(list((snapshot/'tables/repair_financial_summary').glob('*.csv'))) == 2
    baseline = tmp_path/'baseline.csv'
    baseline_template(snapshot,baseline)
    report = reconcile(snapshot,baseline)
    assert 'reported_total_cost' in {r['metric'] for r in report}
    assert 'parts_cost' not in {r['metric'] for r in report if r['report_type']=='repairs'}
    path = next((snapshot/'tables/repair_financial_summary').glob('*.csv'))
    path.write_bytes(b'changed')
    with pytest.raises(ProcessingError,match='summary_hash_mismatch'):
        validate_snapshot(snapshot)
    assert not workspace.approved_folder.exists()


def test_desktop_and_cli_default_to_v2_and_explicit_v1_remains_available(tmp_path,capsys):
    from equipment_data_manager.__main__ import main
    from equipment_data_manager.ui.workflow import DesktopWorkflow
    workflow = DesktopWorkflow(tmp_path/'out',output_format='powerbi')
    request = ProcessingRequest('repairs','2026-01',raw_bytes=raw_report(),source_name='raw.csv')
    result = workflow.coordinator.preview(request)
    assert records(result.cleaned)[0]['SchemaVersion'] == '2'
    source = tmp_path/'raw.csv';source.write_bytes(raw_report())
    args = ['process',str(source),'--report-type','repairs','--period','2026-01','--output-dir',str(tmp_path/'cli')]
    assert main(args+['--output-format','powerbi']) == 0
    result = json.loads(capsys.readouterr().out)[0]
    assert len(result['supplemental_output_locations']) == 1
    assert Path(result['supplemental_output_locations'][0]).exists()
    assert main(args+['--output-format','powerbi-v1','--output-dir',str(tmp_path/'v1')]) == 0
    result = json.loads(capsys.readouterr().out)[0]
    assert result['supplemental_output_locations'] == []
    assert next(csv.DictReader(Path(result['output_location']).open()))['SchemaVersion']=='1'


def test_m_v2_schema_control_metrics_and_summary_grain_are_exact():
    from equipment_data_manager.powerbi_pilot import REPAIR_V2_METRICS
    function = Path('powerquery/fnReadMonthlyFolderV2.pq').read_text()
    for c in schema():
        assert '{"'+c.name+'", "'+c.data_type+'"}' in function
    for c in SUMMARY_COLUMNS:
        assert '{"'+c+'", ' in function
    assert 'if Summary then Table.RowCount(Typed) = 1' in function
    assert 'if Summary then Complete' in function
    assert 'Folder.Files(' not in function and 'Folder.Contents(' in function
    controls = Path('powerquery/fnMonthlyControlTotalsV2.pq').read_text()
    for name,column in REPAIR_V2_METRICS.items():
        assert '{"'+name+'", '+('null' if column is None else '"'+column+'"')+'}' in controls


def test_malformed_summary_or_mixed_repair_schema_versions_rejected(tmp_path):
    result = clean(raw_report())
    rows = list(csv.reader(StringIO(result.supplemental_outputs[0][1].decode())))
    rows[1][rows[0].index('ReportedTotalCost')] = 'NaN'
    stream = StringIO();csv.writer(stream).writerows(rows)
    with pytest.raises(ProcessingError,match='contract_rejected'):
        read_summary(stream.getvalue().encode())
    folder = tmp_path/'mixed';folder.mkdir()
    (folder/'jan.csv').write_bytes(result.output_bytes)
    legacy = v1(tmp_path/'old').process(ProcessingRequest('repairs','2026-02',raw_bytes=raw_report(2),source_name='raw.csv'))
    (folder/'feb.csv').write_bytes(legacy.cleaned.output_bytes)
    with pytest.raises(ProcessingError,match='mixed_schema_versions'):
        read_folder(folder,ReportType.REPAIRS,allow_candidates=True)
