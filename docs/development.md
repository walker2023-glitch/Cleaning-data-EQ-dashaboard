# Development (M1 offline engine)

Read `README.md` and `design.md` fully before changes. Use a feature branch and
pull-request review. M1 is based on M0 commit `2889796`; PR #1 remains a separate
draft and must not be merged automatically. The M1 PR targets the M0 branch so
its review contains only M1 changes; retarget after M0 merges.

Cloud tasks are already isolated. Use the existing checkout and do not create a
worktree unless explicitly requested. Use Python 3.12.14 (`.python-version`) and
uv 0.12.23. From the repository root:

```sh
uv sync --frozen --all-extras
uv run --frozen --all-extras pytest
uv run --frozen --all-extras equipment-data-manager --check-config config.example.toml
uv build
uv run --isolated --no-project --with ./dist/equipment_data_manager-0.1.0-py3-none-any.whl python -I -m equipment_data_manager
uv run --isolated --no-project --with ./dist/equipment_data_manager-0.1.0-py3-none-any.whl python -I -m equipment_data_manager process tests/fixtures/synthetic/repairs_input.csv --report-type repairs --period 2026-09 --output-dir data/wheel-smoke
```

These commands work in PowerShell and POSIX shells. `uv sync` creates `.venv`;
no global pandas installation is needed. CI bootstraps uv with the hosted Python
3.12, then uses `uv python install 3.12.14` for the pinned project runtime;
setup-python lacks that exact Windows build.

The engine requires pinned pandas; the optional `legacy` extra supplies Excel
readers for discovery, not TMA support.
The lockfile pins dependencies and artifact hashes. Update `uv.lock` only with
reviewed dependency changes and rerun all tests. Build tooling is pinned in
`pyproject.toml`. Bump the adapter's `wrapper-v1` version if reading, formatting or
validation behavior changes; source and pandas versions are already in its identity.

## Package layout

| Location | Purpose |
|---|---|
| `processing/interfaces.py` | Cleaner and candidate CSV/schema/metric contracts |
| `processing/models.py` | Requests, statuses and revision/result metadata |
| `processing/cleaners.py` | Supported-layout guards and source-preserving wrappers |
| `processing/_legacy/` | Three bundled original modules; only imports changed |
| `processing/coordinator.py` | Bytes/path inputs, sequential work and review decisions |
| `processing/manifest.py` | Local SQLite selection and immutable CSV revisions |
| `legacy/clean/` | All six untouched uploads with checked SHA-256 hashes |
| `storage/` | Future storage contracts and disabled Graph implementation |
| `tests/` | Offline characterization, failure injection and workflow tests |

The coordinator is callable without CLI/GUI or Graph. See
[cleaning_architecture.md](cleaning_architecture.md) for the Python API and
transaction/recovery boundaries, and [testing.md](testing.md) for tests and limits.

## Fixture and output handling

Keep experiments/output under ignored `data/` or an authorized local temporary
directory. No real exports, credentials, tokens, PBIX files or organizational
settings belong in commits. SQLite manifests are ignored, but CSVs outside ignored
paths are not automatically safe to commit. Commit only reviewed synthetic or
explicitly sanitized fixtures under `tests/fixtures/`, with provenance, expected
counts, exclusions, totals and tolerances. Current examples are source-derived,
not production or TMA validation. Do not change calculation/date/exclusion behavior
without verified fixtures and explicit approval. Tests verify the vendored copies
differ from the untouched originals only in package-relative imports.

## Deferred integration

M0 configuration remains offline-only; Microsoft fields are inert placeholders.
No MSAL, credentials, network client, token cache or GUI is added in M1. The Graph
stub still raises on every operation. Local locking protects this output store
only; it is not a cross-computer SharePoint lease. IT approval, conditional Graph
uploads and secure Windows token caching remain M2.
