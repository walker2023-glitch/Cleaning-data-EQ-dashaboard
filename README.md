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

## Current status: M2 local desktop prototype

The CustomTkinter desktop wraps the real M1 engine with report selection, local
file picking, explicit month confirmation, write-free preview, background processing,
correction review, results, candidate history and help. Bundled synthetic samples
let you preview the workflow without departmental data.

See the [employee guide](docs/user_guide.md), [desktop architecture](docs/desktop_architecture.md)
and [Windows packaging instructions](docs/windows_packaging.md). This user-directed
M2 is offline; the original design's M2 Microsoft/Graph milestone remains deferred.

The application described in [design.md](design.md) is the target design.
The offline coordinator accepts CSV/XLSX bytes or local files, wraps the existing
CompuClean repair and flat Service Orders List transformations, and produces
**candidate** CSVs with structured counts, warnings and artifacts. It processes
files sequentially, skips identical reruns, and requires review before selecting
a corrected monthly revision. Inputs and previous output revisions are retained.

Production cleaning accuracy is **unverified**. Supported layouts are conservative,
source-derived gates, not approved departmental schemas. TMA processing is
available as provisional XLSX candidates for the observed title/header/footer layout. Inventory's
taxonomy dependency is missing. No sign-in, SharePoint operation or Power BI change
is implemented. An automated packaged-window smoke check does not establish
employee-release readiness; a managed-PC usability/security pilot remains required.

M0's verified-sample acceptance criterion remains open: sanitized raw/expected
report pairs, approved totals, and organizational configuration are still needed.
See [discovery](docs/discovery.md), [data contracts](docs/data_contracts.md), and
[the supply checklist](docs/inputs_needed.md). See also [architecture](docs/cleaning_architecture.md)
and [milestone status](docs/milestones.md).

See the [format compatibility matrix](docs/format_compatibility.md) and
[edge-case evidence](docs/edge_case_validation.md) for supported layouts, monthly
count tests and the unresolved January repair financial discrepancy.

See [January rejection diagnostics](docs/january_rejection_investigation.md) for
Windows runtime checks, per-record date/exclusion traces and explicit TMA filters.

## Development

Use Python **3.12.14** and **uv 0.12.23**. pandas is the pinned engine dependency.
The `desktop` extra supplies CustomTkinter/Pillow; `packaging` supplies PyInstaller.
openpyxl is a pinned runtime dependency for TMA XLSX. The `legacy` extra adds
xlrd for XLS discovery only. The wheel bundles four source-preserved modules with package-relative import changes; all six
untouched original uploads remain under `legacy/clean`.
`uv.lock` pins the dependency resolution for Windows and Linux.

```sh
python -m pip install uv==0.12.23
uv sync --frozen --all-extras
uv run --frozen --all-extras python -m equipment_data_manager
uv run --frozen --all-extras python -m equipment_data_manager --check-config config.example.toml
uv run --frozen --all-extras pytest
```

Tests include real windows and need a desktop display. On a headless Linux runner,
use `xvfb-run -a uv run --frozen --all-extras pytest`. Windows runs the same suite
directly. The CLI remains usable without the optional desktop dependencies.

## Preview the desktop

For a developer launch from the repository root:

```sh
uv sync --frozen --extra desktop
uv run --frozen --extra desktop equipment-data-manager-desktop
```

Select a report card, click **Load synthetic sample**, confirm **September 2026**,
then click **Preview Processing** and **Process Reports**. Preview creates no
outputs. Review warnings and use History to open a saved candidate's folder.

For a nontechnical Windows preview, obtain the prototype ZIP from a **successful**
Windows PR build artifact, extract the entire application folder, then double-click
`EquipmentDataManager.exe`. No terminal or Python is needed for that packaged
workflow. See [the employee guide](docs/user_guide.md) for the full steps.

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
filename. Report types: `repairs`, `service_orders`, and `tma_work_orders` (specific XLSX layout, provisional output contract). Pass multiple files for sequential processing. The CLI
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
