# Windows CI: export precedence and concurrent review storage

Baseline: feature/historical-batch-preview at e46bf90. The owner has accepted all
18 January–June previews on Windows. This follow-up changes filesystem validation
and local review-store coordination, not those report transformations.

## Evidence and causes

Reported run: https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard/actions/runs/42828539588

The public run page exposes the two export annotations, including actual
`WindowsPath(.../preview.csv)` inputs and historical_preview.py line 243. GitHub
API access is denied by the environment policy. The public annotations fetched
here do not include the reported parallel review traceback; the full job log
endpoint is unavailable without further access. Do not infer its exact failing
ancestor or guard from the generic review_store_unsafe code.

**Exports (confirmed):** the extension is valid `.csv`; there is no Windows suffix
parsing defect. The tests mark an ancestor as a link. Windows' trusted-location
helper detects it first and returns an unsafe-location message. Export wraps that
as historical_export_requires_local_csv_or_json before the explicit link guard.
Linux's location helper uses a mount check, so it reaches storage_path_rejected.
Both platforms previously rejected the destination; error precedence differed.

The order is now deterministic: un-followed destination/ancestor link checks,
extension, trusted-location policy, protected workspace overlap, Windows length
preflight, then exclusive write. Links win even with an invalid extension. Other
invalid extensions and untrusted destinations still fail. Tests verify no target
is opened/created, not only the error category.

**Review storage (reproduced race class; original native predicate pending):** the
old guard compares `database.resolve()` with a later `root.resolve()` while two
requests can create/open that store. Independently resolving a missing/appearing
child and parent can compare different canonical aliases of a Windows path. A
controlled Windows short/long-alias simulation reproduces review_store_unsafe at
that second guard. This is simulated evidence, not proof that this was the exact
predicate in the owner's original run. The ordinary parallel test passes locally.

There are also two directly observable coordination problems: store validation
and directory creation are not serialized between local service instances; and
`with sqlite3.connect(...)` commits/rolls back but **does not close** the connection.
Windows handles can therefore outlive an operation. Schema/trigger creation was
outside the insert transaction. These are corrected without allowing unsafe paths.

## Review-store protocol

- A shared per-store in-process reentrant lock covers request/history operations,
  including directory validation/creation. Different service instances share it;
  weak references avoid retaining unused stores. SQLite remains the cross-process
  arbiter, not this Python lock.
- Non-following metadata checks cover root/ancestors and the fixed direct child
  `requests.sqlite3`. Symlinks, junctions, any reparse bit, recall/cloud flags,
  unexpected node types and unavailable metadata fail closed. Normal Windows
  directory/archive/temporary/not-content-indexed attributes are not reparse flags.
- The existing local/fixed-disk/network/sync location policy remains mandatory.
  Directory creation is followed by a second safety check before opening SQLite.
- A constant child name under checked ancestors replaces the racy comparison of
  two separately resolved aliases. No dynamic filename or caller-supplied database
  location is accepted. An existing database must be an ordinary, nonredirected file.
- BEGIN IMMEDIATE now covers schema, append-only triggers, dedup lookup and insert.
  The UNIQUE dedup key and verified-record hashes remain unchanged. A fault before
  complete schema creation rolls back; a later request can recover.
- Connections close deterministically after commit/rollback, including early
  duplicate returns, history reads and exceptions. No review_store_unsafe is ignored.
- A remaining unsafe-path failure retains that error code and adds a privacy-safe
  exception note with reason, ancestor depth, attribute mask and WinError number
  when available. No filesystem path, employee data or raw exception text is added.
  The full original traceback or these new notes are needed to establish any
  remaining native predicate precisely.

Checks are conservative preflight within trusted local storage, not a guarantee
against a malicious local administrator changing the filesystem between syscalls.
This does not create authenticated approval, publish authority or enterprise audit.

## Exact Windows reproduction and acceptance

Close the application before dependency synchronization. Run from the Git clone,
with a clean/preserved local worktree, rather than the Downloads prototype folder.

```powershell
cd "$env:USERPROFILE\Cleaning-data-EQ-dashaboard"
git fetch origin
git switch feature/historical-batch-preview
git pull --ff-only
git rev-parse HEAD
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras pytest 'tests/test_historical_preview.py::test_export_rejects_linked_destination_ancestors[is_symlink]' -vv --tb=long
python -m uv run --frozen --all-extras pytest 'tests/test_historical_preview.py::test_export_rejects_linked_destination_ancestors[is_junction]' -vv --tb=long
python -m uv run --frozen --all-extras pytest tests/test_review_requests.py::test_parallel_requests_create_one_append_only_record -vv --tb=long
python -m uv run --frozen --all-extras pytest tests/test_windows_ci_safety.py tests/test_review_packet_paths.py -vv --tb=long
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv build
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app --smoke-test --smoke-dir data/windows-ci-fix-source
python -m uv run --isolated --no-project --with './dist/equipment_data_manager-0.2.0-py3-none-any.whl[desktop,microsoft]' python -I -m equipment_data_manager.ui.app --smoke-test --smoke-dir data/windows-ci-fix-wheel
.\packaging\build.ps1
$dir = Join-Path $PWD 'data/windows-ci-fix-packaged'
$p = Start-Process -FilePath '.\dist\EquipmentDataManager\EquipmentDataManager.exe' -ArgumentList @('--smoke-test','--smoke-dir',$dir) -PassThru
if (-not $p.WaitForExit(120000)) { $p.Kill(); throw 'Packaged smoke timeout' }
if ($p.ExitCode -ne 0) { throw 'Packaged smoke failed' }
Get-Content "$dir/desktop-smoke.json"
Get-Content "$dir/restore-smoke.json"
```

Require all tests and both smoke reports to pass, not merely a window launch.
A native Windows case creates a real disposable directory junction using mklink /J
(no symlink privilege required); Linux exercises a real directory symlink. Neither
test follows the redirected store or writes to its target. No test is disabled.

Linux full-suite command adds `--isolate-gui` and requires a display/Xvfb. Keep
source, wheel and packaged GUI smoke runs sequential on a shared display. The
review-packet MAX_PATH regression cases remain intact; that packet writer is not
modified. Check hosted Windows packaging results before merging. No automatic
merge or production changes are part of this fix.
