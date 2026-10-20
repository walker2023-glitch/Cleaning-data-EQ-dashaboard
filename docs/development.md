# Development (M0)

## Workflow and scope

Read `README.md` and `design.md` in full before editing. Use a feature branch and
review changes through a pull request. Cloud tasks are already isolated; use the
existing checkout and do not create a worktree unless explicitly requested.

Use Python 3.12.14 (`.python-version`) and uv 0.12.23. From the root run:

```sh
uv sync --frozen --all-extras
uv run --frozen --all-extras pytest
uv run --frozen --all-extras equipment-data-manager --check-config config.example.toml
uv build
uv run --isolated --no-project --with ./dist/equipment_data_manager-0.0.1-py3-none-any.whl python -I -m equipment_data_manager
```

`uv sync` creates `.venv`; no global pandas installation is needed. On Windows,
install the approved Python/uv toolchain through your normal development process.
The lockfile contains resolved packages and artifact hashes. Refresh it with
`uv lock` only in a reviewed dependency update, then rerun tests. The core package
has no runtime dependencies. Build tooling is pinned in `pyproject.toml`.

Required for M0: install, offline CLI/config check, all pytest tests, wheel/sdist
build and installed-wheel smoke check. CI runs on Ubuntu and Windows. A Windows
desktop pilot without Python, GUI, sign-in, Graph permissions and real report
reconciliation are later checks, not claims made by the M0 test suite.

## Layout

| Location | Purpose |
|---|---|
| `src/equipment_data_manager/` | Installable offline package and CLI |
| `processing/interfaces.py` | Cleaner, candidate result/schema/metrics contracts |
| `storage/interface.py` | Storage protocol with version-aware reads and create-only output |
| `storage/graph_sharepoint.py` | Explicitly disabled operations; no HTTP or auth implementation |
| `config.example.toml` | Empty, credential-free future integration settings |
| `legacy/clean/` | Exact uploaded sources, excluded from application wheel |
| `tests/fixtures/synthetic/` | Source-derived characterization inputs/expected outputs |
| `docs/` | Discovery, unverified contracts, supply checklist and development notes |

Tests deny socket connections/DNS during execution. The offline CLI never imports
legacy scripts or any Microsoft SDK. Pure legacy transformations are tested to
confirm a few observed behaviors, not to declare the inputs safe or approved.
Inventory import is intentionally unrun until its missing original helper exists;
there is no fake taxonomy module or skipped test masquerading as verification.

## Integration boundaries

`Cleaner.clean` accepts bytes plus a source name and a confirmed YYYY-MM period.
`CleanResult` carries candidate bytes, counts, typed schema, warnings, cleaner
version, source period, and unit-labelled decimal metrics. No production adapters,
registry, classifier or coordinator are implemented in M0. A future validator must
approve candidates before any storage write.

`ReportRepository` is injectable for later local fixture and Graph adapters.
Opaque item/folder IDs avoid assuming URLs or local paths. Reads carry expected
ETags; create-output is defined as fail-if-present. Conditional replacement,
staging, pagination, permission checks, bounded retries, cancellation, and shared
concurrency protection still require M1/M2 implementation and tests. The disabled
Graph class raises on every call; these interfaces do not establish Graph support.

No MSAL/token/cache code is present. Do not add client secrets for a public desktop
client. Future integration requires IT-approved registration/permissions, confirmed
test locations and secure Windows token caching; see `docs/admin_setup.md`.

## Fixture handling

Never commit raw production exports, names, descriptions, tenant IDs, tokens,
PBIX files, local config or outputs. `data/` is ignored. Commit reviewed synthetic
or explicitly sanitized fixtures only under `tests/fixtures/`, with provenance,
expected counts and totals, exclusions and comparison tolerances. The current
synthetic examples are not TMA samples or approved Power BI baselines.

Do not change legacy transforms to fit assumptions. Establish fixture-backed
business contracts before M1 adapter work. No production SharePoint access is
needed for development or tests in M0.
