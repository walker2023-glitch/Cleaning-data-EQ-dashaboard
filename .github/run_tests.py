"""Preserve pytest's outcome and surface synthetic CI failures as annotations.

Useful when the Actions log download route is unavailable to the review environment.
The test suite uses synthetic fixtures only; never use this with private exports.
"""

from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree

root = Path(__file__).resolve().parents[1]
report = root / "data/ci-test-results.xml"
report.parent.mkdir(parents=True, exist_ok=True)
report.unlink(missing_ok=True)
completed = subprocess.run([sys.executable, "-m", "pytest", f"--junitxml={report}"], cwd=root)
if completed.returncode and report.exists():
    for testcase in ElementTree.parse(report).iter("testcase"):
        for category in ("failure", "error"):
            for failure in testcase.findall(category):
                text = (failure.text or failure.get("message", "Test failed"))[-6000:]
                escaped = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                print(f"::error title={testcase.get('name', 'Test failure')}::{escaped}")
raise SystemExit(completed.returncode)
