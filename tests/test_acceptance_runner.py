"""Synthetic runner safety, environment reporting and result handling."""
from pathlib import Path
import subprocess
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.acceptance import run_synthetic as runner
from tools.acceptance import analyze_v3 as analyzer


def test_static_capability_check_does_not_guess_milestone_2(tmp_path):
    path=tmp_path/'src/equipment_data_manager/ui';path.mkdir(parents=True)
    f=path/'app.py';f.write_text('PRIMARY_PAGES=("History","Review & Approval")\nPAGE_LABELS={}\n')
    assert not runner.ui_supported(tmp_path)
    f.write_text('PRIMARY_PAGES=("Process Reports","Results","Historical Data","Settings","Help")\nPAGE_LABELS={"Historical Data":"Process Multiple Months"}\n')
    assert runner.ui_supported(tmp_path)


def test_fresh_data_only_run_does_not_claim_desktop_or_business_acceptance(tmp_path):
    checkout=Path(__file__).resolve().parents[1]
    before=runner.code_state(checkout)
    result=runner.run(tmp_path/'new',checkout)
    assert result['counts']['FAIL']==0 and not result['business_approved']
    assert next(c for c in result['checks'] if c['id']=='desktop_source')['status']=='NOT TESTED'
    assert (tmp_path/'new/v3-report/acceptance.md').is_file()
    assert (tmp_path/'new/run-report/acceptance.json').is_file()
    assert runner.code_state(checkout)==before
    with pytest.raises(FileExistsError):runner.run(tmp_path/'new',checkout)


@pytest.mark.parametrize('where',['source','ancestor','missing_executable'])
def test_no_generated_workspace_can_overlap_application_code(tmp_path,where):
    checkout=tmp_path/'app';(checkout/'examples').mkdir(parents=True)
    (checkout/'examples/create_comparison_classification_demo.py').write_text('')
    if where=='source':target=checkout/'src/new-output'
    elif where=='ancestor':target=tmp_path
    else:target=tmp_path/'new'
    with pytest.raises(analyzer.Rejected):runner.run(target,checkout,executable=tmp_path/'missing.exe' if where=='missing_executable' else None)
    assert not (target/'invented').exists()


def test_subprocess_timeout_and_unavailable_are_not_success(monkeypatch,tmp_path):
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired('synthetic',1)
    monkeypatch.setattr(subprocess,'run',timeout)
    assert runner.execute(['dummy'],tmp_path,{},1)==(None,'timeout')
    def missing(*args,**kwargs):raise OSError('Private environment path')
    monkeypatch.setattr(subprocess,'run',missing)
    assert runner.execute(['dummy'],tmp_path,{},1)==(None,'unavailable')


def test_junit_failures_and_skips_are_preserved(tmp_path):
    path=tmp_path/'test.xml'
    path.write_text('<testsuites><testsuite tests="3" failures="1" errors="0" skipped="1"/></testsuites>')
    assert runner.junit_totals(path)==dict(tests=3,failures=1,errors=0,skipped=1)


def test_no_display_is_not_misreported_as_an_application_defect(tmp_path,monkeypatch,capsys):
    monkeypatch.delenv('DISPLAY',raising=False)
    monkeypatch.setattr(runner.sys,'platform','linux')
    monkeypatch.setattr(runner,'run',lambda *args,**kwargs:dict(executive_summary='Not tested',counts={'FAIL':0},checks=[dict(id='desktop_source',status='NOT TESTED')]))
    assert runner.main(['--desktop','--output',str(tmp_path/'new')])==3
    assert 'Not tested' in capsys.readouterr().out
