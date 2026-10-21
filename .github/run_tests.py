"""Run every synthetic test and surface failures as annotations.

Windows GUI cases use fresh processes: each case owns one Tcl interpreter, just
like an application launch. Repeated Tk destruction/recreation in one process
has produced intermittent init.tcl/tk.tcl loading errors on the Windows runner.
No test is skipped or retried, and all subprocess outcomes are preserved.
"""

import argparse
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--isolate-gui', action='store_true', help='Use Windows-style GUI isolation on other platforms')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
report = root / 'data/ci-test-results.xml'
report.parent.mkdir(parents=True, exist_ok=True)
report.unlink(missing_ok=True)
commands = [(None, [])]
if sys.platform == 'win32' or args.isolate_gui:
    widget_file = 'tests/test_desktop_widgets.py'
    collected = subprocess.run(
        [sys.executable, '-m', 'pytest', '--collect-only', '-q', widget_file],
        cwd=root, capture_output=True, text=True,
    )
    if collected.returncode:
        print(collected.stdout)
        print(collected.stderr)
        raise SystemExit(collected.returncode)
    cases = [line.strip() for line in collected.stdout.splitlines() if line.startswith(widget_file + '::')]
    if not cases:
        raise SystemExit('No GUI test cases collected; refusing to omit them')
    print(f'Running all {len(cases)} GUI cases in fresh processes (no retries).', flush=True)
    commands = [('core', [f'--ignore={widget_file}'])]
    commands += [(f'widget-{index}', [case]) for index, case in enumerate(cases)]

combined = ElementTree.Element('testsuites')
exit_code = 0
for label, arguments in commands:
    part = report if label is None else report.with_name(f'ci-tests-{label}.xml')
    part.unlink(missing_ok=True)
    completed = subprocess.run([sys.executable, '-m', 'pytest', f'--junitxml={part}', *arguments], cwd=root)
    if completed.returncode:
        exit_code = completed.returncode
    if not part.exists():
        exit_code = exit_code or 1
        continue
    parsed = ElementTree.parse(part)
    combined.extend(parsed.getroot())
    if completed.returncode:
        # Synthetic fixtures only. Never use this runner with private exports.
        for testcase in parsed.iter('testcase'):
            for category in ('failure', 'error'):
                for failure in testcase.findall(category):
                    text = (failure.text or failure.get('message', 'Test failed'))[-6000:]
                    escaped = text.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
                    print(f"::error title={testcase.get('name', 'Test failure')}::{escaped}")
ElementTree.ElementTree(combined).write(report, encoding='utf-8', xml_declaration=True)
raise SystemExit(exit_code)
