# Equipment Data Manager

A Windows desktop application for cleaning and validating
CompuClean and TMA reports stored in SharePoint.

## Goals
- Microsoft account sign-in
- Direct SharePoint integration
- One-click data cleaning
- Safe file processing and validation
- Power BI-ready CSV outputs
- Simple Windows executable distribution

## Current status: M1 offline cleaning foundation

The application described in [design.md](design.md) is the target design.
The offline coordinator accepts CSV bytes or local files, wraps the existing
CompuClean repair and flat Service Orders List transformations, and produces
**candidate** CSVs with structured counts, warnings and artifacts. It processes
files sequentially, skips identical reruns, and requires review before selecting
a corrected monthly revision. Inputs and previous output revisions are retained.

Production cleaning accuracy is **unverified**. Supported layouts are conservative,
source-derived gates, not approved departmental schemas. TMA processing remains
blocked because the requests cleaner's compatibility is unconfirmed. Inventory's
taxonomy dependency is missing. No GUI, sign-in, SharePoint operation or Power BI
change is implemented.

M0's verified-sample acceptance criterion remains open: sanitized raw/expected
report pairs, approved totals, and organizational configuration are still needed.
See [discovery](docs/discovery.md), [data contracts](docs/data_contracts.md), and
[the supply checklist](docs/inputs_needed.md). See also [architecture](docs/cleaning_architecture.md)
and [milestone status](docs/milestones.md).

## Development

Use Python **3.12.14** and **uv 0.12.23**. pandas is the pinned engine dependency.
The `legacy` extra adds Excel readers for source discovery only. The wheel bundles
three source-preserved modules with package-relative import changes; all six
untouched original uploads remain under `legacy/clean`.
`uv.lock` pins the dependency resolution for Windows and Linux.

```sh
python -m pip install uv==0.12.23
uv sync --frozen --all-extras
uv run --frozen --all-extras python -m equipment_data_manager
uv run --frozen --all-extras python -m equipment_data_manager --check-config config.example.toml
uv run --frozen --all-extras pytest
```

These commands work in PowerShell and POSIX shells from the repository root.
Use `Copy-Item config.example.toml config.local.toml` on Windows, or
`cp config.example.toml config.local.toml` on POSIX, for optional local settings.
Local settings are ignored. Keep the configuration offline and never add credentials.

## Try a synthetic report

From the repository root:

```sh
uv run --frozen --all-extras equipment-data-manager process tests/fixtures/synthetic/repairs_input.csv --report-type repairs --period 2026-09 --output-dir data/m1-candidates
```

`--period` is an explicitly confirmed month; the engine does not infer it from the
filename. Report types: `repairs`, `service_orders`, and `tma_work_orders` (blocked
pending verified fixtures). Pass multiple files for sequential processing. The CLI
prints JSON and exits 0 for success/skipped results or 1 for failure/needs-review.

The result's `output_location` identifies its candidate artifact. The manifest
selects one current revision per report type/month; **do not recursively ingest
the versions directory into Power BI**, as it also retains previous revisions.
For a correction, inspect the proposed result and pass its `replacement_token`
using `--replacement-token TOKEN` with the same single file/type/month. Tokens
bind both current and proposed revisions; stale or different corrections require
review again. This is local acknowledgement, not an authentication mechanism.

See [development instructions](docs/development.md) for layout, validation,
fixture rules, and milestone boundaries. Read this README and `design.md`
completely before implementation changes.
