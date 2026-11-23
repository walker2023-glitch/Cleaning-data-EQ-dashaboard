"""Synthetic updates through real candidate/correction and snapshot machinery."""
from dataclasses import replace
from pathlib import Path
from threading import Event
import json

import pytest

from test_historical_dataset import selected, build, database, read
from test_historical_discovery import snapshot
from test_historical_processing import preview, plan_for, execute
from equipment_data_manager.historical_dataset import preview_dataset, NAMES, validate_dataset
from equipment_data_manager.monthly_update import preview_update, generate_update, ADD, REBUILD, UNCHANGED, REVIEW
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest, ReportType
from equipment_data_manager.processing.repair_financial import powerbi_coordinator
from equipment_data_manager.storage.local import LocalFolderStorage
from equipment_data_manager.historical import discover_history


def plan(w,p,start='2026-01',end='2026-01',baseline=None):
    return preview_update(w,start,end,'sharepoint_year_month',p,baseline=baseline)


def generate(w,p,**kw):
    mode=kw.pop('mode',p.permitted[0] if p.permitted else p.recommendation)
    return generate_update(w,p,mode=mode,confirmation=kw.pop('confirmation',p.confirmation(mode)),
        local_confirmed=kw.pop('local_confirmed',True),compatibility_acknowledged=True,**kw)


def baseline(w,p,end='2026-01'):
    return build(w,preview_dataset(w,'2026-01',end),p)


def source(w,kind='repairs',month='2026-01'):
    inv=discover_history(LocalFolderStorage(w.raw_folder),month,month,'sharepoint_year_month')
    item=next(r for m in inv.months for r in m.reports if r.report_type.value==kind).sources[0]
    return w.raw_folder/item.item_id


def correct(w):
    path=source(w);path.write_bytes(path.read_bytes().replace(b'Synthetic',b'Corrected'))
    engine=powerbi_coordinator(w.candidate_folder)
    request=ProcessingRequest('repairs','2026-01',input_path=path)
    result=engine.preview(request)
    assert result.status=='needs_review'
    return engine.process(replace(request,replacement_token=result.replacement_token))


def test_initial_add_retry_determinism_and_integrity(tmp_path):
    w=selected(tmp_path,(1,2));before=snapshot(w.candidate_folder);raw=snapshot(w.raw_folder)
    first=plan(w,tmp_path/'first');assert first.recommendation==REBUILD
    a=generate(w,first);assert validate_dataset(a)['end']=='2026-01'
    p=plan(w,tmp_path/'second',end='2026-02',baseline=a)
    assert p.recommendation==ADD and p.added==('2026-02',) and p.unchanged==('2026-01',)
    b=generate(w,p);second=snapshot(b)
    retry=plan(w,tmp_path/'retry',end='2026-02',baseline=b)
    assert retry.recommendation==UNCHANGED and not retry.permitted
    with pytest.raises(ProcessingError,match='blocked_or_unchanged'):generate(w,retry)
    assert not (tmp_path/'retry').exists() and snapshot(b)==second
    c=generate(w,plan(w,tmp_path/'third',end='2026-02',baseline=a))
    for name in NAMES.values():
        assert (b/name).read_bytes()==(c/name).read_bytes()
        assert read(b/name)==read(a/name)+[r for r in read(b/name) if r['ReportingMonth']=='2026-02']
    assert snapshot(w.candidate_folder)==before and snapshot(w.raw_folder)==raw


def test_pending_then_committed_correction_requires_rebuild_and_explicit_change_consent(tmp_path):
    w=selected(tmp_path);a=baseline(w,tmp_path/'base');old=snapshot(a)
    path=source(w);path.write_bytes(path.read_bytes()+b'\n')
    p=plan(w,tmp_path/'pending',baseline=a)
    assert p.recommendation==REVIEW and not p.permitted and 'source changed' in p.summary()
    # No approval occurs in the update layer. Complete the existing workflow first.
    engine=powerbi_coordinator(w.candidate_folder);request=ProcessingRequest('repairs','2026-01',input_path=path)
    result=engine.preview(request);assert result.status=='needs_review'
    engine.process(replace(request,replacement_token=result.replacement_token))
    p=plan(w,tmp_path/'corrected',baseline=a)
    assert p.recommendation==REBUILD and len(p.replacements)==1 and p.changes_history
    with pytest.raises(ProcessingError,match='confirmation_required'):generate(w,p)
    with pytest.raises(ProcessingError,match='blocked_or_unchanged'):generate(w,p,mode=ADD)
    b=generate(w,p,changes_confirmed=True)
    assert snapshot(a)==old and validate_dataset(b)['complete']
    assert len(engine.store.history())==4


@pytest.mark.parametrize('fault',['candidate_missing','candidate_corrupt','source_missing','ambiguous_source','baseline_missing','baseline_corrupt','wrong_workspace','staging_baseline'])
def test_review_required_for_unverifiable_evidence(tmp_path,fault):
    w=selected(tmp_path);a=baseline(w,tmp_path/'base')
    if fault=='candidate_missing':database(w).unlink()
    elif fault=='candidate_corrupt':next((w.candidate_folder/'powerbi_candidates/versions').rglob('*.csv')).write_bytes(b'bad')
    elif fault=='source_missing':source(w).unlink()
    elif fault=='ambiguous_source':
        f=source(w);(f.parent/('copy_'+f.name)).write_bytes(f.read_bytes())
    elif fault=='baseline_missing':a=tmp_path/'absent'/'snapshot'
    elif fault=='baseline_corrupt':(a/NAMES['repairs']).write_bytes(b'bad')
    elif fault=='wrong_workspace':
        j=json.loads((a/'snapshot_manifest.json').read_text());j['configuration']='bad';(a/'snapshot_manifest.json').write_text(json.dumps(j))
    else:a=a.rename(a.parent/'.s')
    p=plan(w,tmp_path/'out',baseline=a)
    assert p.recommendation==REVIEW and not p.permitted
    with pytest.raises(ProcessingError):generate(w,p)
    assert not (tmp_path/'out').exists()


def test_no_silent_removal_and_explicit_smaller_rebuild(tmp_path):
    w=selected(tmp_path,(1,2));a=baseline(w,tmp_path/'base',end='2026-02');old=snapshot(a)
    p=plan(w,tmp_path/'out',baseline=a)
    assert p.recommendation==REVIEW and p.permitted==(REBUILD,) and p.removed==('2026-02',)
    with pytest.raises(ProcessingError,match='confirmation_required'):generate(w,p)
    b=generate(w,p,changes_confirmed=True)
    assert validate_dataset(b)['end']=='2026-01' and snapshot(a)==old


@pytest.mark.parametrize('change',['source','baseline','selection','destination','range'])
def test_stale_confirmations_cannot_write(tmp_path,change):
    w=selected(tmp_path,(1,2));a=baseline(w,tmp_path/'base');p=plan(w,tmp_path/'out',end='2026-02',baseline=a)
    if change=='source':
        f=source(w);f.write_bytes(f.read_bytes()+b'\n')
    elif change=='baseline':
        f=a/'snapshot_manifest.json';f.write_bytes(f.read_bytes()+b' ')
    elif change=='selection':correct(w)
    elif change=='destination':(tmp_path/'out').mkdir()
    else:p=replace(p,dataset=replace(p.dataset,end='2026-01'))
    with pytest.raises(ProcessingError):generate(w,p,confirmation='wrong' if change=='range' else p.confirmation(ADD))
    assert not (tmp_path/'out'/'snapshot').exists()


@pytest.mark.parametrize('stage',['confirmation','local','cancel','write','interrupt'])
def test_confirmation_cancel_failure_cleanup_and_prior_output_preservation(tmp_path,monkeypatch,stage):
    w=selected(tmp_path,(1,2));a=baseline(w,tmp_path/'base');old=snapshot(a);store=snapshot(w.candidate_folder)
    p=plan(w,tmp_path/'out',end='2026-02',baseline=a);kw={}
    if stage=='confirmation':kw['confirmation']=''
    elif stage=='local':kw['local_confirmed']=False
    elif stage=='cancel':
        stop=Event();stop.set();kw['cancelled']=stop
    else:
        def fail(*a,**kw):raise (KeyboardInterrupt() if stage=='interrupt' else OSError('simulated interrupted write'))
        monkeypatch.setattr('equipment_data_manager.historical_dataset._write',fail)
    with pytest.raises((ProcessingError,OSError,KeyboardInterrupt)):generate(w,p,**kw)
    assert not (tmp_path/'out').exists() and snapshot(a)==old and snapshot(w.candidate_folder)==store


def test_missing_month_and_destination_collision_preserve_no_zero_policy(tmp_path):
    w=selected(tmp_path);p=plan(w,tmp_path/'out',end='2026-02')
    assert p.recommendation==REVIEW and all(s.rows is None for s in p.dataset.selections if s.month=='2026-02')
    (tmp_path/'collision').mkdir();(tmp_path/'collision'/'keep').write_text('unchanged')
    p=plan(w,tmp_path/'collision');assert not p.permitted
    assert (tmp_path/'collision'/'keep').read_text()=='unchanged'
