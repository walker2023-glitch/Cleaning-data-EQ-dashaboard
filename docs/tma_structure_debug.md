# Debug May XLS structure rejection without exposing report data

## Finding and evidence boundary

The exact owner-described workbook passes all six original structural predicates
in an invented native-date-cell fixture: BIFF 80, one exact sheet, 85 rows, four
columns, timestamp cell type 3, title/separator/headers and 81 May records.
The code correctly compares **xlrd BIFF version 80**, not 8 or the string "80".
Native date cells (3) and numeric serial cells (2) use xlrd's workbook datemode.
No BIFF-version or timestamp relaxation is required.

A reproducible defect was found in the reader's **formatting_info=True** geometry.
That setting is needed to preserve numeric identifiers' leading-zero display
formats, but also includes BIFF formatting-only BLANK cell records that default
xlrd omits. A synthetic file demonstrates:

| Inspection | Default xlrd | App's old formatting reader | Old outcome |
|---|---|---|---|
| Native date cell, 81 records, no style edges | 85 × 4 | 85 × 4 | Passes |
| Same records plus a formatting-only fifth column | 85 × 4 | 85 × 5 | Exact reported structural rejection |
| Same records plus formatting-only rows through row 101 | 85 × 4 | 101 × 4 | Source record count inflated by blank style rows |

For the fifth-column case, the failed predicates were `physical_columns != 4`
and `raw.shape[1] != 4`. For an independently parsed frame, the remaining guards
are XLS extension, exact sheet name, at least five rows and row-count alignment.
The generation/title/separator/header/date gates run *after* that compound guard;
they cannot cause its old generic error message.

**This reproduces the defect, not proof that the private May file contains those
style records.** The actual workbook has not been read here. Owner inspection may
have used default formatting_info=False. Run the private diagnostic below to
confirm its geometry and loaded code. If all predicates pass, investigate a stale
process/branch/package/executable instead of bypassing validation.

## Focused fix and diagnostics

- Keep formatting_info=True and its ID number formats. For the timestamped layout
  only, calculate content bounds by excluding trailing XL_CELL_EMPTY (0) and
  XL_CELL_BLANK (6) style cells, then bound the parsed frame to that content.
- Do not remove internal rows or any typed data. Text (including whitespace),
  numeric zero and boolean False in a fifth column still fail. The original bytes,
  record/date exclusions, repeated transactions and retained-month check remain.
- Emit one specific category per structural predicate: extension, sheet name,
  content-column count, parsed-column count, minimum rows or row-count alignment.
  Unknown actual names, titles, headers and employee cells are never put in errors.
- `tma_structure_diagnostic` performs a write-free local preview from captured bytes.
  It reports formatting/content/parsed dimensions, BIFF version, sheet count,
  timestamp cell type/datemode, pass/fail conditions and safe categories/counts.
  It does **not** print source paths/names/hashes, actual titles/headers, dates,
  work-order IDs, requestors or descriptions. The separate --runtime command
  intentionally reports the loaded Python/module paths and module hash.
- Settings → Advanced Settings now identifies the actual TMA module path and
  diagnostic build marker `tma-structure-v1-content-bounds` in the running window.

Cleaner identity is **tma-workbook-v3.1**, so any reprocessing can require explicit
correction acknowledgement. Existing revisions remain. No month-validation,
financial schema-v2, cleaning formula or approval-state change is introduced.
Classic XLS/XLSX layouts retain their existing validation. The bundled June
synthetic XLS now includes formatting-only edges so executable smoke exercises
this defect, not just an ordinary worksheet.

## Exact Windows commands: prove which code is loaded

Close old application windows first. A downloaded v0.2.0 ZIP is not a Git checkout;
git switch/uv sync there cannot update its executable. In VS Code open the cloned
repository, then use its PowerShell terminal (adjust the first path if your clone
is elsewhere):

```powershell
Set-Location (Join-Path $HOME 'Cleaning-data-EQ-dashaboard')
if (-not (Test-Path .git)) { throw 'Open the cloned repository, not the downloaded executable directory.' }
git fetch origin
git switch --track origin/feature/tma-structure-diagnostics
git branch --show-current
git rev-parse HEAD
git status --short
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python -m equipment_data_manager.tma_structure_diagnostic --runtime
```

If already tracked, use `git switch feature/tma-structure-diagnostics` and
`git pull --ff-only`. Do not discard local modifications automatically. If sync
reports a locked launcher, close the running app and retry; retain all history.

The runtime JSON must show:

- diagnostic_build: `tma-structure-v1-content-bounds`;
- cleaner_version starting `tma-workbook-v3.1:`;
- xlrd_version 2.0.2 and pandas_version 2.2.3;
- python_executable in this checkout's `.venv`, and module_path under this checkout's
  `src/equipment_data_manager/processing/work_orders.py` for the editable install.

An additional command works even if an older package lacks the diagnostic module:

```powershell
python -m uv run --frozen --all-extras python -c "import sys,pathlib,hashlib; import equipment_data_manager.processing.work_orders as m; p=pathlib.Path(m.__file__).resolve(); expected=pathlib.Path('src/equipment_data_manager/processing/work_orders.py').resolve(); print('python=',sys.executable); print('loaded_module=',p); print('matches_checkout=',p==expected); print('build=',getattr(m,'STRUCTURE_DIAGNOSTIC_VERSION','MISSING-OLDER-BUILD')); print('cleaner=',m.TmaXlsxCleaner().version); print('module_sha256=',hashlib.sha256(p.read_bytes()).hexdigest())"
Get-FileHash -Algorithm SHA256 src/equipment_data_manager/processing/work_orders.py
Get-Process | Where-Object { $_.ProcessName -like '*equipment-data-manager*' -or $_.ProcessName -like '*EquipmentDataManager*' } | Select-Object Id,ProcessName,Path
```

Module SHA and checkout file SHA should match (case-insensitive hex). **Git HEAD
alone is not proof of loaded code**: a modified working tree, another Python
installation, installed wheel or already running executable can differ. The
commands describe the newly invoked Python process, not a previously launched GUI.
Check running process paths locally; do not publish private environment paths.
Restart the GUI using this verified project command:

```powershell
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app --settings-file data/may-structure-test/settings.toml
```

In that window, Settings → Advanced Settings must show the new build marker and
TMA module path. An old downloaded executable is not updated by a repository
switch. Do not infer a release's commit from the shared 0.2.0 label; use the
specific reviewed CI artifact/checksum and require native Windows tests before
employee distribution. No speculative executable commit is reported by the app.

## Read-only diagnostic on the private May original

From the same verified checkout/terminal:

```powershell
$mayPath = Read-Host 'Full private path to the original May XLS (kept local)'
python -m uv run --frozen --all-extras python -m equipment_data_manager.tma_structure_diagnostic --input $mayPath --period 2026-05
```

This reads stable local bytes through the existing provider and performs the same
cleaner preview in memory. It creates no CSV, SQLite, review request or token cache.
Keep its output private. No credential, employee data or original file is needed
in GitHub; share only authorized build markers, category/condition names and counts.

Interpretation:

- BIFF 80/type 3 with content/parsed 85 × 4 and formatting dimensions larger:
  confirms formatting-only edges. Expect `tma_formatting_only_edges_ignored` and
  81 source/retained records if original exclusion rules do not remove any.
- Every `structure_checks` entry has `passed: true`, followed by another failure:
  inspect `failure_code` and named timestamp/title/separator/header checks. The
  original compound structural guard is not the remaining failure.
- All checks and preview pass here but the GUI still shows the old generic layout
  error: the GUI is running different/older code. Check its process path/build
  marker and restart the verified source command. The new guard uses specific
  failure messages, not the old catch-all structural message.
- A false content-column check: there is actual typed data outside four columns;
  the app continues to reject it. Do not delete columns, change dates or rename
  source files to force acceptance. Inspect privately and provide only an approved
  sanitized structural example if further adapter work is needed.

After the diagnostic passes, repeat the full May acceptance in
tma_timestamped_layout.md using a NEW trusted-local candidate directory. Confirm
85 content rows, 81 source records, 81 parseable May dates, retained count subject
to original exclusions, leading zeros/repeated records and missing assignments.
Compare original hash before/after; original dates remain May 1 05:01–May 29 16:25
according to the owner's independent observations. No candidate is approved or
published. A larger formatting dimension is not an extra transaction count.
June uses the same checks, with July generation and June request dates; inspect
its own counts independently. Real May preview/output acceptance remains owner-manual.

## Regression and delivery boundary

The synthetic fixtures reproduce default-xlrd 85 × 4 with native date type 3,
formatting-only row/column edges, and genuine data in extra columns. Tests cover
all six condition categories, safe diagnostics, unchanged source hashes and
no-output preview, plus all existing timestamp/title/header/month/footer gates.
Final Linux regression: **754 passed, 0 failures, 0 errors, 0 skips**, retaining
all 731 previous cases. Wheel/sdist builds, installed-wheel diagnostics/81-record
processing and source/installed-wheel phase-36 desktop/restart passed. These are
synthetic/offline Linux results, not actual May or native Windows acceptance.
The actual departmental file was not committed, converted, renamed or modified.

Branch feature/tma-structure-diagnostics starts at timestamped-layout **3b00a95**;
main remains bd21499 at inspection. It depends on the unmerged timestamped,
legacy-TMA and discovery branches. The PR targets feature/tma-timestamped-layout;
no feature is merged automatically. GitHub API still returns HTTP 403, so open PR
metadata/hosted Windows/Linux/native packaging outcomes cannot be claimed here.
The branch push config includes native build, formatting-aware executable smoke
and installed-wheel diagnostics/processing. See testing.md for actual local results.
