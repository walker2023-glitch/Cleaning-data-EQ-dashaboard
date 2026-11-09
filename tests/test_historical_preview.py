"""Synthetic read-only batch orchestration: real adapters, no departmental data."""
import csv
from dataclasses import replace
from io import StringIO
import json
from pathlib import Path
from threading import Event

import pytest

from report_samples import csv_bytes, REPAIR_HEADERS, service_csv, tma_xlsx
from test_repair_financial import raw_report
from test_historical_discovery import populate, snapshot
from equipment_data_manager.historical import discover_history
from equipment_data_manager.historical_preview import preview_history, export_preview, EXPORT_COLUMNS, month_status
from equipment_data_manager.processing.models import ProcessingRequest, ProcessingError, ReportType
from equipment_data_manager.processing.repair_financial import powerbi_coordinator
from equipment_data_manager.storage.local import LocalFolderStorage


def setup(root, months=(1,), layout='sharepoint_year_month'):
    import calendar
    for month in months:
        folder = populate(root, f'2026-{month:02d}', calendar.month_name[month], layout, valid=True)
        path = folder / 'repairs' if layout == 'standard' else folder
        (path / 'CompuClean Repair Report.csv').write_bytes(raw_report(month))


def run(root, output, start='2026-01', end=None, layout='sharepoint_year_month', **kwargs):
    provider = LocalFolderStorage(root)
    inventory = discover_history(provider, start, end or start, layout)
    return preview_history(provider, inventory, output, **kwargs)


@pytest.mark.parametrize('layout', ['standard', 'sharepoint_year_month'])
@pytest.mark.parametrize('months', [(1,), (1,2,3,4,5,6)])
def test_real_adapter_multi_month_preview_never_writes(tmp_path, layout, months, monkeypatch):
    root, output = tmp_path/'raw', tmp_path/'candidates'
    setup(root, months, layout)
    before = snapshot(tmp_path)
    from equipment_data_manager.processing.coordinator import ProcessingCoordinator
    monkeypatch.setattr(ProcessingCoordinator, 'process', lambda *_: pytest.fail('write API'))
    from equipment_data_manager.processing.manifest import LocalOutputStore
    monkeypatch.setattr(LocalOutputStore, 'transaction', lambda *_: pytest.fail('write transaction'))
    events = []
    result = run(root, output, end=f'2026-{max(months):02d}', layout=layout, on_result=events.append)
    assert len(result.reports) == len(months)*3 and tuple(events) == result.reports
    assert all(r.status in ('previewed','warnings') for r in result.reports)
    assert [r.retained_records for r in result.reports[:3]] == [3,2,2]
    financial = dict(result.reports[0].financial)
    assert financial['ReportedTotalCost'] == '30.00' and financial['ReconciliationStatus'] == 'arithmetic_match'
    assert snapshot(tmp_path) == before and not output.exists()
    assert 'Synthetic Requestor' not in json.dumps(result.document())
    assert 'Synthetic repair, repeated' not in json.dumps(result.document())
    assert result.document()['business_accuracy'] == 'not_independently_verified'


def test_year_rollover_and_missing_months_are_not_zero(tmp_path):
    root = tmp_path/'raw'
    setup(root)
    result = run(root, tmp_path/'out', '2025-12', '2026-02')
    assert len(result.reports) == 9
    assert all(r.status=='missing' and r.source_records is None for r in result.reports[:3]+result.reports[6:])
    assert result.reports[3].retained_records == 3
    assert month_status(result.reports[:3]) == 'Missing reports'


@pytest.mark.parametrize('change', ['modify','delete','replace'])
def test_source_changes_require_rediscovery_and_do_not_reclean(tmp_path, change):
    root = tmp_path/'raw'; setup(root)
    provider = LocalFolderStorage(root)
    inventory = discover_history(provider,'2026-01','2026-01','sharepoint_year_month')
    source = inventory.months[0].reports[0].sources[0]
    path = root/source.item_id
    if change == 'delete':
        path.unlink()
    elif change == 'replace':
        raw = path.read_bytes(); path.unlink(); path.write_bytes(raw)
    else:
        path.write_bytes(raw_report(count=2))
    result = preview_history(provider, inventory, tmp_path/'out')
    assert result.reports[0].status=='stale' and result.reports[0].retained_records is None
    assert result.reports[1].retained_records==2
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('mode', ['duplicate','unsupported','missing','invalid_date','wrong_month'])
def test_failed_report_does_not_hide_other_reports(tmp_path, mode):
    root = tmp_path/'raw'; setup(root,(1,2))
    folder = root/'2026/2026-01 (January)'
    repair = folder/'CompuClean Repair Report.csv'
    if mode=='duplicate':
        (folder/'CompuClean_Repair_Report.csv').write_bytes(repair.read_bytes())
    elif mode=='unsupported':
        repair.rename(repair.with_suffix('.xlsx'))
    elif mode=='missing':
        repair.unlink()
    elif mode=='invalid_date':
        repair.write_bytes(repair.read_bytes().replace(b'1/15/2026',b'not-a-date'))
    else:
        repair.write_bytes(raw_report(month=2))
    batch = run(root,tmp_path/'out',end='2026-02')
    assert len(batch.reports)==6 and batch.reports[0].status in ('missing','failed','unsupported')
    assert batch.reports[3].retained_records==3
    assert batch.reports[1].retained_records==2
    if mode=='invalid_date':
        assert dict(batch.reports[0].date_observations)['CompletedDate1:invalid']==3
    if mode=='wrong_month':
        assert dict(batch.reports[0].date_observations)['CompletedDate1:outside_period']==3


@pytest.mark.parametrize('costs,status', [(['$10','',''], 'incomplete_repair_costs_or_excluded_records'),
                                         (['$10','$10','$20'],'difference')])
def test_missing_costs_and_discrepancies_remain_visible(tmp_path,costs,status):
    root=tmp_path/'raw';setup(root)
    (root/'2026/2026-01 (January)/CompuClean Repair Report.csv').write_bytes(raw_report(costs=costs))
    result=run(root,tmp_path/'out').reports[0]
    financial=dict(result.financial)
    assert financial['ReconciliationStatus']==status and result.status=='warnings'
    if '' in costs:
        assert financial['UnavailableRepairCostCount']=='2' and financial['RepairTotalDifference'] is None
        assert dict(result.missing_values)['ReportedTotalCost']==2


@pytest.mark.parametrize('name,month,count', [('may_small.xls',5,3), ('june.xls',6,3),
    ('formatting_column.xls',5,81),('formatting_rows.xls',5,81)])
def test_timestamped_biff8_and_formatting_edges(tmp_path,name,month,count):
    root=tmp_path/'raw';setup(root,(month,))
    import calendar
    folder=root/f'2026/2026-{month:02d} ({calendar.month_name[month]})'
    next(folder.glob('*.xlsx')).unlink()
    fixture=Path(__file__).parent/'fixtures/synthetic/tma_timestamped'/name
    (folder/'CU_Repair_WO_History_-_Previous_Month_(HI-042b)12345.xls').write_bytes(fixture.read_bytes())
    result=run(root,tmp_path/'out',start=f'2026-{month:02d}').reports[2]
    assert result.retained_records==count and result.excluded_records==0
    assert dict(result.missing_values)['AssignedTo']==count
    assert 'tma_timestamped_previous_month_layout' in result.warnings


def test_cancel_keeps_results_and_marks_remaining_slots(tmp_path):
    root=tmp_path/'raw';setup(root,(1,2))
    stop=Event();seen=[]
    def update(result):
        seen.append(result)
        stop.set()
    result=run(root,tmp_path/'out',end='2026-02',on_result=update,cancelled=stop)
    assert result.stopped and result.reports[0].retained_records==3
    assert all(r.status=='not_previewed' and r.retained_records is None for r in result.reports[1:])
    assert len(seen)==6 and not (tmp_path/'out').exists()


def test_already_processed_and_corrected_candidate_preview_has_details_but_no_writes(tmp_path):
    root=tmp_path/'raw';setup(root)
    output=tmp_path/'out'
    coordinator=powerbi_coordinator(output)
    raw=raw_report()
    assert coordinator.process(ProcessingRequest('repairs','2026-01',raw_bytes=raw)).status=='success'
    before=snapshot(output)
    result=run(root,output).reports[0]
    assert result.candidate_status=='skipped' and result.retained_records==3 and result.financial
    assert snapshot(output)==before
    (root/'2026/2026-01 (January)/CompuClean Repair Report.csv').write_bytes(raw_report(costs=['$20']*3))
    corrected=run(root,output).reports[0]
    assert corrected.candidate_status=='needs_review' and corrected.financial
    assert snapshot(output)==before


@pytest.mark.parametrize('extension',['csv','json'])
def test_export_is_diagnostic_exclusive_and_content_minimized(tmp_path,extension):
    root=tmp_path/'raw';setup(root)
    batch=run(root,tmp_path/'out')
    target=tmp_path/f'preview.{extension}'
    export_preview(batch,target,protected_roots=(root,tmp_path/'out',tmp_path/'approved'))
    text=target.read_text(encoding='utf-8-sig')
    assert 'NonproductionDiagnosticPreview' in text and 'Synthetic Requestor' not in text
    assert 'Synthetic inspection' not in text
    if extension=='csv':
        rows=list(csv.reader(StringIO(text)))
        assert tuple(rows[0])==EXPORT_COLUMNS and len(rows)==4
        record=dict(zip(rows[0], rows[1]))
        assert record['FinancialStatus']=='arithmetic_match' and record['ReportedTotalCost']=='30.00'
    with pytest.raises(ProcessingError,match='exists'):
        export_preview(batch,target,protected_roots=(root,))
    for protected in (root,tmp_path/'out',tmp_path/'approved'):
        with pytest.raises(ProcessingError,match='overlaps_workspace'):
            export_preview(batch,protected/f'preview.{extension}',protected_roots=(root,tmp_path/'out',tmp_path/'approved'))


def test_export_failed_write_removes_only_owned_partial(tmp_path,monkeypatch):
    root=tmp_path/'raw';setup(root)
    batch=run(root,tmp_path/'out')
    import equipment_data_manager.historical_preview as module
    def fail(_): raise OSError('synthetic interrupted flush')
    monkeypatch.setattr(module.os,'fsync',fail)
    target=tmp_path/'preview.csv'
    with pytest.raises(OSError): export_preview(batch,target,protected_roots=(root,))
    assert not target.exists()


@pytest.mark.parametrize('name', ['may_four_columns.xls','may_five_columns.xls'])
def test_classic_legacy_xls_batch_uses_existing_adapter(tmp_path,name):
    root=tmp_path/'raw';setup(root,(5,),layout='standard')
    folder=root/'2026-05/tma_work_orders'
    next(folder.glob('*.xlsx')).unlink()
    fixture=Path(__file__).parent/'fixtures/synthetic/legacy_tma'/name
    (folder/'legacy.xls').write_bytes(fixture.read_bytes())
    result=run(root,tmp_path/'out',start='2026-05',layout='standard').reports[2]
    assert result.source_records==result.retained_records==2 and result.excluded_records==0
    assert 'tma_xls_cached_values_only' in result.warnings


def test_unexpected_adapter_exception_is_private_and_batch_continues(tmp_path,monkeypatch):
    import equipment_data_manager.historical_preview as module
    root=tmp_path/'raw';setup(root,(1,2))
    original=module.verify_inventory_source
    def fail_one(provider,source):
        if source.name=='CompuClean Repair Report.csv' and '2026-01' in source.item_id:
            raise RuntimeError('SYNTHETIC PRIVATE SOURCE CONTENT')
        return original(provider,source)
    monkeypatch.setattr(module,'verify_inventory_source',fail_one)
    result=run(root,tmp_path/'out',end='2026-02')
    assert result.reports[0].status=='failed' and result.reports[3].retained_records==3
    assert 'PRIVATE' not in json.dumps(result.document())


def test_windows_export_path_limit_counts_utf16_and_does_not_create_directories(tmp_path):
    from equipment_data_manager.historical_preview import _check_export_path
    prefix=str(tmp_path.resolve())+'/'
    path=Path(prefix+'a'*(260-len(prefix)-4)+'.csv')
    assert len(str(path).encode('utf-16-le'))//2==260
    with pytest.raises(ProcessingError,match='path_too_long'): _check_export_path(path,windows=True)
    _check_export_path(Path(str(path)[:-1]),windows=True)
    with pytest.raises(ProcessingError,match='path_too_long'):
        _check_export_path(Path(prefix+'😀'*130+'.csv'),windows=True)
    assert list(tmp_path.iterdir())==[]


def test_tma_timestamp_mismatch_remains_blocking_in_batch(tmp_path):
    root=tmp_path/'raw';setup(root,(6,))
    folder=root/'2026/2026-06 (June)'
    next(folder.glob('*.xlsx')).unlink()
    fixture=Path(__file__).parent/'fixtures/synthetic/tma_timestamped/may_small.xls'
    (folder/'CU_Repair_WO_History_-_Previous_Month_(HI-042b)123.xls').write_bytes(fixture.read_bytes())
    report=run(root,tmp_path/'out',start='2026-06').reports[2]
    assert report.status=='failed' and report.code=='tma_generation_period_mismatch'
    assert report.retained_records is None


@pytest.mark.parametrize('layout', ['standard','sharepoint_year_month'])
def test_documented_synthetic_demo_all_six_months(tmp_path,layout):
    import runpy
    example=Path(__file__).resolve().parents[1]/'examples/create_historical_batch_demo.py'
    create=runpy.run_path(str(example))['create_demo']
    destination=create(tmp_path/'demo')
    root=destination/('sharepoint' if layout=='sharepoint_year_month' else layout)
    batch=run(root,tmp_path/'out',end='2026-06',layout=layout)
    assert len(batch.reports)==18 and all(r.retained_records is not None for r in batch.reports)
    assert batch.reports[-1].retained_records==3
    assert not (tmp_path/'out').exists()
    with pytest.raises(FileExistsError): create(destination)


def test_real_multi_year_preview_not_just_missing_slots(tmp_path):
    import openpyxl
    root=tmp_path/'raw';setup(root)
    folder=populate(root,'2025-12','December','sharepoint_year_month',valid=True)
    (folder/'CompuClean Repair Report.csv').write_bytes(raw_report(12).replace(b'2026',b'2025'))
    service=folder/'CompuClean Service Orders List.csv'
    service.write_bytes(service.read_bytes().replace(b'2026',b'2025'))
    workbook=folder/'Work Orders December 2025.xlsx'
    book=openpyxl.load_workbook(workbook)
    for row in book.active:
        for cell in row:
            if isinstance(cell.value,str): cell.value=cell.value.replace('2026','2025')
    book.save(workbook);book.close()
    result=run(root,tmp_path/'out','2025-12','2026-01')
    assert len(result.reports)==6 and all(r.retained_records is not None for r in result.reports)


def test_service_exclusion_and_date_counts_reuse_existing_rules(tmp_path):
    root=tmp_path/'raw';setup(root)
    path=root/'2026/2026-01 (January)/CompuClean Service Orders List.csv'
    table=list(csv.reader(StringIO(service_csv(1,3).decode('utf-8-sig'))))
    table[2][1]=''
    table[3][4]=table[3][5]='invalid'
    path.write_bytes(csv_bytes(table[0],table[1:]))
    result=run(root,tmp_path/'out').reports[1]
    assert (result.source_records,result.retained_records,result.excluded_records)==(3,1,2)
    assert dict(result.exclusions)=={'missing_equipment_id':1,'no_parseable_service_date':1}
    assert dict(result.date_observations)['ScheduledDate:invalid']==1


@pytest.mark.parametrize('cost,known,status',[('$0','0','arithmetic_match'),('',None,'incomplete_repair_costs_or_excluded_records')])
def test_zero_and_all_missing_costs_are_distinct(tmp_path,cost,known,status):
    root=tmp_path/'raw';setup(root)
    path=root/'2026/2026-01 (January)/CompuClean Repair Report.csv'
    path.write_bytes(raw_report(costs=[cost]*3,reported_total='0.00',labor='0.00',parts='0.00'))
    result=run(root,tmp_path/'out').reports[0]
    financial=dict(result.financial)
    assert financial['KnownRepairTotalCost']==known and financial['ReconciliationStatus']==status


def test_wrong_hash_and_oversized_range_fail_closed(tmp_path):
    root=tmp_path/'raw';setup(root)
    provider=LocalFolderStorage(root)
    inventory=discover_history(provider,'2026-01','2026-01','sharepoint_year_month')
    month=inventory.months[0];report=month.reports[0]
    wrong=replace(report,sources=(replace(report.sources[0],sha256='0'*64),))
    altered=replace(inventory,months=(replace(month,reports=(wrong,*month.reports[1:])),))
    result=preview_history(provider,altered,tmp_path/'out').reports[0]
    assert result.status=='stale' and result.code=='storage_source_hash_mismatch'
    with pytest.raises(ProcessingError):
        preview_history(provider,replace(inventory,end='2040-01'),tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_synced_destinations_and_candidate_roots_rejected(tmp_path,monkeypatch):
    root=tmp_path/'raw';setup(root)
    batch=run(root,tmp_path/'out')
    import equipment_data_manager.historical_preview as module
    monkeypatch.setattr(module,'candidate_location_error',lambda _: 'sync-root-not-local')
    with pytest.raises(ProcessingError,match='requires_local'):
        export_preview(batch,tmp_path/'diagnostic.csv',protected_roots=(root,))
    with pytest.raises(ProcessingError,match='trusted_local'):
        run(root,tmp_path/'out')
    assert not (tmp_path/'diagnostic.csv').exists()


@pytest.mark.parametrize('method',['is_symlink','is_junction'])
def test_export_rejects_linked_destination_ancestors(tmp_path,monkeypatch,method):
    root=tmp_path/'raw';setup(root)
    batch=run(root,tmp_path/'out')
    original=getattr(Path,method)
    def linked(path): return path==tmp_path or original(path)
    monkeypatch.setattr(Path,method,linked)
    with pytest.raises(ProcessingError,match='storage_path_rejected'):
        export_preview(batch,tmp_path/'preview.csv',protected_roots=(root,))
    assert not (tmp_path/'preview.csv').exists()
