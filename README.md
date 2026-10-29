# Equipment Data Manager

## Approval and publishing foundation

The **feature/approval-publishing-foundation** branch adds **Review & Approval**:
monthly counts, financial summaries, missing values, warnings, exact candidate
revisions/hashes and durable **local, unsent review requests**. Changed originals
or corrected candidates invalidate earlier request evidence. Final approval and
Publish remain disabled because authoritative reviewer verification is unavailable.
Upload/recovery/concurrency/rollback tests use an in-memory specification model,
never a real publisher. See [architecture and employee preview](docs/approval_publishing_foundation.md).
Owner-tested OneDrive raw reads do not prove automated cloud synchronization.

## Integration baseline — merged by owner, 2026-10-29

The owner merged integration PR #14 into **main** at 36f8f20.
It contains every audited feature head through the owner merge of PR #13.
The integration documents retain their historical test/CI evidence; this merge
does not retroactively prove previously inaccessible checks. [Integration status, dependency graph, test evidence,
Windows/CI blockers and rollback](docs/integration_baseline.md) supersede older
branch-specific launch instructions below. Live Graph and publication remain disabled.

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
taxonomy dependency is missing. No live sign-in or SharePoint operation is enabled; production Power BI is unchanged. An automated packaged-window smoke check does not establish
employee-release readiness; a managed-PC usability/security pilot remains required.

M0's verified-sample acceptance criterion remains open: sanitized raw/expected
report pairs, approved totals, and organizational configuration are still needed.
See [discovery](docs/discovery.md), [data contracts](docs/data_contracts.md), and
[the supply checklist](docs/inputs_needed.md). See also [architecture](docs/cleaning_architecture.md)
and [milestone status](docs/milestones.md).

See the [format compatibility matrix](docs/format_compatibility.md) and
[edge-case evidence](docs/edge_case_validation.md) for supported layouts, monthly
count tests and remaining repair financial semantics and estimate-policy gates.

See [January rejection diagnostics](docs/january_rejection_investigation.md) for
Windows runtime checks, per-record date/exclusion traces and explicit TMA filters.

The recommended/default desktop **Power BI CSV candidate** output format adds versioned header-first
exports with ISO dates, text IDs, ReportMonth and provenance. Legacy mode remains
available for compatibility. See [output contracts/publication design](docs/powerbi_output_design.md),
[future maintenance classification design](docs/maintenance_classification_design.md)
and [VS Code preview steps](docs/development.md#power-bi-candidate-branch-in-vs-code).
The classifier and production publisher are not implemented; publication remains
blocked by financial and trusted-output validation gates.

## Monthly departmental workflow

Configure folders with **Settings → Browse → Check Locations → Save Settings**.
Choices restore automatically; employees need no TOML editor. Select a month,
then **Discover month**, confirm, preview and process. The checklist identifies
missing report types. **Export review packet** copies one current normalized
candidate per type into a new immutable review folder, with hashes and warnings;
it never writes the reserved approved location. Original inputs remain unchanged.

See the [monthly SOP](docs/monthly_workflow.md), [status and roadmap](docs/roadmap.md),
[validation checklist](docs/validation_checklist.md),
[Power Query example and offline checks](docs/powerquery_integration.md), and
[delegated Graph requirements](docs/sharepoint_integration_plan.md).
Synchronization, business approval and production publication are not implemented.

## Settings and Guided Mode

First launch opens visual setup. Candidate history must stay on a trusted local
disk; the approved folder remains reserved. Guided Mode defaults to Detailed, with
hover/focus explanations, F1 Help and an offline employee guide. Preferences persist
without changing cleaning logic. See [Settings](docs/settings_guide.md),
[Guided Mode / help maintenance](docs/guided_mode.md) and
[VS Code first-run testing](docs/development.md#settings-and-guided-mode-preview).

## Repair financial correction

Recommended Power BI mode now uses repair schema v2: reported repair totals,
estimated labor and original legacy arithmetic are separate, with a hashed monthly
financial-summary CSV. Legacy/v1 compatibility remains. See the
[financial contract, evidence limits and migration guide](docs/repair_financial_v2.md).
January arithmetic reconciliation passed locally; the owner now reports January/February
v2 reconciliation and successful real-data Desktop imports/visual testing. Nonzero
unequal equipment-subtotal semantics and formal business/model approval remain open. No approval
or production change is implied.

## Power BI integration pilot

Use the [multi-month pilot instructions](docs/powerbi_pilot.md) to generate a
January/February synthetic snapshot, import it into a separate PBIX and create a
source/cleaned/dashboard reconciliation report. Exact schemas, expected months,
hashes and duplicate checks keep historical revisions outside ingestion folders.
See [model mappings](docs/powerbi_compatibility.md) and the
[unresolved repair-cost decisions](docs/repair_cost_reconciliation.md). Candidates
remain unverified; actual model/M execution and financial approval are still open.

## Real-data Power BI readiness (Milestone A)

Use the [January/February v2 workflow](docs/powerbi_real_data_readiness.md) for explicit
packet selection, a four-folder snapshot, private monthly/combined expectations,
optional original-file SHA-256 verification, a readiness report and shared-period
Power Query examples. The complete synthetic walkthrough is runnable without data.
See the [backup-dashboard migration plan](docs/powerbi_backup_migration.md),
[management decisions](docs/management_decisions.md) and
[inventory design/required inputs](docs/inventory_foundation_design.md).
No cleaning rules or production state change. The owner reports successful local v2
imports/visual testing; formal acceptance/production approval remains separate.

## SharePoint connectivity foundation (Milestone C)

Local/downloaded synced raw reads now check Windows placeholder availability,
stable file identity/length and hashes. Settings explains sync limits and keeps
Graph disabled. Provider contracts, an injected offline Graph adapter, an
MSAL-compatible session and DPAPI protected-cache component are tested without
credentials. No HTTP/SDK bootstrap or business publication is enabled. See the
[implementation/status guide](docs/sharepoint_foundation.md),
[future authorized live pilot](docs/sharepoint_live_pilot.md) and inert
graph.example.toml. Candidate history/SQLite remain on trusted local disk.

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
uv run --frozen --all-extras python .github/run_tests.py
```

Tests include real windows and need a desktop display. On a headless Linux runner,
use `xvfb-run -a uv run --frozen --all-extras python .github/run_tests.py`. Windows runs the same suite
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
