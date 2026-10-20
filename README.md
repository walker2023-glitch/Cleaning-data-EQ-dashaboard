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

## Current status: M0 discovery scaffold

The application described in [design.md](design.md) is the target design.
This branch provides an installable **offline** Python scaffold, safe configuration,
cleaner/storage interfaces, preserved source uploads, and smoke/characterization
tests. It does not yet process departmental reports, sign in, access SharePoint,
launch a GUI, or produce an approved Power BI output.

M0's verified-sample acceptance criterion remains open: sanitized raw/expected
report pairs, approved totals, and organizational configuration are still needed.
See [discovery](docs/discovery.md), [data contracts](docs/data_contracts.md), and
[the supply checklist](docs/inputs_needed.md).

## Development

Use Python **3.12.14** and **uv 0.12.23**. The `src/` package uses the standard
library in M0. The `legacy` extra installs pandas and Excel readers only for
inspection/tests of supplied cleaners; legacy scripts are not part of the wheel.
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
Local settings are ignored. Keep M0 in offline mode and never add credentials.

See [development instructions](docs/development.md) for layout, validation,
fixture rules, and milestone boundaries. Read this README and `design.md`
completely before implementation changes.
