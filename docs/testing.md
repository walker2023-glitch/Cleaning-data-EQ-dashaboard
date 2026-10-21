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
