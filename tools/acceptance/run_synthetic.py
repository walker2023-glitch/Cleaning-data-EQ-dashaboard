"""Reusable acceptance run against one checkout, using NEW synthetic stores only.

No departmental input/store arguments are accepted. Original Tk widget tests and
phase-51 smoke are reused; Playwright is not appropriate for native Tk widgets.
"""
import argparse
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from xml.etree import ElementTree

try:from . import analyze_v3 as analyzer
except ImportError:import analyze_v3 as analyzer

M2_COMMIT='f2718b384f0c2ce7730239ee872f5da1b9d101a8'
UI_CASES=(
    'test_employee_navigation_history_refresh_and_hidden_review_foundation',
    'test_employee_correction_approval_saves_nothing_and_selection_invalidates_it',
    'test_employee_result_partial_failure_warning_and_technical_details',
    'test_employee_settings_history_and_multi_month_keyboard_help',
    'test_employee_partial_failure_completion_uses_actual_saved_and_failed_results',
)


def ui_supported(checkout):
    tree=ast.parse((checkout/'src/equipment_data_manager/ui/app.py').read_text())
    constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in ('PRIMARY_PAGES','PAGE_LABELS'):
                    constants[target.id]=ast.literal_eval(node.value)
    pages=constants.get('PRIMARY_PAGES',())
    return (tuple(pages)==('Process Reports','Results','Historical Data','Settings','Help')
        and constants.get('PAGE_LABELS',{}).get('Historical Data')=='Process Multiple Months')


def code_state(checkout):
    source=checkout/'src/equipment_data_manager'
    return {str(p.relative_to(source)):sha256(analyzer.read_bytes(p)).hexdigest()
        for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def junit_totals(path):
    root=ElementTree.parse(path).getroot()
    suites=[root] if root.tag=='testsuite' else list(root)
    return {key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')}


def execute(command,checkout,env,timeout):
    try:
        done=subprocess.run(command,cwd=checkout,env=env,capture_output=True,stdin=subprocess.DEVNULL,timeout=timeout)
        return done.returncode,'completed'
    except subprocess.TimeoutExpired:return None,'timeout'
    except OSError:return None,'unavailable'


def run(output,checkout,*,desktop=False,executable=None):
    output=analyzer.plain_path(output);checkout=analyzer.plain_path(checkout)
    if not (checkout/'examples/create_comparison_classification_demo.py').is_file():raise analyzer.Rejected('application_checkout_required')
    if checkout.is_relative_to(output):raise analyzer.Rejected('output_must_not_contain_checkout')
    if output.is_relative_to(checkout) and not output.is_relative_to(checkout/'data'):
        raise analyzer.Rejected('use_ignored_data_or_separate_workspace')
    if executable is not None:
        executable=analyzer.plain_path(executable)
        if not executable.is_file():raise analyzer.Rejected('executable_unavailable')
    before=code_state(checkout)
    output.parent.mkdir(parents=True,exist_ok=True);output.mkdir(exist_ok=False)
    env=dict(os.environ);env['PYTHONPATH']=str(checkout/'src')
    checks=analyzer.Checks()
    code,reason=execute([sys.executable,str(checkout/'examples/create_comparison_classification_demo.py'),
        '--output',str(output/'invented')],checkout,env,120)
    checks.add('invented_demo','PASS' if code==0 else 'FAIL','Fresh synthetic generation and deterministic double export.',dict(exit_code=code,execution=reason))
    if code==0:
        base=output/'invented';comparison=base/'comparison-1/comparison';canonical=base/'canonical/snapshot'
        report=analyzer.analyze(comparison,canonical)
        analyzer.write_reports(report,output/'v3-report',(comparison,canonical))
        checks.items.extend(c for c in report['checks'] if c['id']!='native_desktop')
        manifest=analyzer.document(analyzer.read_bytes(comparison/'comparison_manifest.json'))
        counts={e['report_type']:e['rows'] for e in manifest['datasets']}
        checks.invariant('synthetic_known_counts',counts==dict(repairs=18,service_orders=12,tma_work_orders=13,repair_financial_summary=6,equipment=3),
            'Invented demonstration matches independent fixed control counts.',counts)
        repair=analyzer.records(analyzer.read_bytes(comparison/'Repairs_History.csv'))
        equipment=analyzer.records(analyzer.read_bytes(comparison/'Equipment_History.csv'))
        checks.invariant('synthetic_known_nulls_and_text_ids',sum(not r['ReportedTotalCost'] for r in repair)==6
            and any(r['EquipmentId']=='E00045' for r in equipment),
            'Invented missing costs and a known leading-zero text ID survive.',dict(missing_reported_costs=sum(not r['ReportedTotalCost'] for r in repair)))
    display_ready=sys.platform=='win32' or bool(env.get('DISPLAY'))
    if desktop and display_ready:
        probe,_=execute([sys.executable,'-c','import tkinter; r=tkinter.Tk(); r.withdraw(); r.update(); r.destroy()'],checkout,env,15)
        display_ready=probe==0
    supported=ui_supported(checkout)
    if desktop and display_ready and supported:
        for i,case in enumerate(UI_CASES):
            xml=output/f'widget-{i}.xml'
            code,reason=execute([sys.executable,'-m','pytest','-q',f'tests/test_desktop_widgets.py::{case}',f'--junitxml={xml}'],checkout,env,90)
            try:totals=junit_totals(xml)
            except (OSError,ValueError,ElementTree.ParseError):totals={}
            ok=code==0 and totals==dict(tests=1,failures=0,errors=0,skipped=0)
            checks.add('ui_'+case,'PASS' if ok else 'FAIL','Existing isolated synthetic real-widget acceptance case.',dict(exit_code=code,execution=reason,**totals))
        for name,command in [('source',[sys.executable,'-m','equipment_data_manager.ui.app']),
                             *(([('packaged',[str(executable)])]) if executable else [])]:
            folder=output/f'{name}-smoke'
            code,reason=execute(command+['--smoke-test','--smoke-dir',str(folder)],checkout,env,180)
            try:
                smoke=analyzer.document(analyzer.read_bytes(folder/'desktop-smoke.json'))
                restore=analyzer.document(analyzer.read_bytes(folder/'restore-smoke.json'))
                expected_phase=55 if (checkout/'src/equipment_data_manager/monthly_update.py').is_file() else 51
                ok=code==0 and smoke.get('status')=='passed' and smoke.get('phase')==expected_phase and restore.get('passed') is True
                if expected_phase==55:
                    ok=ok and {'monthly_update_recommendation','monthly_update_explicit_confirmation','monthly_update_version_and_retry'}<=set(smoke.get('checks',[]))
            except (OSError,ValueError):ok=False;smoke={};restore={}
            checks.add('desktop_'+name,'PASS' if ok else 'FAIL','Complete desktop smoke (including monthly updates when available) and fresh-process settings restart.',
                dict(exit_code=code,execution=reason,phase=smoke.get('phase'),restart_passed=restore.get('passed',False)))
    else:
        checks.add('desktop_source','NOT TESTED','Desktop checks need --desktop, a usable display and the Milestone 2 interface in the selected checkout.',
            dict(requested=desktop,display_available=display_ready,m2_interface_present=supported),action='Select the pinned Milestone 2 checkout and an available Windows desktop or Linux virtual display.')
    if executable is None:
        checks.add('desktop_packaged','NOT TESTED','No packaged executable supplied.',action='Build the selected checkout on its native platform and pass --executable.')
    if sys.platform!='win32':checks.add('native_windows','NOT TESTED','This run is not native Windows; Linux results are separate evidence.',action='Run the Windows workflow/checklist at the selected commit.')
    checks.invariant('application_source_unchanged',code_state(checkout)==before,'Application source/resources remained byte-identical; only new synthetic stores/reports were used.')
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()
    except (OSError,subprocess.CalledProcessError):commit='unavailable'
    try:
        clean=not subprocess.check_output(['git','status','--porcelain','--','src','tests','examples','packaging'],cwd=checkout,text=True).strip()
    except (OSError,subprocess.CalledProcessError):clean=False
    checks.add('application_tree_provenance','PASS' if clean else 'REVIEW','Selected source/tests/examples/packaging match recorded Git HEAD.' if clean else 'Selected source/tests/examples/packaging have uncommitted changes or provenance is unavailable.',action='Use a clean reviewed application checkout for reproducible acceptance evidence.')
    counts={status:sum(c['status']==status for c in checks.items) for status in analyzer.STATUSES}
    result=dict(report_schema='edm-synthetic-acceptance-v1',overall='FAIL' if counts['FAIL'] else 'REVIEW',
        application_commit=commit,application_tree_clean=clean,platform=platform.system(),python=platform.python_version(),business_approved=False,
        executable_sha256=sha256(analyzer.read_bytes(executable)).hexdigest() if executable else None,
        counts=counts,checks=checks.items,executive_summary='Synthetic checks only. '+', '.join(f'{v} {k}' for k,v in counts.items())+'. No business approval.')
    analyzer.write_reports(result,output/'run-report',())
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-checkout',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path,required=True,help='NEW synthetic-only workspace; never reuse an existing store')
    parser.add_argument('--desktop',action='store_true')
    parser.add_argument('--executable',type=Path)
    args=parser.parse_args(argv)
    try:r=run(args.output,args.app_checkout,desktop=args.desktop,executable=args.executable)
    except (OSError,ValueError,SyntaxError):
        print('Synthetic workspace or selected checkout unavailable; no existing store was reused.',file=sys.stderr);return 2
    print(r['executive_summary'])
    if r['counts']['FAIL']:return 1
    if args.desktop and any(c['status']=='NOT TESTED' and c['id']=='desktop_source' for c in r['checks']):return 3
    return 0


if __name__=='__main__':raise SystemExit(main())
