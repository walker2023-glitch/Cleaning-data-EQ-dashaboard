# January rejection investigation and Windows test steps

## Findings and limits

The same previously supplied raw January attachments were tested with the current
engine **and the actual local GUI**. No original source bytes changed. Results:

| Input | Source records | Retained | Reproduction result |
|---|---:|---:|---|
| CompuClean Repair Report CSV | 29 | 29 | Preview/process succeed for `2026-01`; every CompletedDate1 parses into January 2026 |
| CompuClean Service Orders List CSV | 29 | 29 | Preview/process succeed for `2026-01`; all scheduled/completed dates parse into January 2026 |
| TMA January XLSX | 38 | 38 | Reviewed XLSX adapter previews/processes; footer is not a work order |

**No repair record in the supplied January file is responsible for a period
mismatch under these checks.** All 29 parsed/cleaned completion dates match the
selected period. No service record is excluded in the supplied January file:

| First exclusion reason | January service count |
|---|---:|
| Missing equipment ID | 0 |
| Missing scheduled date | 0 |
| Placeholder description | 0 |
| Neither date parseable | 0 |
| Both dates outside selected period | 0 |
| Description empty after original suffix stripping | 0 |
| Description begins `delete duplicate` | 0 |
| Accepted | 29 |

The user's Windows transcript shows a successful switch/sync to the multi-month
branch. It does **not** establish an old checkout as the cause. The two reported
CSV failures remain unreproduced with those attachments. New local traces expose
the exact period, file fingerprint, record numbers and date values needed to
identify a discrepancy in the actual Windows run; no speculative parsing fix was
made. A downloaded prototype executable is separate from a Git checkout and is
not updated by fetching branches. Both previously used application version 0.2.0.

## Confirmed diagnostic gap and changes

Previously, `no_output_rows` and `output_period_mismatch` discarded the parsing
context and exclusion reasons. They now carry in-memory diagnostics through the
coordinator to the GUI even when the entire file is rejected. Successful CSV
previews also provide the same trace for comparison.

The selected result's details show the engine's confirmed month, source SHA-256,
cleaner version, input/retained counts, first-match reason counts and each source
data record's raw date values and parsed ISO dates. Record 1 means the first data
record after the CSV header, **not** physical line 2: quoted descriptions can span
lines. Dates use the same scalar pandas parsing as the original CSV cleaners;
Literal CSV date cells (including `NA`, `NULL` and blanks) are retained separately
from pandas-inferred missing values. ISO values match the existing cleaned date formatting. For repairs, a retained
row outside the confirmed month rejects the whole candidate. For services, the
existing period rule excludes rows with neither date in the selected month.

The diagnostic observer uses original helper predicates and follows the original
first-exclusion order. It never filters rows or changes calculations. Retained
counts must agree with the actual original transform or processing stops with
`diagnostic_contract_mismatch`. No date parsing, inclusion/exclusion, cost, hours,
labor rate, output schemas or original/vendored source scripts were changed.
CompuClean wrapper identity advances to `wrapper-v5-january-diagnostics`; earlier
selected months therefore need the normal correction review, never silent replacement.

Raw date cells are visible only in local GUI details or an explicitly requested
CLI trace. They are excluded from diagnostic repr/default CLI summaries and never
stored in the manifest/history. Earlier skipped revisions do not retain a date
trace; use a fresh preview output directory when investigating. No real source
file, private date trace, names, descriptions or financial amounts are fixtures.

## TMA file selection and legacy XLS

The current branch already used `TmaXlsxCleaner`; it is not a CompuClean adapter.
TMA selection now uses separate native-dialog filters: **TMA XLSX reports**
(`*.xlsx`, the default) and **Legacy XLS (unsupported)** (`*.xls`). Selecting XLSX
routes its bytes to the strict single-sheet title/header/footer adapter. Selecting
XLS returns `legacy_xls_awaiting_sample` with an explanation, no artifact and no
attempt to read it as CSV/XLSX. Never rename an extension to make it pass.

There is still no actual legacy XLS attachment to inspect. A genuine BIFF workbook
requires xlrd, while HTML or another export mislabeled XLS needs separate evidence.
The optional discovery dependency is present but no XLS layout is enabled by guess.
TMA XLSX output remains the existing requests cleaner's **provisional** title/five
columns/MM/DD/YYYY contract, not an approved production baseline.

## Test in VS Code on Windows

Close all Equipment Data Manager windows before syncing: a running console-script
launcher can cause the Access Denied update error shown in the Windows transcript.
Do not edit the installed environment or reinstall Python to address a CSV rejection.
Use the repository containing `.git`, not the extracted prototype ZIP directory.
From its VS Code PowerShell terminal:

```powershell
cd C:\path\to\Cleaning-data-EQ-dashaboard
git fetch origin
git switch feature/january-rejection-diagnostics
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app --output-dir data/january-review
```

`git switch` will track the matching origin branch on its first checkout. If the
branch already exists, fetch and update it with `git pull --ff-only` before syncing.
The test runner executes every Windows GUI case once in a fresh process, avoiding
the intermittent repeated-interpreter `tk.tcl`/`init.tcl` error seen in plain pytest.
No case is skipped or retried. The transcript's 184 passed/one Tk setup error was
this separate GUI-test problem, not a failing date or cleaning assertion.

1. Open **Help**. Confirm `January diagnostics v1`, pandas 2.2.3, the engine path
   inside this checkout, and `TMA adapter: TmaXlsxCleaner`. An older downloaded EXE
   will not acquire this marker simply because the repository branch changed.
2. **Repairs:** choose Repair Reports, select the raw January repair CSV, explicitly
   select January/2026 and confirm the month. Preview; select the result and scroll
   its details. Expect 29 accepted records and no outside-period records. The
   separate financial-disagreement warning remains; do not treat it as approval.
3. **Services:** choose Service Orders List, select the raw January service CSV,
   explicitly select/confirm January 2026 and preview. Expect 29 accepted records
   and zero exclusions. If it fails, inspect the first-match counts and record/date
   trace rather than changing a rule to force acceptance.
4. **Process** each successful preview. Raw bytes and old revisions remain unchanged.
   A corrected month requires review; an identical selected revision skips.
5. **TMA:** choose TMA Work Orders before opening Select local raw files. The default
   filter should show XLSX files. Select the January XLSX, confirm January 2026,
   preview/process and expect 38 work orders. The unsupported XLS filter lets you
   select legacy files to see the explicit blocker. No XLS parsing is claimed.

For a write-free CSV investigation using a **fresh** output directory:

```powershell
python -m uv run --frozen equipment-data-manager process "C:\approved\raw\CompuClean Repair Report.csv" --report-type repairs --period 2026-01 --output-dir data/january-diagnostic-preview --preview --include-date-values
```

For services change the path and use `--report-type service_orders`. `--preview`
creates neither candidates nor history. `--include-date-values` explicitly prints
private source date cells and record numbers; keep the output local, never attach
it or financial metrics to a public PR. Without the flag, diagnostics include only
counts/parsed-month summaries, fingerprint, period and cleaner identity. Exit 1
on validation failure is expected. For runtime verification without opening Tk:

```powershell
python -m uv run --frozen python -c "import sys,pandas; import equipment_data_manager.processing.coordinator as c; print(sys.executable); print(pandas.__version__); print(c.__file__)"
```

## Regression evidence and remaining questions

Synthetic cases reproduce the exact rejection **categories** with controlled
outside-month dates and each original service exclusion. They are not claimed to
explain the user's still-unreproduced failures. Tests assert exact record/date
traces, safe default summaries, no-write preview, blocked processing, preserved
failed corrections, valid January processing, GUI month propagation and both TMA
filters/adapter routing. All prior tests remain. Current local suite: 200 passed;
Windows/Linux CI and packaged smoke outcomes are recorded on the PR.

Business questions remain: repair cost-field meanings/labor policy (separate
reconciliation); whether a service with blank scheduled date but a valid completed
date should be included; placeholder/`delete duplicate` exclusions; date ambiguity
and cross-period policy; actual XLS layouts; trusted expected cleaned outputs and
baselines. These explicit original rules are preserved, not declared approved.
No Microsoft authentication, Graph, production SharePoint or Power BI changes.
