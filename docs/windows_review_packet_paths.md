# Windows review-packet staging investigation

## Exact integration audit

The owner shared integration/historical-tma-complete. Fetched commit:
**1c63644b9da1d0e21345db936fcd36b270af9a1e**, with parents
**f416ce1309f233e2f447e48f77db37e5da0599f5** (main after PR #19) and
**3711aed2755f04a3eb8ec79fdff0d563c2fb88f3** (structure diagnostics).
Its tree **e03c70dc51705968c917f8c237b515475c9789dd** contains all four historical
feature histories and matches the source tree previously audited. Main contains
discovery/legacy/timestamped work; structure diagnostics is the remaining feature.

The focused branch **feature/windows-review-packet-fix** starts directly from
1c63644. The patch was applied without merging branches or changing main or the
integration branch. An isolated detached worktree at the exact unmodified commit
was used for baseline reproduction; its actually loaded monthly.py path was checked.

## Reproduced cause versus actual Windows confirmation

The summary parent is created immediately before writing. The temporary packet
root is also created exclusively before entering the write loop. Under ordinary
serial execution, the parent exists when the summary is opened. A subsequent
failure invokes cleanup, so **checking parent existence after the exception is
not evidence that creation failed**: the handler intentionally removed staging.

The owner supplied the complete failing path (not committed here). It measures
**260 characters / UTF-16 units before the terminating null**, requiring 261 units
under a classic MAX_PATH=260 API. The parent is **214 units**, within the directory
budget. The traceback reports Errno 2 and no separate WinError; no WinError number
is inferred. The reported write is the longest packet target: long pytest/user temp root +
synthetic-review/candidates/review_packets + .staging-32hex +
repair_financial_summary + CompuClean_RepairFinancialSummary_YYYY-MM.csv.
A same-length anonymized Windows root reproduces exactly a 260-unit target while
its parent remains short enough to create. Classic Win32 limits can report this as
FileNotFoundError/WinError 3 even though the parent exists. Permissions normally raise PermissionError. No permission or external-deletion
problem was observed in the controlled reproduction. Native Windows confirmation
remains necessary to verify the owner environment after this path-budget fix.

A controlled test ran the REAL exporter loaded from the exact unmodified 1c63644
checkout, emulating the classic Win32 open limit with an anonymized same-length
path. It recorded `parent_exists_at_open=true`, target length 260 and the same
FileNotFoundError. The source's normal exception handler cleaned its own stage;
all three source revisions remained. Repeating on a short root succeeded (147-unit
summary path). The patched exporter at the same original boundary succeeded with
a 248-unit staging path and readable final summary; original source bytes and
prior revisions remained. This reproduces the precise source/path-budget cause,
not a native Windows kernel run on this Linux execution host.

All four reported widget cases were also run, in fresh processes, on unmodified
1c63644 under Linux and passed. This distinguishes the Windows path boundary from
an unconditional missing-directory bug. No test was disabled or skipped. The
original/default Windows run and shorter-root comparison below remain the native
acceptance check; no OS policy/registry modification is required.

Example path budget for a 132-unit candidate root (ASCII example):

| Target | Old | New |
|---|---:|---:|
| Staged summary file | 260 units | 248 units |
| Final summary read path | 259 units | 253 units |

Long-path behavior depends on the Windows process/OS policy. This fix does not
change registry settings, permissions or machine policy, and does not pretend
unbounded paths are supported.

## Focused implementation and safety

- Encode every UUID bit as 26 lowercase base32 characters rather than 32 hex
  characters. This retains the same UUID entropy and is unambiguous on Windows
  case-insensitive filesystems. No truncation or uppercase/lowercase collision
  shortcut is used. Engine candidate/revision IDs are unchanged.
- Staging names are now `.s-<id>`; final names remain `YYYY-MM-<id>`. Older packets
  remain readable because consumers use packet.json and relative dataset paths,
  not a fixed UUID-directory regex. No existing packet is renamed or migrated.
- On Windows, preflight BOTH staging and final file/read paths using UTF-16 units
  and conservative 260-file/248-directory bounds before creating packet folders.
  If a configured root is still too deep, show review_packet_path_too_long and ask
  for a shorter trusted-local candidate location. Do not create a packet that
  stages successfully but cannot be read after its final rename.
- Keep every dataset folder, CSV filename, manifest/hash/revision binding, schema,
  financial value and CandidateUnverified/production_ready=false status unchanged.
- Keep staging hidden, current-candidate read transaction/hash verification and a
  single final local directory rename. Final destination collisions fail rather
  than replacing an existing packet. No approved output is created.
- Summary copies now use exclusive binary creation, flush and fsync before the
  manifest/final rename, matching the existing primary CSV write protection.
- On summary/manifest/rename failure, clean only this operation's staging directory.
  Existing packets, raw reports, selected revisions and previous history remain.
  A hard process/power interruption may still leave hidden .s- or older .staging-
  directories: neither is a completed packet and neither should be ingested.

Source/candidate folder permissions and third-party interference still matter.
No retry blindly removes existing destinations or weakens integrity checks.

## Windows comparison: ordinary versus shorter temporary roots

Use the cloned repository in VS Code. Close old app windows before uv updates
locked launchers. Keep raw departmental data out of automated tests.

First on the owner's existing integration branch, record the exact baseline:

```powershell
git branch --show-current
git rev-parse HEAD
git show --no-patch --format="%H %P" HEAD
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
```

Record the full synthetic failing target path/WinError privately. Count its Windows
UTF-16 units without posting the path publicly:

```powershell
$failedPath = Read-Host 'Paste the full failing synthetic target path (kept local)'
$failedPath.Length
```

Do not infer write-time parent existence from Test-Path after cleanup. Compare the
same four tests with newly allocated short test roots. Each Tk test gets a fresh
Python process, matching the existing Windows runner; no tests are skipped.

```powershell
$shortParent = Join-Path $env:LOCALAPPDATA 'edm-t'
New-Item -ItemType Directory -Force $shortParent | Out-Null
$shortRun = Join-Path $shortParent ([guid]::NewGuid().ToString('N').Substring(0,8))
if (Test-Path $shortRun) { throw 'Choose a new test-run directory; never reuse a data folder.' }
New-Item -ItemType Directory $shortRun -ErrorAction Stop | Out-Null
$cases = @(
  'test_business_review_handles_missing_month_workspace_and_stale_source',
  'test_business_review_background_operation_remains_responsive_and_fails_safely',
  'test_review_month_selector_invalidates_evidence_and_invalid_year_does_not_replace_saved_month',
  'test_review_tabs_are_employee_friendly_keep_technical_details_and_all_states_guarded'
)
$index = 0
foreach ($case in $cases) {
  $base = Join-Path $shortRun "t$index"
  python -m uv run --frozen --all-extras pytest "tests/test_desktop_widgets.py::$case" --basetemp $base
  if ($LASTEXITCODE -ne 0) { throw "Short-root case failed: $case" }
  $index++
}
```

**pytest clears --basetemp**: use only the newly allocated synthetic directories
above. Never pass raw, candidate, approved, shared or other existing data folders.
If ordinary roots fail but these short roots pass on the SAME baseline, path
length is strongly confirmed. If both fail, inspect the actual error/permissions/
antivirus/temp-directory behavior; do not remove validation or silently accept it.

Then test the focused fix branch (do not merge main automatically):

```powershell
git fetch origin
git switch --track origin/feature/windows-review-packet-fix
# If it already exists: git switch feature/windows-review-packet-fix; git pull --ff-only
git rev-parse HEAD
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python -c "import equipment_data_manager.monthly as m; print(m.__file__); print('packet_token_length=',len(m._packet_identifier()) if hasattr(m,'_packet_identifier') else 'OLD WRITER')"
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv run --frozen --all-extras python -m equipment_data_manager.ui.app --smoke-test --smoke-dir data/packet-windows-smoke
./packaging/build.ps1
```

Run the ordinary-root full suite first; short-root reruns are diagnostic evidence,
not a replacement for passing default tests. Do not move/modify actual source
reports or delete history to resolve a test path problem. A user-configured path
still beyond safe limits should fail with the new clear error; choose a shorter
local candidate root using normal Settings, without automatic history migration.

## Regression and remaining gates

New tests cover the old parent-existing MAX_PATH failure model, shorter roots,
full UUID-bit round trip, case-insensitive-safe names, UTF-16/final-path preflight,
summary parent disappearance/permission/fsync/rename failures, staging cleanup,
immutable prior packets/revisions/raw bytes, and forced identifier collision.
Full regression on the fix based directly on 1c63644: **765 passed, 0 failures,
0 errors, 0 skips**, including all previously reported failing widget cases and
11 new path/failure cases. The four affected baseline cases also pass on Linux
at unmodified 1c63644; the exact-path reproduction log explicitly models classic
Win32 limits rather than claiming a native Linux failure. Existing financial
v2/Power BI/review/history/TMA tests remain in the full suite.
Wheel/sdist build, installed-wheel complete four-table financial-v2 pilot/
snapshot check and source/installed-wheel phase-36 desktop/restart checks passed.
An initial source smoke overlapped other Tk tests and failed at the F1-focus step;
after isolating display use, both serial smoke runs passed with no test changes.
Its original report is retained in ignored data/review-packet-exact-source-smoke;
serial success reports are in data/review-packet-serial-source-smoke and
 data/review-packet-serial-wheel-smoke. This is orchestration evidence, not a change
to application or test behavior. No financial calculations, source files,
approval or publication state changes.

Native Windows and hosted CI results remain separate verification gates. The
exact integration commit and reported target length are now verified; baseline
and fixed-code boundary reproductions use the exact 1c63644 source tree and an
anonymized Win32 limit model. GitHub API access remains HTTP 403; a Linux test or
workflow definition is not a Windows executable result. The feature push config
runs Windows/Linux tests and native packaging/smoke. Verify exact-head native
outcomes before owner integration. Do not push or merge main automatically.

After review and passing Windows checks, the owner can merge the focused fix PR
into integration/historical-tma-complete, rerun the full suite there, then handle
main through the separately authorized protected integration review. This work
performs neither integration nor main merge. No history needs to be rewritten.
