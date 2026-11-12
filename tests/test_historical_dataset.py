"""Synthetic selected-revision snapshots; no private PBIX or departmental data."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import csv
import io
import json
import sqlite3
from threading import Event
from concurrent.futures import ThreadPoolExecutor

import pytest

from test_historical_processing import prepare, plan_for, execute, preview
from test_historical_discovery import snapshot
from equipment_data_manager.historical_dataset import (preview_dataset,generate_dataset,columns,
    _destination,NAMES)
from equipment_data_manager.processing.models import ProcessingError,ProcessingRequest
from equipment_data_manager.processing.repair_financial import powerbi_coordinator,summary_name


def selected(tmp_path,months=(1,)):
    workspace,inventory,batch=prepare(tmp_path,months)
    run=execute(workspace,inventory,plan_for(workspace,inventory,batch))
    assert run.summary['created']==len(months)*3
    return workspace


def build(workspace,plan,target,**kwargs):
    return generate_dataset(workspace,plan,target,confirmation=plan.fingerprint,
        local_confirmed=True,compatibility_acknowledged=True,**kwargs)


def read(path):
    return list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8'))))


def database(workspace):return workspace.candidate_folder/'powerbi_candidates/manifest.sqlite3'


def change_db(workspace,sql,args=()):
    with sqlite3.connect(database(workspace)) as c:c.execute(sql,args)


@pytest.mark.parametrize('months',[(1,),(1,2,3,4,5,6)])
def test_complete_repeatable_snapshot_preserves_all_rows_nulls_and_store(tmp_path,months):
    workspace=selected(tmp_path,months);before=snapshot(tmp_path/'candidates')
    raw_before=snapshot(workspace.raw_folder)
    plan=preview_dataset(workspace,'2026-01',f'2026-{max(months):02d}')
    assert plan.ready and len(plan.selections)==len(months)*3
    outputs=[build(workspace,plan,tmp_path/f'test-{i}') for i in (1,2)]
    assert snapshot(tmp_path/'candidates')==before and snapshot(workspace.raw_folder)==raw_before
    for name in NAMES.values():assert (outputs[0]/name).read_bytes()==(outputs[1]/name).read_bytes()
    manifest=json.loads((outputs[0]/'snapshot_manifest.json').read_text())
    assert manifest['status']=='CandidateUnverified' and manifest['approval_status']=='NotApproved'
    assert manifest['financial_schema_version']=='2' and not manifest['production_ready']
    assert manifest['missing_selections']==[] and manifest['source_bytes_verified'] is False
    for item in manifest['datasets']:
        path=outputs[0]/item['file'];rows=read(path)
        assert sha256(path.read_bytes()).hexdigest()==item['sha256']
        assert item['rows']==len(rows)==sum(item['rows_by_month'].values())
        assert list(rows[0])==list(columns(item['report_type']))
        assert all(r['ReportingMonth']==r['ReportMonth'] for r in rows)
        assert all(len(r['CandidateRevisionId'])==32 for r in rows)
    services=read(outputs[0]/NAMES['service_orders'])
    assert any(r['EquipmentId'].startswith('0') for r in services)
    assert all(r['EstimatedPrice']=='' for r in services)
    summaries=read(outputs[0]/NAMES['repair_financial_summary'])
    assert len(summaries)==len(months) and all('LegacyLaborCostSum' in r for r in summaries)
    assert not workspace.approved_folder.exists()


def test_cross_year_range_reports_exact_missing_slots_without_zero_invention(tmp_path):
    workspace=selected(tmp_path)
    plan=preview_dataset(workspace,'2025-12','2026-02')
    assert len(plan.selections)==9 and sum(s.status=='missing' for s in plan.selections)==6
    with pytest.raises(ProcessingError,match='incomplete_selection'):build(workspace,plan,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_no_manifest_does_not_create_one_or_fall_back_to_orphan_files(tmp_path):
    workspace,_,_=prepare(tmp_path)
    orphan=workspace.candidate_folder/'powerbi_candidates/versions'/('a'*32)
    orphan.mkdir(parents=True);(orphan/'CompuClean_RepairReports_2026-01.csv').write_text('orphan')
    before=snapshot(workspace.candidate_folder)
    plan=preview_dataset(workspace,'2026-01','2026-01')
    assert all(s.status=='missing' and s.rows is None and s.unavailable_costs is None for s in plan.selections)
    assert snapshot(workspace.candidate_folder)==before and not database(workspace).exists()


@pytest.mark.parametrize('fault',['main_hash','summary_missing','summary_hash','schema','schema_v1','cleaner','source_hash','row_count','binding','duplicate_revision'])
def test_integrity_errors_are_scoped_and_block_all_writes(tmp_path,fault):
    workspace=selected(tmp_path);engine=powerbi_coordinator(workspace.candidate_folder)
    repair=next(e.artifact for e in engine.store.history() if e.report_type=='repairs')
    if fault=='main_hash':repair.output_path.write_bytes(repair.output_path.read_bytes()+b'bad')
    elif fault.startswith('summary'):
        path=repair.output_path.parent/summary_name('2026-01')
        if fault=='summary_missing':path.unlink()
        else:path.write_bytes(path.read_bytes()+b'bad')
    elif fault in ('schema','schema_v1'):
        raw=repair.output_path.read_bytes()
        if fault=='schema':raw=raw.replace(b'EquipmentId',b'WrongColumn',1)
        else:raw=raw.replace(b',powerbi-v2,2,',b',powerbi-v1,1,')
        repair.output_path.write_bytes(raw)
        change_db(workspace,'UPDATE revisions SET output_hash=? WHERE id=?',(sha256(raw).hexdigest(),repair.revision_id))
    elif fault=='cleaner':change_db(workspace,'UPDATE revisions SET cleaner_version=? WHERE id=?',('unknown',repair.revision_id))
    elif fault=='source_hash':change_db(workspace,'UPDATE revisions SET source_hash=? WHERE id=?',('a'*64,repair.revision_id))
    elif fault=='row_count':change_db(workspace,'UPDATE revisions SET output_rows=99 WHERE id=?',(repair.revision_id,))
    else:change_db(workspace,'UPDATE active SET revision_id=? WHERE report_type=?',(repair.revision_id,'service_orders'))
    plan=preview_dataset(workspace,'2026-01','2026-01')
    assert not plan.ready and any(s.status=='invalid' for s in plan.selections)
    with pytest.raises(ProcessingError,match='incomplete_selection'):build(workspace,plan,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_changed_selection_requires_new_preview_and_confirmation(tmp_path):
    workspace=selected(tmp_path);plan=preview_dataset(workspace,'2026-01','2026-01')
    engine=powerbi_coordinator(workspace.candidate_folder)
    entry=next(e for e in engine.store.history() if e.report_type=='service_orders')
    raw=(workspace.raw_folder/'2026/2026-01 (January)/CompuClean Service Orders List.csv').read_bytes()
    request=ProcessingRequest('service_orders','2026-01',raw_bytes=raw.replace(b'Synthetic',b'Corrected'),source_name='CompuClean Service Orders List.csv')
    proposal=engine.preview(request)
    assert proposal.replacement_token
    corrected=engine.process(replace(request,replacement_token=proposal.replacement_token))
    assert corrected.status=='success' and corrected.artifact.revision_id!=entry.artifact.revision_id
    before=snapshot(workspace.candidate_folder)
    with pytest.raises(ProcessingError,match='plan_stale'):build(workspace,plan,tmp_path/'out')
    assert snapshot(workspace.candidate_folder)==before
    fresh=preview_dataset(workspace,'2026-01','2026-01');root=build(workspace,fresh,tmp_path/'new')
    assert {r['CandidateRevisionId'] for r in read(root/NAMES['service_orders'])}=={corrected.artifact.revision_id}


@pytest.mark.parametrize('confirmation,local,gaps',[('wrong',True,True),('correct',False,True),('correct',True,False)])
def test_explicit_local_unapproved_and_compatibility_acknowledgement(tmp_path,confirmation,local,gaps):
    workspace=selected(tmp_path);plan=preview_dataset(workspace,'2026-01','2026-01')
    with pytest.raises(ProcessingError,match='confirmation_required'):
        generate_dataset(workspace,plan,tmp_path/'out',confirmation=plan.fingerprint if confirmation=='correct' else confirmation,
            local_confirmed=local,compatibility_acknowledged=gaps)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('destination',['raw','candidates','approved','parent','OneDrive'])
def test_protected_and_synced_destination_rejected(tmp_path,destination):
    workspace=selected(tmp_path);plan=preview_dataset(workspace,'2026-01','2026-01')
    target={'raw':workspace.raw_folder/'out','candidates':workspace.candidate_folder/'out',
        'approved':workspace.approved_folder/'out','parent':tmp_path,'OneDrive':tmp_path/'OneDrive'/'out'}[destination]
    with pytest.raises(ProcessingError,match='overlaps_workspace|trusted_local'):build(workspace,plan,target)


@pytest.mark.parametrize('predicate',['is_symlink','is_junction'])
def test_link_checks_include_destination_and_candidate_ancestors(tmp_path,monkeypatch,predicate):
    workspace=selected(tmp_path)
    target=tmp_path/'redirect'/'out';original=getattr(Path,predicate)
    monkeypatch.setattr(Path,predicate,lambda p:p==target.parent or original(p))
    plan=preview_dataset(workspace,'2026-01','2026-01')
    with pytest.raises(ProcessingError,match='link_rejected'):build(workspace,plan,target)
    original_root=workspace.candidate_folder
    monkeypatch.setattr(Path,predicate,lambda p:p==original_root or original(p))
    with pytest.raises(ProcessingError,match='link_rejected'):preview_dataset(workspace,'2026-01','2026-01')


def test_windows_path_preflight_does_not_depend_on_host_policy(tmp_path):
    workspace=selected(tmp_path)
    with pytest.raises(ProcessingError,match='windows_path_too_long'):
        _destination(workspace,tmp_path/('x'*190)/'output',windows=True)
    assert _destination(workspace,tmp_path/'short',windows=True)


def test_collision_never_overwrites_completed_snapshot(tmp_path):
    workspace=selected(tmp_path);plan=preview_dataset(workspace,'2026-01','2026-01')
    build(workspace,plan,tmp_path/'out');before=snapshot(tmp_path/'out')
    with pytest.raises(ProcessingError,match='destination_exists'):build(workspace,plan,tmp_path/'out')
    assert snapshot(tmp_path/'out')==before


@pytest.mark.parametrize('failure',['write','rename','cancel_write','interrupt'])
def test_atomic_finalization_and_owned_cleanup_on_failure(tmp_path,monkeypatch,failure):
    import equipment_data_manager.historical_dataset as module
    workspace=selected(tmp_path);plan=preview_dataset(workspace,'2026-01','2026-01');before=snapshot(workspace.candidate_folder)
    target=tmp_path/'out';cancelled=Event();write=module._write;rename=Path.rename
    def fail_write(path,raw):
        assert not (target/'snapshot').exists()
        write(path,raw)
        if path.name==NAMES['service_orders']:
            if failure=='write':raise OSError('Synthetic interruption')
            if failure=='interrupt':raise KeyboardInterrupt()
            if failure=='cancel_write':cancelled.set()
    def fail_rename(path,other):
        if path==target/'.s' and failure=='rename':raise OSError('Synthetic rename failure')
        return rename(path,other)
    monkeypatch.setattr(module,'_write',fail_write);monkeypatch.setattr(Path,'rename',fail_rename)
    with pytest.raises((OSError,ProcessingError,KeyboardInterrupt)):build(workspace,plan,target,cancelled=cancelled.is_set)
    assert not target.exists() and snapshot(workspace.candidate_folder)==before


def test_cancelled_preview_has_explicit_not_assessed_slots(tmp_path):
    workspace=selected(tmp_path);stop=Event()
    plan=preview_dataset(workspace,'2026-01','2026-01',progress=lambda *_:stop.set(),cancelled=stop.is_set)
    assert plan.stopped and not plan.ready and sum(s.status=='not_assessed' for s in plan.selections)==2


def test_missing_costs_and_repeated_ids_remain_explicit_and_unallocated(tmp_path):
    from test_repair_financial import raw_report
    workspace,inventory,batch=prepare(tmp_path,(5,))
    repair_path=workspace.raw_folder/'2026/2026-05 (May)/CompuClean Repair Report.csv'
    repair_path.write_bytes(raw_report(5,costs=['$10.00','','bad']))
    inventory,batch=preview(workspace,'2026-05','2026-05')
    execute(workspace,inventory,plan_for(workspace,inventory,batch))
    engine=powerbi_coordinator(workspace.candidate_folder)
    raw=Path('tests/fixtures/synthetic/tma_timestamped/may_81.xls').read_bytes()
    request=ProcessingRequest('tma_work_orders','2026-05',raw_bytes=raw,
        source_name='CU_Repair_WO_History_-_Previous_Month_(HI-042b)512345.xls')
    proposal=engine.preview(request)
    result=engine.process(replace(request,replacement_token=proposal.replacement_token))
    assert result.status=='success'
    plan=preview_dataset(workspace,'2026-05','2026-05');assert plan.ready
    repair=next(s for s in plan.selections if s.report_type=='repairs')
    tma=next(s for s in plan.selections if s.report_type=='tma_work_orders')
    assert repair.unavailable_costs==2 and repair.reconciliation=='incomplete_repair_costs_or_excluded_records'
    assert tma.missing_assignments==tma.rows==81
    out=build(workspace,plan,tmp_path/'snapshot-out')
    summary=read(out/NAMES['repair_financial_summary'])[0]
    assert summary['KnownRepairTotalCost']=='10.00' and summary['RepairTotalDifference']==''
    rows=read(out/NAMES['repairs'])
    assert sum(r['ReportedTotalCost']=='' for r in rows)==2
    assert len(read(out/NAMES['tma_work_orders']))==81
    assert all(r['AssignedTo']=='' for r in read(out/NAMES['tma_work_orders']))


def test_repeated_work_order_business_ids_across_months_are_not_deduplicated(tmp_path):
    workspace=selected(tmp_path,(1,2))
    plan=preview_dataset(workspace,'2026-01','2026-02');out=build(workspace,plan,tmp_path/'out')
    rows=read(out/NAMES['tma_work_orders']);ids=[r['WorkOrderId'] for r in rows]
    assert len(rows)==4 and len(set(ids))<len(ids)
    manifest=json.loads((out/'snapshot_manifest.json').read_text())
    assert manifest['repeated_work_order_id_occurrences']==len(ids)-len(set(ids))


def test_successful_year_rollover_order_and_monthly_counts(tmp_path):
    from openpyxl import Workbook
    from test_repair_financial import raw_report
    from equipment_data_manager.monthly import Workspace
    workspace=Workspace(tmp_path/'raw',tmp_path/'candidates',tmp_path/'approved')
    engine=powerbi_coordinator(workspace.candidate_folder)
    for period in ('2026-01','2025-12'): # Deliberately create in reverse order.
        year,month=period.split('-')
        repair=raw_report(int(month)).replace(b'/2026',b'/'+year.encode())
        # Use the supported bundled no-price sample, replacing its source month.
        from importlib.resources import files
        service=files('equipment_data_manager').joinpath('resources/samples/service_sample.csv').read_bytes()
        import re
        service=service.replace(b'2026-09',period.encode())
        for kind,raw in [('repairs',repair),('service_orders',service)]:
            r=engine.process(ProcessingRequest(kind,period,raw_bytes=raw,source_name=kind+'.csv'))
            assert r.status=='success',r.code
        book=Workbook();sheet=book.active
        import calendar
        for row in [[f'CU Repair WO History — {calendar.month_name[int(month)]} {year}','','','',''],
            ['Work Order #','Request Date','Requestor','Request','Assigned To'],
            ['000001',f'{month}/15/{year}','Synthetic','Synthetic',''],['Total: 1 records','','','','']]:sheet.append(row)
        stream=io.BytesIO();book.save(stream);book.close()
        r=engine.process(ProcessingRequest('tma_work_orders',period,raw_bytes=stream.getvalue(),source_name='work.xlsx'))
        assert r.status=='success',r.code
    plan=preview_dataset(workspace,'2025-12','2026-01');assert plan.ready
    out=build(workspace,plan,tmp_path/'out')
    assert [r['ReportingMonth'] for r in read(out/NAMES['tma_work_orders'])]==['2025-12','2026-01']


def test_completed_snapshot_integrity_checker_rejects_modified_datasets(tmp_path):
    from equipment_data_manager.historical_dataset import validate_dataset
    workspace=selected(tmp_path);plan=preview_dataset(workspace,'2026-01','2026-01')
    out=build(workspace,plan,tmp_path/'out')
    assert validate_dataset(out)['complete']
    (out/NAMES['repairs']).write_bytes((out/NAMES['repairs']).read_bytes()+b'bad')
    with pytest.raises(ProcessingError,match='snapshot_hash_mismatch'):validate_dataset(out)


def test_manifest_journal_mode_guard_and_preview_cancellation(tmp_path):
    workspace=selected(tmp_path)
    with sqlite3.connect(database(workspace)) as c:c.execute('PRAGMA journal_mode=WAL')
    with pytest.raises(ProcessingError,match='journal_rejected'):preview_dataset(workspace,'2026-01','2026-01')


@pytest.mark.parametrize('costs,total,labor,parts,unavailable',[(['$0.00']*3,'0.00','0.00','0.00',0),(['']*3,'30.00','5.00','25.00',3)])
def test_zero_and_all_missing_cost_contracts(tmp_path,costs,total,labor,parts,unavailable):
    from test_repair_financial import raw_report
    workspace,inventory,batch=prepare(tmp_path)
    path=workspace.raw_folder/'2026/2026-01 (January)/CompuClean Repair Report.csv'
    path.write_bytes(raw_report(costs=costs,reported_total=total,labor=labor,parts=parts))
    inventory,batch=preview(workspace,'2026-01','2026-01')
    execute(workspace,inventory,plan_for(workspace,inventory,batch))
    plan=preview_dataset(workspace,'2026-01','2026-01');assert plan.ready
    out=build(workspace,plan,tmp_path/'out');summary=read(out/NAMES['repair_financial_summary'])[0]
    assert int(summary['UnavailableRepairCostCount'])==unavailable
    assert summary['KnownRepairTotalCost']==('' if unavailable else '0.00')
    assert summary['RepairTotalDifference']==('' if unavailable else '0.00')


def test_concurrent_same_destination_keeps_one_complete_snapshot(tmp_path):
    workspace=selected(tmp_path);plan=preview_dataset(workspace,'2026-01','2026-01')
    def attempt():
        try:return str(build(workspace,plan,tmp_path/'out'))
        except (ProcessingError,OSError):return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:attempt(),range(2)))
    assert sum(r is not None for r in results)==1
    from equipment_data_manager.historical_dataset import validate_dataset
    assert validate_dataset(tmp_path/'out/snapshot')['complete']


def test_sample_generator_and_bundled_mapping_are_complete(tmp_path):
    import runpy
    outputs=runpy.run_path('examples/create_historical_dataset_demo.py')['create_demo'](tmp_path/'demo')
    assert len(read(outputs[0]/NAMES['repair_financial_summary']))==6
    text=(outputs[0]/'compatibility_report.md').read_text()
    assert 'March 9' in text and 'omitting August' in text and 'date-only' in text
    from importlib.resources import files
    assert files('equipment_data_manager.resources.guides').joinpath('historical_powerbi_compatibility.md').read_text()==Path('docs/historical_powerbi_compatibility.md').read_text()


def test_powerquery_example_matches_exact_snapshot_contracts():
    import re
    text=Path('powerquery/fnReadHistoricalSnapshot.pq').read_text()
    for kind in NAMES:
        body=re.search(r'\b'+kind+r' = \{([^\n]+)\}',text).group(1)
        names=re.findall(r'\{"([^"]+)", "(?:text|integer|decimal|date)"',body)
        # Include the final field (the outer brace terminates after its type).
        assert names==list(columns(kind))
    assert 'Folder.Files' not in text and 'File.Contents' in text
    assert 'type nullable number' in text and 'CandidateRevisionId' in text
