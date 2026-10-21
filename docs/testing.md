# Test instructions and evidence limits

M2 adds workflow/background-worker and real CustomTkinter widget tests. The local
multi-month full run passed **185 tests**, including every prior M0/M1 test. Widget tests need
a real/virtual display and do not silently skip when a display is missing.

M1 local validation: **89 tests passed** on Linux / Python 3.12.14, with no skips.
Frozen dependency installation, package builds and an isolated wheel-based
synthetic repair run also passed. Remote Windows/CI results are separate evidence.

From the repository root using Python 3.12.14 / uv 0.12.23:

```sh
uv sync --frozen --all-extras
uv run --frozen --all-extras pytest
```

On headless Linux use `xvfb-run -a uv run --frozen --all-extras pytest`. The cloud
run used its existing Xorg server with a dummy display. Windows CI runs directly.

Focused desktop checks:

```sh
uv run --frozen --all-extras pytest tests/test_desktop_workflow.py tests/test_desktop_widgets.py
uv run --frozen --all-extras python -m equipment_data_manager.ui.app --smoke-test --smoke-dir data/desktop-smoke
```

The smoke check creates an actual window and isolated synthetic inputs/outputs,
then checks write-free preview, M1 processing, duplicates, explicit correction
confirmation, retained revisions, history and TMA XLSX preview/process. It exits 0 and writes
`desktop-smoke.json` with `passed` only when the complete flow finishes. GUI tests
also exercise native selection adapters, invalid input/type/month, TMA XLSX and rejection of unconfirmed TMA formats,
input mutation after preview, stale corrections, long work without freezing,
deferred close, cancellation and recoverable worker errors.

Windows CI builds and runs the actual PyInstaller executable with this flow before
uploading a prototype ZIP/checksum. The build/check outcomes belong to their exact
PR commit; they do not establish managed-PC usability or production accuracy.

For focused development:

```sh
uv run --frozen --all-extras pytest tests/test_cleaning_adapters.py tests/test_coordinator.py tests/test_processing_cli.py
```

Run the complete suite before PR review. All M0 tests remain; socket connections
and DNS are denied during tests. Test outputs use temporary directories, and
inputs contain only synthetic values. Real data requires approved sanitization
and fixture review before it can be committed or used here.

Coverage includes report selection, missing/invalid files, schemas and periods,
duplicate/blank headers, malformed encodings/row widths, invalid dates/numbers,
source preservation, original transform/writer equivalence, sequential continuation,
renamed reruns, duplicate basenames across months, reopened manifests, corrected
reports, changed cleaner versions, stale confirmations, previous revision retention,
local simultaneous calls, injected write/manifest failures and missing/tampered
artifacts. Original source hashes and disabled Graph/config/CLI behavior remain
covered. Error tests check category-only messages rather than raw private details.

`uv build` plus the isolated installed-wheel commands in `development.md` check
the packaged engine without pytest's legacy import path. Windows/Linux CI runs the
full suite and wheel-based synthetic repair/TMA commands. A workflow definition does
not prove remote CI or Windows completed; report observed results separately.

These are code-derived synthetic characterizations. They do **not** establish
production cleaning accuracy, approved financial reconciliation, correctness of
unseen exports or legacy XLS, Graph permissions or managed-PC behavior. Those checks require `inputs_needed.md` inputs.

## Monthly regression scope

`test_monthly_compatibility.py` exercises invented January–June CompuClean and
January–April TMA count cases, strict metadata/layout guards, unchanged money/hours,
IDs/text, dates/status, exclusion warnings, repeated transactions and corrected
months. `tests/report_samples.py` is both the fixture factory and the optional
local GUI sample generator. See `edge_case_validation.md` for the inventory and
`format_compatibility.md` for precise supported formats. Matching source counts
is not financial or production accuracy validation. CI outcomes are recorded on
the PR; never infer Windows success from the local Linux run.

Windows CI runs each real-widget case in a fresh Python process through
`.github/run_tests.py`, avoiding Tcl interpreter reuse across destroyed test windows.
The initial Windows PR attempts exposed intermittent init.tcl/tk.tcl loading
errors while the same-commit push suite passed. This isolation runs every case
once, preserves failures, and combines their JUnit reports; it does not retry or
skip tests. Linux uses the normal single pytest run. To exercise the isolated
runner locally (with a display on Linux), use
`uv run --frozen --all-extras python .github/run_tests.py --isolate-gui`.

## January rejection diagnostics follow-up

The current local suite passes 200 tests. `test_rejection_diagnostics.py` and added
widget cases check per-record dates/reasons surviving failures, every service
first-exclusion category, valid January process/preview, default date-cell privacy,
write-free CLI preview, correction safety and explicit TMA XLSX/XLS routing.
See `january_rejection_investigation.md` for the unreproduced Windows symptoms,
actual local January findings, and commands. On Windows prefer
`python -m uv run --frozen --all-extras python .github/run_tests.py` over plain pytest
to isolate each GUI case's Tcl interpreter; no tests are skipped or retried.

## Normalized export follow-up

`test_powerbi_exports.py` covers all 16 synthetic monthly count cases and stable
contracts, dates/numbers, source-bound IDs, leading zeros, Unicode/quotes/newlines,
missing/invalid/zero financial values, legacy-value preservation, source alignment,
raw descriptions/status/tags, real duplicate transactions, malformed candidates,
independent histories/correction confirmation, no-write preview and simulated flat
folder combination. New real-widget cases select each report's Power BI candidate
mode, preview/process with the real engine and switch safely back to legacy.
The current local suite has 237 tests. All previous M0–M2/compatibility/diagnostic
tests remain. No manually labeled classification accuracy test is claimed.

The visible-window smoke now runs all three report types in normalized mode after
its existing legacy/duplicate/correction/history checks. Windows PR CI builds and
runs the actual executable; both OS jobs run isolated installed-wheel normalized
repair/TMA commands. Remote results belong to the specific PR commit. Pandas-based
synthetic folder tests check CSV structural combination, not execution of a real
Power Query model or modification of an actual PBIX. No trusted production golden
output, financial approval, classification engine or publisher is supplied.

The normalized-export PR's later Linux run exited with a native process crash
before a completed JUnit report (while its same-commit push run passed both OSes).
Linux CI now also uses `--isolate-gui` under xvfb, the same fresh-interpreter runner
already tested locally for all 237 cases and used by Windows. Each GUI case runs
once; failures are preserved, with no retries or skips. This contains repeated Tk
interpreter state in the test harness without changing application/cleaning rules.
