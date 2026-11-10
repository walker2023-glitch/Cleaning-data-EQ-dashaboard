"""Invented reports, real coordinator, no production services or business approvals."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from threading import Event

import pytest

from test_historical_preview import setup
from test_historical_discovery import snapshot
from test_repair_financial import raw_report
from equipment_data_manager.historical import discover_history
from equipment_data_manager.historical_preview import preview_history
from equipment_data_manager.historical_processing import make_plan, execute_plan, export_processing, _check_candidate_paths
from equipment_data_manager.processing.models import ProcessingRequest, ProcessingError, ReportType
from equipment_data_manager.processing.repair_financial import powerbi_coordinator
from equipment_data_manager.storage.local import LocalFolderStorage
from equipment_data_manager.monthly import Workspace


def prepare(tmp_path, months=(1,), layout='sharepoint_year_month'):
    workspace=Workspace(tmp_path/'raw',tmp_path/'candidates',tmp_path/'approved')
    setup(workspace.raw_folder,months,layout)
    inventory,batch=preview(workspace,f'2026-{min(months):02d}',f'2026-{max(months):02d}',layout)
    return workspace,inventory,batch


def preview(workspace,start,end,layout='sharepoint_year_month'):
    provider=LocalFolderStorage(workspace.raw_folder)
    inventory=discover_history(provider,start,end,layout)
    return inventory,preview_history(provider,inventory,workspace.candidate_folder)


def plan_for(workspace,inventory,batch,selected=None,**kwargs):
    selected=tuple((r.month,r.report_type) for r in batch.reports) if selected is None else selected
    return make_plan(workspace,inventory.layout,inventory,batch,selected,**kwargs)


def execute(workspace,inventory,plan,**kwargs):
    return execute_plan(workspace,inventory.layout,plan,plan.fingerprint,**kwargs)


@pytest.mark.parametrize('layout',['standard','sharepoint_year_month'])
@pytest.mark.parametrize('months',[(1,),(1,2,3,4,5,6)])
def test_real_coordinator_all_reports_and_retry_skip_without_duplicate_revisions(tmp_path,layout,months):
    workspace,inventory,batch=prepare(tmp_path,months,layout)
    raw_before=snapshot(workspace.raw_folder)
    plan=plan_for(workspace,inventory,batch)
    assert all(i.action=='create' for i in plan.items) and not workspace.candidate_folder.exists()
    with pytest.raises(ProcessingError,match='confirmation_required'):
        execute_plan(workspace,layout,plan,'not the reviewed fingerprint')
    assert not workspace.candidate_folder.exists()
    results=execute(workspace,inventory,plan)
    assert results.summary['created']==len(months)*3 and all(i.revision for i in results.items)
    engine=powerbi_coordinator(workspace.candidate_folder)
    assert len(engine.store.history())==len(months)*3
    for item in results.items:
        assert sha256(Path(item.output_location).read_bytes()).hexdigest()==item.output_sha256
        assert item.evidence.source_sha256==item.source.sha256
        assert item.integrity=='local_bytes_read_stably_sync_unverified'
    # New coordinator/discovery/preview simulates restart; no persisted batch auto-resume.
    inventory,batch=preview(workspace,inventory.start,inventory.end,layout)
    again=plan_for(workspace,inventory,batch)
    assert all(i.action=='skip' for i in again.items)
    skipped=execute(workspace,inventory,again)
    assert skipped.summary['skipped']==len(months)*3 and skipped.summary['created']==0
    assert len(engine.store.history())==len(months)*3
    assert snapshot(workspace.raw_folder)==raw_before and not workspace.approved_folder.exists()


def test_subset_mixed_selections_and_invalid_selection(tmp_path):
    workspace,inventory,batch=prepare(tmp_path,(1,2))
    selected=(('2026-01','repairs'),('2026-02','tma_work_orders'))
    plan=plan_for(workspace,inventory,batch,selected)
    run=execute(workspace,inventory,plan)
    assert len(run.items)==2 and run.summary['created']==2
    for invalid in ((),selected+selected,(('2026-03','repairs'),),(('2026-01','unknown'),)):
        with pytest.raises(ProcessingError,match='invalid_selection'):
            plan_for(workspace,inventory,batch,invalid)


def test_missing_unsupported_and_invalid_rows_remain_blocked_while_others_continue(tmp_path):
    workspace,_,_=prepare(tmp_path,(1,2))
    folder=workspace.raw_folder/'2026/2026-01 (January)'
    (folder/'CompuClean Service Orders List.csv').unlink()
    (folder/'CompuClean Repair Report.csv').write_bytes(b'invalid,layout\n1,2\n')
    tma=next(folder.glob('*.xlsx'));tma.rename(tma.with_suffix('.csv'))
    inventory,batch=preview(workspace,'2026-01','2026-02')
    plan=plan_for(workspace,inventory,batch)
    run=execute(workspace,inventory,plan)
    assert run.summary['blocked']==3 and run.summary['created']==3
    assert all(i.revision is None for i in run.items[:3])


def test_corrections_stay_blocked_and_previous_revision_survives(tmp_path):
    workspace,inventory,batch=prepare(tmp_path)
    plan=plan_for(workspace,inventory,batch)
    first=execute(workspace,inventory,plan)
    path=workspace.raw_folder/'2026/2026-01 (January)/CompuClean Repair Report.csv'
    path.write_bytes(raw_report(costs=['$20']*3))
    inventory,batch=preview(workspace,'2026-01','2026-01')
    plan=plan_for(workspace,inventory,batch)
    assert plan.items[0].action=='correction'
    engine=powerbi_coordinator(workspace.candidate_folder);before=engine.store.history()
    run=execute(workspace,inventory,plan)
    assert run.summary['correction']==1 and run.summary['skipped']==2
    assert engine.store.history()==before
    # The unchanged single-report token mechanism still performs a specific correction.
    request=ProcessingRequest('repairs','2026-01',input_path=path)
    pending=engine.preview(request)
    assert pending.status=='needs_review'
    corrected=engine.process(replace(request,replacement_token=pending.replacement_token))
    assert corrected.status=='success' and corrected.previous.revision_id==first.items[0].revision
    assert len(engine.store.history())==4 and Path(first.items[0].output_location).exists()


@pytest.mark.parametrize('when',['before_plan','after_plan'])
def test_source_changes_never_substitute_new_bytes(tmp_path,when):
    workspace,inventory,batch=prepare(tmp_path)
    plan=plan_for(workspace,inventory,batch) if when=='after_plan' else None
    (workspace.raw_folder/'2026/2026-01 (January)/CompuClean Repair Report.csv').write_bytes(raw_report(count=2))
    plan=plan or plan_for(workspace,inventory,batch)
    run=execute(workspace,inventory,plan)
    assert run.items[0].status=='blocked' and run.items[0].revision is None
    assert run.summary['created']==2


def test_candidate_selection_changed_after_confirmation_is_rejected_atomically(tmp_path):
    workspace,inventory,batch=prepare(tmp_path)
    plan=plan_for(workspace,inventory,batch)
    engine=powerbi_coordinator(workspace.candidate_folder)
    # A different operation commits after plan review. Batch has no correction authority.
    path=workspace.raw_folder/'2026/2026-01 (January)/CompuClean Repair Report.csv'
    other=engine.process(ProcessingRequest('repairs','2026-01',input_path=path))
    run=execute(workspace,inventory,plan)
    assert run.items[0].code=='batch_candidate_selection_changed' and run.items[0].status=='blocked'
    assert len(engine.store.history())==3
    assert next(e for e in engine.store.history() if e.report_type==ReportType.REPAIRS).artifact.revision_id==other.artifact.revision_id


@pytest.mark.parametrize('version_change',[False,True])
def test_changed_cleaner_output_or_version_cannot_commit_an_old_plan(tmp_path,version_change):
    workspace,inventory,batch=prepare(tmp_path)
    engine=powerbi_coordinator(workspace.candidate_folder)
    plan=plan_for(workspace,inventory,batch,coordinator=engine)
    base=engine.cleaners[ReportType.REPAIRS]
    class Changed:
        version=base.version+':new' if version_change else base.version
        def clean(self,*args,**kwargs):
            result=base.clean(*args,**kwargs)
            return replace(result,cleaner_version=self.version,output_bytes=result.output_bytes+b'\n')
    engine.cleaners[ReportType.REPAIRS]=Changed()
    run=execute(workspace,inventory,plan,coordinator=engine)
    assert run.items[0].code=='batch_preview_changed' and run.items[0].revision is None
    assert run.summary['created']==2


def test_cancel_before_start_and_between_commits_keeps_completed_revisions(tmp_path):
    workspace,inventory,batch=prepare(tmp_path)
    plan=plan_for(workspace,inventory,batch)
    stop=Event();stop.set()
    nothing=execute(workspace,inventory,plan,cancelled=stop)
    assert nothing.summary['not_started']==3 and not workspace.candidate_folder.exists()
    stop.clear()
    def after_first(_):stop.set()
    partial=execute(workspace,inventory,plan,cancelled=stop,on_result=after_first)
    assert partial.summary['created']==1 and partial.summary['not_started']==2
    inventory,batch=preview(workspace,'2026-01','2026-01')
    fresh=plan_for(workspace,inventory,batch)
    completed=execute(workspace,inventory,fresh)
    assert completed.summary['skipped']==1 and completed.summary['created']==2
    assert len(powerbi_coordinator(workspace.candidate_folder).store.history())==3


def test_partial_storage_failure_preserves_history_and_continues(tmp_path,monkeypatch):
    workspace,inventory,batch=prepare(tmp_path)
    engine=powerbi_coordinator(workspace.candidate_folder)
    plan=plan_for(workspace,inventory,batch,coordinator=engine)
    original=engine.store.write_revision
    def fail(kind,*args,**kwargs):
        if kind==ReportType.REPAIRS:raise OSError('SYNTHETIC PRIVATE CONTENT')
        return original(kind,*args,**kwargs)
    monkeypatch.setattr(engine.store,'write_revision',fail)
    run=execute(workspace,inventory,plan,coordinator=engine)
    assert run.summary['failed']==1 and run.summary['created']==2
    assert 'PRIVATE CONTENT' not in json.dumps(run.document())
    assert len(engine.store.history())==2


def test_abrupt_interruption_recovers_only_from_durable_manifest(tmp_path):
    workspace,inventory,batch=prepare(tmp_path)
    plan=plan_for(workspace,inventory,batch)
    class SimulatedExit(BaseException):pass
    def crash(_):raise SimulatedExit()
    with pytest.raises(SimulatedExit):execute(workspace,inventory,plan,on_result=crash)
    assert len(powerbi_coordinator(workspace.candidate_folder).store.history())==1
    inventory,batch=preview(workspace,'2026-01','2026-01')
    resumed=execute(workspace,inventory,plan_for(workspace,inventory,batch))
    assert resumed.summary['skipped']==1 and resumed.summary['created']==2


def test_concurrent_batch_attempts_fail_closed(tmp_path):
    workspace,inventory,batch=prepare(tmp_path)
    plan=plan_for(workspace,inventory,batch)
    entered,release=Event(),Event()
    def pause(month,kind):
        if not entered.is_set():entered.set();assert release.wait(10)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(execute,workspace,inventory,plan,on_start=pause)
        assert entered.wait(10)
        try:
            with pytest.raises(ProcessingError,match='already_running'):execute(workspace,inventory,plan)
        finally:release.set()
        assert first.result().summary['created']==3


def test_configuration_change_and_stopped_plan_cannot_write(tmp_path):
    workspace,inventory,batch=prepare(tmp_path)
    plan=plan_for(workspace,inventory,batch)
    changed=replace(workspace,candidate_folder=tmp_path/'other')
    with pytest.raises(ProcessingError,match='configuration_changed'):
        execute(changed,inventory,plan)
    with pytest.raises(ProcessingError,match='confirmation_required'):
        p=replace(plan,stopped=True);execute(workspace,inventory,p)
    assert not workspace.candidate_folder.exists()


@pytest.mark.parametrize('extension',['csv','json'])
def test_export_nonproduction_safe_paths_no_contents_or_overwrite(tmp_path,extension):
    workspace,inventory,batch=prepare(tmp_path)
    run=execute(workspace,inventory,plan_for(workspace,inventory,batch))
    target=tmp_path/f'processing.{extension}'
    roots=(workspace.raw_folder,workspace.candidate_folder,workspace.approved_folder)
    export_processing(run,target,protected_roots=roots)
    text=target.read_text(encoding='utf-8-sig')
    assert 'NonproductionCandidateProcessingDiagnostic' in text and 'Synthetic Requestor' not in text
    assert 'Synthetic repair, repeated legitimately' not in text
    for root in roots:
        with pytest.raises(ProcessingError,match='overlaps_workspace'):
            export_processing(run,root/f'processing.{extension}',protected_roots=roots)
    with pytest.raises(ProcessingError,match='exists'):export_processing(run,target,protected_roots=roots)


def test_windows_candidate_path_preflight_uses_full_utf16_paths_without_creating(tmp_path):
    root=tmp_path/('x'*120)/('y'*100)
    with pytest.raises(ProcessingError,match='path_too_long'):
        _check_candidate_paths(root,ReportType.REPAIRS,'2026-01',windows=True)
    assert not root.exists()


def test_preview_destination_and_injected_store_must_match_plan_configuration(tmp_path):
    workspace,inventory,batch=prepare(tmp_path)
    changed=replace(workspace,candidate_folder=tmp_path/'other')
    with pytest.raises(ProcessingError,match='configuration_changed'):plan_for(changed,inventory,batch)
    wrong=powerbi_coordinator(tmp_path/'wrong-store')
    with pytest.raises(ProcessingError,match='configuration_changed'):plan_for(workspace,inventory,batch,coordinator=wrong)
    plan=plan_for(workspace,inventory,batch)
    with pytest.raises(ProcessingError,match='configuration_changed'):execute(workspace,inventory,plan,coordinator=wrong)
    assert not workspace.candidate_folder.exists() and not wrong.store.root.exists()


def test_multi_year_processing_reuses_valid_content_months(tmp_path):
    from test_historical_discovery import populate
    import openpyxl
    workspace,_,_=prepare(tmp_path)
    folder=populate(workspace.raw_folder,'2025-12','December','sharepoint_year_month',valid=True)
    (folder/'CompuClean Repair Report.csv').write_bytes(raw_report(12).replace(b'2026',b'2025'))
    path=folder/'CompuClean Service Orders List.csv';path.write_bytes(path.read_bytes().replace(b'2026',b'2025'))
    path=folder/'Work Orders December 2025.xlsx';book=openpyxl.load_workbook(path)
    for row in book.active:
        for cell in row:
            if isinstance(cell.value,str):cell.value=cell.value.replace('2026','2025')
    book.save(path);book.close()
    inventory,batch=preview(workspace,'2025-12','2026-01')
    result=execute(workspace,inventory,plan_for(workspace,inventory,batch))
    assert result.summary['created']==6
    assert {i.month for i in result.items}=={'2025-12','2026-01'}


@pytest.mark.parametrize('name,month,count,subfolder',[
    ('may_four_columns.xls',5,2,'legacy_tma'),('may_five_columns.xls',5,2,'legacy_tma'),
    ('may_81.xls',5,81,'tma_timestamped'),('formatting_june.xls',6,3,'tma_timestamped')])
def test_legacy_timestamped_and_formatting_only_tma_processing(tmp_path,name,month,count,subfolder):
    import calendar
    workspace,_,_=prepare(tmp_path,(month,))
    folder=workspace.raw_folder/f'2026/2026-{month:02d} ({calendar.month_name[month]})'
    next(folder.glob('*.xlsx')).unlink()
    source=Path(__file__).parent/'fixtures/synthetic'/subfolder/name
    (folder/'CU_Repair_WO_History_-_Previous_Month_(HI-042b)123456.xls').write_bytes(source.read_bytes())
    inventory,batch=preview(workspace,f'2026-{month:02d}',f'2026-{month:02d}')
    result=execute(workspace,inventory,plan_for(workspace,inventory,batch))
    tma=next(i for i in result.items if i.report_type=='tma_work_orders')
    assert tma.status=='created' and tma.evidence.retained_records==count
    if 'five_columns' not in name:assert dict(tma.evidence.missing_values)['AssignedTo']==count


def test_missing_financial_values_warnings_and_summary_are_preserved(tmp_path):
    workspace,_,_=prepare(tmp_path)
    path=workspace.raw_folder/'2026/2026-01 (January)/CompuClean Repair Report.csv'
    path.write_bytes(raw_report(costs=['$10','','']))
    inventory,batch=preview(workspace,'2026-01','2026-01')
    result=execute(workspace,inventory,plan_for(workspace,inventory,batch)).items[0]
    assert result.status=='created'
    assert dict(result.evidence.financial)['UnavailableRepairCostCount']=='2'
    assert dict(result.evidence.financial)['RepairTotalDifference'] is None
    assert any(w.startswith('repair_reported_cost_unavailable:2') for w in result.evidence.warnings)
    assert 'CandidateUnverified' in Path(result.output_location).read_text()


def test_interrupted_candidate_commit_never_selects_or_ingests_orphans(tmp_path,monkeypatch):
    workspace,inventory,batch=prepare(tmp_path)
    engine=powerbi_coordinator(workspace.candidate_folder)
    plan=plan_for(workspace,inventory,batch,coordinator=engine)
    original=engine.store.select_revision
    def before_commit(connection,kind,*args,**kwargs):
        if kind==ReportType.REPAIRS:raise OSError('Synthetic interruption after file write, before manifest selection')
        return original(connection,kind,*args,**kwargs)
    monkeypatch.setattr(engine.store,'select_revision',before_commit)
    result=execute(workspace,inventory,plan,coordinator=engine)
    assert result.items[0].status=='failed' and len(engine.store.history())==2
    assert not any(e.report_type==ReportType.REPAIRS for e in engine.store.history())
    monkeypatch.setattr(engine.store,'select_revision',original)
    inventory,batch=preview(workspace,'2026-01','2026-01')
    fresh=execute(workspace,inventory,plan_for(workspace,inventory,batch))
    assert fresh.summary['created']==1 and fresh.summary['skipped']==2
    assert len(engine.store.history())==3


@pytest.mark.parametrize('method',['is_symlink','is_junction'])
def test_batch_writes_and_diagnostic_exports_reject_linked_ancestors(tmp_path,monkeypatch,method):
    workspace,inventory,batch=prepare(tmp_path)
    plan=plan_for(workspace,inventory,batch)
    original=getattr(Path,method)
    monkeypatch.setattr(Path,method,lambda p:p==workspace.candidate_folder or original(p))
    with pytest.raises(ProcessingError,match='untrusted_candidate_location'):
        execute(workspace,inventory,plan)
    assert not workspace.candidate_folder.exists()
    # Export validation uses the shared deterministic Windows-safe guard.
    monkeypatch.setattr(Path,method,original)
    result=execute(workspace,inventory,plan)
    monkeypatch.setattr(Path,method,lambda p:p==tmp_path or original(p))
    with pytest.raises(ProcessingError,match='storage_path_rejected'):
        export_processing(result,tmp_path/'report.csv',protected_roots=(workspace.raw_folder,workspace.candidate_folder,workspace.approved_folder))
    assert not (tmp_path/'report.csv').exists()


def test_plan_cancellation_cannot_authorize_partial_plan(tmp_path):
    workspace,inventory,batch=prepare(tmp_path)
    stop=Event();stop.set()
    plan=plan_for(workspace,inventory,batch,cancelled=stop)
    assert plan.stopped
    with pytest.raises(ProcessingError,match='confirmation_required'):execute(workspace,inventory,plan)
    assert not workspace.candidate_folder.exists()



def test_synced_local_sources_use_the_existing_provider_contract(tmp_path):
    workspace,_,_=prepare(tmp_path)
    provider=LocalFolderStorage(workspace.raw_folder,synced=True)
    inventory=discover_history(provider,'2026-01','2026-01','sharepoint_year_month')
    batch=preview_history(provider,inventory,workspace.candidate_folder)
    plan=plan_for(workspace,inventory,batch)
    result=execute(workspace,inventory,plan)
    assert result.summary['created']==3 and all(i.source.provider=='synced-local' for i in result.items)
    assert not result.document()['sync_verified']


@pytest.mark.parametrize('method',['is_symlink','is_junction'])
@pytest.mark.parametrize('child',['versions','manifest.sqlite3'])
def test_internal_candidate_redirects_are_blocked_even_inside_trusted_root(tmp_path,monkeypatch,method,child):
    workspace,inventory,batch=prepare(tmp_path)
    plan=plan_for(workspace,inventory,batch)
    target=workspace.candidate_folder/'powerbi_candidates'/child
    original=getattr(Path,method)
    monkeypatch.setattr(Path,method,lambda p:p==target or original(p))
    with pytest.raises(ProcessingError,match='untrusted_candidate_location'):
        execute(workspace,inventory,plan)
    assert not workspace.candidate_folder.exists()


def test_service_exclusions_and_cross_period_warnings_survive_candidate_creation(tmp_path):
    import csv
    from io import StringIO
    from report_samples import service_csv, csv_bytes
    workspace,_,_=prepare(tmp_path)
    data=list(csv.reader(StringIO(service_csv(1,3).decode('utf-8-sig'))))
    data[2][1]=''  # Existing missing-ID exclusion, not a new batch rule.
    data[3][5]='2/16/2026'  # Scheduled date remains January; preserve cross-period warning.
    (workspace.raw_folder/'2026/2026-01 (January)/CompuClean Service Orders List.csv').write_bytes(csv_bytes(data[0],data[1:]))
    inventory,batch=preview(workspace,'2026-01','2026-01')
    run=execute(workspace,inventory,plan_for(workspace,inventory,batch))
    service=next(i for i in run.items if i.report_type=='service_orders')
    assert service.status=='created'
    assert (service.evidence.source_records,service.evidence.retained_records,service.evidence.excluded_records)==(3,2,1)
    assert dict(service.evidence.exclusions)['missing_equipment_id']==1
    assert any(w.startswith('cross_period_output_dates:') for w in service.evidence.warnings)
