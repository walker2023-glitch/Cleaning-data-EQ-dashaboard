# Windows prototype packaging and distribution

## Microsoft 365 dependency check

The all-extras Windows build now includes the optional official MSAL/requests
components, controller and certifi CA roots. CI invokes the actual executable with
--check-m365-components to write a no-auth/no-network JSON report, then runs the
existing GUI/restart/approval smoke. This feature branch's pushes schedule both
OS tests and Windows build/checks even if PR API creation is blocked.

No real IT config, cache, receipt or report is bundled. The blank
m365-test.example.toml and manual pilot guide accompany the ZIP. Local Linux import/
wheel checks do not establish Windows executable readiness: inspect the exact-head
hosted result and managed-PC/dependency/security behavior before distribution.
Desktop live controls remain disabled. See m365_readonly_pilot.md.

## Approval UX / identity build

Build feature/approval-ux-identity-readiness at its reviewed commit. Windows CI
schedules packaging/executable smoke on this branch's pushes as well as PRs. The
smoke checks the readable overview, disabled identity/approval/publish controls,
and January restored in a fresh process with processing confirmation unchecked.
Settings saves use version 2; retain a private profile backup before older-build
rollback. Hosted Windows evidence is separate from local Linux tests and remains
unverified until actual check results are available. See approval_ux_identity_readiness.md.

## Approval foundation build

Build feature/approval-publishing-foundation at its exact reviewed commit. The new
review module/page is imported through the desktop and the offline employee guide
remains bundled. approval_publishing_foundation.md is copied into the review ZIP.
No local request database, candidate data, tenant settings or identity evidence is
bundled. Windows/Linux CI includes the offline installed-wheel request demonstration;
this branch's pushes also schedule Windows executable build/smoke. Inspect actual
hosted results before claiming success. A managed-PC reviewer-role/signing pilot
remains required; final approval/Publish remain disabled in every build.

## Integration build gate

Build the **integration/stable-baseline** commit and record its full SHA; an older
v0.2.0 ZIP does not update when Git branches change. Windows build and executable
smoke are not yet independently verified for this integration. Linux source smoke
is not Windows packaging evidence. CI now schedules the existing Windows build and
actual executable smoke on integration pushes as well as PRs/manual dispatch.
Hosted results must be inspected; API access is currently proxy-blocked.

Run the isolated full suite with
`uv run --frozen --all-extras python .github/run_tests.py`, then build and run the
packaged check below. Require schema-v2 fields and companion summary, intact legacy
history/corrections, monthly packet, Settings/restart, Guided Help, displayed sync
caveat and disabled Graph. The smoke asserts these structural checks; manually test
ordinary employee interaction/scaling on a second managed PC without Python/Git/
VS Code. Use only synthetic or approved private local inputs. Do not distribute a
failed/unverified build or bypass endpoint policy. See integration_baseline.md.

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

Normalized export follow-up: the packaged-window smoke also previews/processes
Repair History, Service Orders and TMA Work Orders in Power BI CSV candidate mode,
checks the header-first output and publication-blocked warning, and retains its
legacy revision checks. No new dependency is needed for the exporter. Download
only a successful build for this feature PR; earlier 0.2.0 artifacts do not gain
new code when a separate Git checkout is updated. The feature still requires
managed-PC testing and approval before employee distribution/publication.

## Monthly workflow build follow-up

The same build script packages the new local monthly modules; no Graph/auth SDK
or secret is added. The executable smoke now also loads a synthetic workspace,
discovers all three January report types, previews/processes them together, exports
a candidate packet and verifies the approved folder is untouched. Only a successful
Windows build and this executable smoke at the PR head justify using that build
for a review pilot. A previously downloaded ZIP is not updated by switching Git
branches. Supply a private local workspace TOML separately; never bundle tenant
configuration or raw/cleaned departmental reports into the application ZIP.

## Visual settings and Guided Mode build

The packaged app includes an offline Employee guide resource. START_HERE.md and
supplementary settings/monthly/guidance documents with synthetic UI screenshots
are included in the ZIP. No local preferences or departmental paths/data are
bundled. Normal first launch opens Settings and later restores profile preferences.
The packaged smoke now also saves settings/preferences, opens F1/Employee guide,
and starts a fresh executable instance using the same synthetic local preferences.
Use the successful settings-guided-mode PR artifact, not an older v0.2.0 ZIP.
The versioned prototype artifact name stays v0.2.0; identify a review build by its
PR head/checksum. This is not authorization for general employee distribution.
