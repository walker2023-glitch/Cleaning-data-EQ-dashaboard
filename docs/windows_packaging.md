# Windows prototype packaging and distribution

Build **on Windows** using the pinned Python 3.12.14 and uv 0.12.23. PyInstaller
does not cross-compile a Windows executable from Linux. The build is an unsigned
review prototype until Windows checks and the managed-PC pilot have completed.

From the repository root in PowerShell:

```powershell
uv python install 3.12.14
uv sync --frozen --all-extras
uv run --frozen --all-extras pytest
./packaging/build.ps1
```

`build.ps1` produces an onedir application, a versioned ZIP and a SHA-256 checksum
under ignored `dist/`. Keep the complete application folder; the executable needs
its `_internal` resources. The specification explicitly includes CustomTkinter
assets and M1's source-hash resources. Only invented CSV samples are bundled.
No organizational config, credentials, tokens, output history or departmental data
is included. Inspect ZIP contents before distribution; keep builds in a clean checkout.

For an automated packaged-window check:

```powershell
$checkDir = Join-Path $PWD "data/packaged-smoke"
$process = Start-Process "dist/EquipmentDataManager/EquipmentDataManager.exe" -ArgumentList @("--smoke-test", "--smoke-dir", $checkDir) -PassThru
if (-not $process.WaitForExit(120000)) { $process.Kill(); throw "Desktop smoke timed out" }
if ($process.ExitCode -ne 0) { throw "Packaged desktop check failed" }
Get-Content "$checkDir/desktop-smoke.json"
```

The JSON must report `passed`; process existence or a visible window alone is not
a passing check. Use a diagnostic path without spaces for this command, or quote
individual `Start-Process` arguments correctly for your chosen path. The diagnostic
check creates only isolated synthetic files and candidate outputs in that directory.

Windows CI runs tests, builds this ZIP and checks the actual packaged GUI with
the same smoke flow, then uploads `EquipmentDataManager-v0.2.0-Windows-prototype`.
Download the artifact from a successful PR Actions run while signed into GitHub,
extract its outer artifact ZIP, then extract the versioned application ZIP.
Automated build/smoke evidence is recorded in PR results; do not infer readiness
merely from the existence of this configuration.

Authorized employees preview it by double-clicking `EquipmentDataManager.exe`;
no Python, VS Code or terminal should be needed for that packaged workflow.
See `user_guide.md` (also copied into the application as `START_HERE.md`).

Before an employee release, test the extracted ZIP on a separate IT-managed
Windows 10/11 PC without Python, with standard-user privileges and typical display
scaling/keyboard navigation. Verify native dialogs, large files/progress, cancellation,
correction review, restricted folder errors, sample outputs and retained revisions.
Obtain IT approval for signing, endpoint policy, distribution/retention and support.
Never ask users to disable endpoint protection or bypass executable restrictions.

Publishing to a departmental SharePoint release folder is a later authorized
maintainer action. This task does not upload anything there. If approved later,
distribute the complete versioned ZIP, checksum, release notes and user guide;
employees download/extract locally and run the executable, not SharePoint preview.
The prototype remains offline and its production cleaning accuracy unverified.
