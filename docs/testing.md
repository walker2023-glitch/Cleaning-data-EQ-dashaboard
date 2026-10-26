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

## Departmental monthly workflow

`test_monthly_workflow.py` adds synthetic mixed-type discovery/preview/process,
missing/unavailable folders, strict separate-root configuration, no recursive
history ingestion, per-type conflicts, unchanged reruns, corrected month selection,
input mutation/partial failures, read-only previews, immutable review packets,
failed staging cleanup and tampered-output blocking. Redirect guards are simulated
on all platforms without requiring privileged Windows symlink creation. Real-widget
cases cover the new default, configuration/discovery/checklist, all-three processing,
explicit packet export, changed-month rescanning and safe output destination errors.
The prior legacy UI cases explicitly inject legacy mode to preserve their original
compatibility coverage; the packaged smoke likewise tests legacy then normalized.

`powerquery_contract.py` tests use the real normalized cleaners and synthetic data.
They validate exact schemas, UTF-8 text IDs, null money, ISO dates, finite numbers,
distinct-month combination, duplicate-month/status rejection and nonrecursive folder
reading. Tests also compare every M column/type specification to the Python schema.
Microsoft's `@microsoft/powerquery-parser` 4.0.0 accepted the example's syntax in a
separate temporary development tool installation; it is not an app dependency.
Neither that parser nor Python reference tests execute Power BI's M evaluator.
Real Power Query import, numeric precision and model/DAX regression remain a pilot
gate; see `powerquery_integration.md`. No candidate is approved by passing tests.

Run the full existing isolated runner on Windows, or with --isolate-gui and a
display on Linux. Historical counts above describe earlier milestones, not the
current suite. Current outcomes and exact commit checks are recorded on this PR.

During this follow-up's local rerun, the legacy correction GUI case exited with a
native segmentation fault even in its own process. The trace showed a Tk font
finalizer on the pandas worker during automatic cyclic garbage collection. The
app now owns cyclic collection on its main thread for its lifetime, restores the
prior setting on close and joins the finished worker. The new regression checks
that GC cannot run automatically on the worker and verifies main-thread collection.
The failed run was retained; the post-fix full run is reported separately.

Local post-fix evidence for this branch: **266 tests passed, 0 skipped**, using the
isolated runner, plus the extended visible-window smoke through phase 19 (monthly
configuration/discovery, three-type preview/process, review-packet export and
untouched approved root). Wheel/sdist build and offline-config checks also passed.
Windows/Linux hosted results are recorded on the PR for its exact head; do not
infer Windows success from this Linux result.

## Settings and Guided Mode regression scope

New backend tests cover no-write first-run defaults, existing/missing/invalid/
overlapping paths, access/probe/create failures, explicit creation policy,
known-sync/UNC/non-fixed-drive rejection, required local confirmation, atomic
replacement failure, strict/corrupt settings recovery, legacy relative-path import,
reset data preservation and sanitized templates. The Windows drive rejection is
also simulated portably without admin privileges. No test needs real sync/auth.

Real-widget tests cover Browse/save/confirmed creation, settings and Brief/Guided
preferences restored in another window, invalid/corrupt/unavailable configuration,
reset confirmation, draft import, template sanitization, known sync rejection,
failed saves retaining active workspace, original candidate byte equality with
Guided Mode off, disabled hover/focus/F1, keyboard activation, bounded tooltip
placement, missing/error context, and responsive slow folder checks. Registry tests
check required source/business caveats, both detail levels, scaled-window sizing
and exact bundled-guide freshness. Every previous test is retained.

The first sizing implementation exposed a distinction between CTk window and
widget scaling APIs. The edge-placement test caught it; the tooltip now uses the
framework scaling tracker with a bounded styled Tk popup, not short-lived CTk
windows with delayed titlebar callbacks. Tests were corrected through code changes,
not omissions/retries. Fresh-process isolated test collection remains unchanged.

Run the full existing isolated runner on Windows; add --isolate-gui with a display
on Linux. The extended actual-window smoke through phase 24 covers visual save,
Brief/Detailed/off settings, F1, bundled employee guide and persisted startup in a
fresh **process** (source Python or the packaged exe). This avoids pretending that
reusing Tk's global trackers is an operating-system app restart. Windows PR CI must
build and run the actual executable before a review build is considered tested.
Automated checks do not replace employee usability/accessibility/scaling or trusted
financial/data validation. Hosted outcomes belong to their exact PR head.

Local post-fix result: **321 passed, 0 skipped**, plus the phase-24 actual-window
smoke and fresh-process settings restore. Hosted Windows/Linux tests and Windows
executable build/smoke must be assessed separately on this PR's exact head.

The initial Windows runs caught a second placement issue on their 768-pixel-high
display: the source window's default position could put an anchor below the screen,
so placing a tooltip above it was still too low. The app now positions its initial
window within the primary display and clamps the popup independently of anchor
position. An additional real-widget regression simulates an offscreen anchor;
the original edge assertion is retained unchanged. Post-fix results supersede the
initial Windows failures; no case is skipped or retried by the runner.

Packaged Windows diagnostics subsequently showed that restored folders/page/help
preferences were correct, but the restart smoke exited unsuccessfully after its
check. CTk's Windows mainloop startup pumps events during titlebar initialization;
a self-closing check could destroy the root during that startup pump. The restart
harness now finishes initial mapping before attaching its close/check callback.
A real-Tk regression simulates the Windows startup pump with an immediately ready
check. Both restored-state and successful-exit assertions remain required; no
failure is converted into success. Phase-only synthetic diagnostics are retained
as a small CI artifact and check annotation for future packaged failures.

## Power BI pilot checks

Run `uv run --frozen pytest tests/test_powerbi_pilot.py` for synthetic real-engine
two-month selection, original/snapshot preservation, corrected-month review,
duplicate/missing/unexpected months and types, hashes/paths/links, incompatible
schemas, failed staging, null/partial sums, unknown/invalid/duplicate baselines,
explicit comparability/tolerances, report isolation and M contract specifications.
The existing full Windows/Linux runner is unchanged; wheel CI also generates and
checks the pilot using the installed artifact. These do not execute Microsoft's
mashup runtime, existing DAX or a PBIX. Follow powerbi_pilot.md for those manual gates.

Pilot branch local evidence (Python 3.12.14, Linux real display): **357 tests
passed, 0 failed/errors/skips**, including the 323 preserved tests and 34 pilot
cases. All six .pq files passed Microsoft's powerquery-parser 4.0.0 syntax parser;
this is not mashup evaluation. Wheel/sdist build and an isolated installed-wheel
synthetic generation/snapshot check passed. Hosted Windows/Linux checks are
recorded separately on the pull request; manual backup-PBIX checks remain pending.

## Repair financial schema-v2 regression checks

`uv run --frozen pytest tests/test_repair_financial.py` covers January-/February-shaped
29/5-record datasets with invented financial amounts, equal/unequal grouped fields,
zero/missing/malformed money, repeated summaries/transactions, excluded records,
monthly discrepancies, exact legacy calculation retention, v1-to-v2 correction
review, write-free preview, companion integrity/write failures, desktop/CLI routing,
packet/snapshot propagation, mixed-version rejection and M schema/control contracts.
The malformed-number ingestion test now mutates RepairPersonHours, a numeric field
shared by both schema versions; no original test was removed. Actual January was
reconciled locally read-only; no real raw report, identity or financial amount is
committed. Real February and formatted repair/grouped-workbook validation are pending.

Financial branch local results: **376 passed, 0 failures/errors/skips** on Linux
with real desktop tests isolated per case (357 preserved tests + 19 new cases).
All eleven M files passed Microsoft's powerquery-parser 4.0.0 syntax parser.
Wheel/sdist build and installed-wheel v2 synthetic generation/snapshot checks passed.
These are not actual Power BI M/DAX execution or production accuracy approval.
