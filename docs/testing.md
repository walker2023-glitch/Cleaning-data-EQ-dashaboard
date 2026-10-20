# Test instructions and evidence limits

M1 local validation: **89 tests passed** on Linux / Python 3.12.14, with no skips.
Frozen dependency installation, package builds and an isolated wheel-based
synthetic repair run also passed. Remote Windows/CI results are separate evidence.

From the repository root using Python 3.12.14 / uv 0.12.23:

```sh
uv sync --frozen --all-extras
uv run --frozen --all-extras pytest
```

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
full suite and a wheel-based synthetic repair command. A workflow definition does
not prove remote CI or Windows completed; report observed results separately.

These are code-derived synthetic characterizations. They do **not** establish
production cleaning accuracy, approved source-total reconciliation, real export
ID/type/date correctness, TMA compatibility, Graph permissions, Windows executable
packaging or managed-PC behavior. Those checks require `inputs_needed.md` inputs.
