# Development comparison exports — Milestone 1a

> Current desktop generation uses [comparison-preview-v3](comparison_exports_v3.md).
> This document describes the retained historical contract.


**Original v1 contract reference.** The current development action and CLI default
now generate [comparison-preview-v2](comparison_exports_v2.md), adding ID/Building
enrichment. This v1 schema/helper are preserved. Request `--export-schema
comparison-preview-v1` explicitly to reproduce v1; the demo scripts use the latest
profile. Use the V2 guide/helper for new desktop exports.

Contract: **comparison-preview-v1**. Purpose: **DevelopmentComparison**.
This is a temporary development tool for comparing a backup PBIX, not another
permanent employee output mode. It does not activate files, approve data, refresh
Power BI, upload to SharePoint, or change the canonical historical-powerbi-v1
contract. Equipment Type, Building, MaintenanceType and Equipment_History.csv
remain subsequent, separately approved milestones.

## Desktop workflow

1. Configure the existing raw/candidate/reserved-approved roots in Settings.
2. Open Historical Data → Power BI snapshot. Generate a canonical snapshot using
   the existing reviewed workflow, or use a previously completed snapshot.
3. Expand **Development tools** and choose **Create simplified comparison export**.
4. Select one completed canonical folder ending in `snapshot`. Confirm development
   comparison intent and trusted local storage, then choose a separate output parent
   outside raw, candidates, reserved approved, the source snapshot and production.
5. Wait for completion, then choose **Open comparison export**. Only a completed
   `comparison` directory is eligible for import. Stop cancels between writes;
   previous completed exports and all inputs remain intact.

This action uses the existing worker. It does not rerun cleaning or consult current
candidate selections. The input snapshot supplies the exact historical revisions.
The current single-month format preference and canonical generation stay unchanged.

## Files and fields

```text
Comparison_Test_<id>/
  comparison/                       # visible only after successful validation
    Repairs_History.csv
    ServiceOrders_History.csv
    TMAWorkOrders_History.csv
    RepairFinancialSummaries.csv
    comparison_manifest.json
    audit/
      lineage.csv
      canonical/                    # exact six-file canonical input, not another input query
        <original four CSVs>
        snapshot_manifest.json
        compatibility_report.md
```

The four top-level CSVs contain ordered business columns, header-first UTF-8 with
LF line endings. Every cell copies the canonical string exactly, including blank
numeric/date nulls, zero, leading zeros, multiline descriptions, dates and legacy
amounts. Rows remain in canonical order. No normalization, classification, filter,
deduplication, rate calculation, allocation or rounding is performed.

| Dataset | Ordered columns |
|---|---|
| Repairs_History.csv | ReportMonth, CompletedDate, EquipmentName, EquipmentId, Location, ServiceVendor, RepairCount, RepairPersonHours, ReportedTotalCost, ReportedTotalCostStatus, EstimatedLaborCost, LegacyPartsCost, LegacyLaborCost, LegacyEstimatedTotalCost, Description, Details, AccountName, RawEquipmentId |
| ServiceOrders_History.csv | ReportMonth, EquipmentId, EquipmentName, ScheduledDate, CompletedDate, Location, Description, Status, RawStatus, EstimatedPrice, RawDescription, SourceMaintenanceTag, AccountName, SourceVendorName, RawCost, RawEquipmentId |
| TMAWorkOrders_History.csv | ReportMonth, WorkOrderId, RequestDate, Requestor, Request, AssignedTo |
| RepairFinancialSummaries.csv | ReportMonth, ReportedLaborCost, ReportedPartsCost, ReportedTotalCost, ReportedRepairCount, SourceRecordCount, RetainedRepairCount, KnownRepairTotalCost, UnavailableRepairCostCount, RepairTotalDifference, SummaryComponentsDifference, ReconciliationStatus, EstimatedLaborCostSum, EstimatedLaborCostMissingCount, LegacyPartsCostSum, LegacyPartsCostMissingCount, LegacyLaborCostSum, LegacyLaborCostMissingCount, LegacyEstimatedTotalCostSum, LegacyEstimatedTotalCostMissingCount |

Hashes, revisions, validation/cleaner metadata, raw financial textbox cells and
legacy row ordinals are available in the retained canonical evidence rather than
the simplified tables. Raw identifiers and descriptions stay in the comparison
tables. All files contain private operational data; do not commit real exports.

Financial meanings are unchanged: ReportedTotalCost is not parts plus an additional
labor estimate. EstimatedLaborCost is separate. Legacy* values are compatibility
arithmetic, not verified source charges. KnownRepairTotalCost may be a partial
subtotal: read UnavailableRepairCostCount and ReconciliationStatus. A blank is not
zero. Monthly reported totals cannot be allocated to individual repairs. Existing
PM/Repair source tags are literal indicators, not approved classifications.

## Lineage, integrity and interruption

`comparison_manifest.json` records the contract, unapproved status, source manifest
SHA-256, exact columns/types, CSV hashes, rows/month and lineage hash/count. It has
no creation timestamp: repeated exports of the same snapshot produce identical
bytes throughout. Different canonical manifest timestamps change source identity,
even when projected CSV bytes are identical.

`audit/lineage.csv` identifies each output by Dataset and **one-based parsed CSV
record number**, excluding its header. CanonicalRecordNumber maps to the same
ordinal in the retained canonical CSV. It also copies RecordId, ReportMonth,
candidate revision/hash/cleaner, source filename/hash/record number and financial
summary hash where available. A monthly financial summary has no transaction
RecordId or source row: those fields stay blank; its month, repair revision and
canonical record ordinal establish lineage. Never use physical text line numbers
for CSVs with embedded newlines.

Generation validates the canonical source, captures allowlisted files, checks the
captured hashes, exclusively creates its own output container, writes/fsyncs and
reads back files, then validates projections and full lineage against the retained
canonical copy. Finalization renames `.s` to `comparison` on the same filesystem.
No existing destination is overwritten. Path checks reject links, known synced/
network storage, protected overlaps and Windows paths exceeding conservative bounds.
The configured roots are protected; the app cannot identify every unconfigured
production folder, so the operator must choose a separate test destination.

Caught errors/cancellation remove only the new owned container. An OS/process kill
may leave `.s`: do not import or resume it. Preserve it for diagnosis and create a
new export. Finalization is not a hardware power-loss guarantee. Hashes are not
signatures against an attacker able to rewrite the whole evidence bundle. The
retained copy verifies candidate evidence, not original raw bytes or business accuracy.

## Windows acceptance and backup PBIX import

Use a review build from this feature branch at its recorded commit. Keep production
PBIX and SharePoint untouched. First generate a NEW invented demonstration:

```powershell
uv run --frozen --all-extras python examples/create_comparison_demo.py --output data/comparison-demo
uv run --frozen --all-extras python -m equipment_data_manager.comparison_export --verify data/comparison-demo/comparison-1/comparison
uv run --frozen --all-extras python -m equipment_data_manager.ui.app
```

For the desktop test, import `data/comparison-demo/workspace.toml` in Settings →
Advanced Settings, check/reconfirm local storage and save. Follow the desktop steps
above; choose `data/comparison-demo/test-snapshot-1/snapshot` as input. Confirm four
files, matching monthly counts, text IDs and unchanged source/candidate evidence.
Repeat to a fresh output and compare CSV hashes. Cancel once and try an invalid
snapshot; neither should replace a previous result. A packaged app requires no
Python for generation; a maintainer can perform the separate Python integrity check.

In a separately saved backup PBIX:

1. Run Python `--verify` on the completed comparison folder first.
2. Paste `powerquery/fnReadComparisonPreview.pq` into a Blank Query named
   **fnReadComparisonPreview**. Create text parameter **ComparisonFolder** pointing
   to that one completed `comparison` directory.
3. Create four NEW, disconnected comparison queries, one expression per query:

```powerquery
= fnReadComparisonPreview(ComparisonFolder, "repairs", true)
= fnReadComparisonPreview(ComparisonFolder, "service_orders", true)
= fnReadComparisonPreview(ComparisonFolder, "tma_work_orders", true)
= fnReadComparisonPreview(ComparisonFolder, "repair_financial_summary", true)
```

4. Compare shared-month row counts, repair counts/hours, date/null behavior and each
   financial meaning separately. Keep existing DAX, relationships and production
   sources unchanged. Never import `audit` recursively or combine export directories.

The helper validates exact headers/types and monthly/total counts, preserving text
IDs and nullable numbers/dates. It does not cryptographically verify files or run
the Python verifier. `true` opts into unapproved comparison, not business approval.
Actual M/DAX/visual evaluation requires Power BI Desktop on Windows. Existing
Building policies, March exclusions, Requests/Work Order grain, date-only requests
and missing historical coverage remain as documented in historical_powerbi_compatibility.md.

## Extension boundary and developer checks

`comparison_export.py` owns an independent ordered projection registry, pure
`project_tables`, manifest, lineage, validation and local writing. Future enrichment
can extend the projection stage and typed registry with a new preview contract
version, including a derived equipment table. Keep canonical readers/cleaners
unchanged and use one shared enrichment implementation for facts and lookup.
Do not turn this temporary control into competing permanent output modes.

Tests: `tests/test_comparison_export.py` and the comparison cases in
`tests/test_desktop_widgets.py`. The full runner isolates each GUI case; do not run
GUI suites/smokes concurrently on one display. Existing executable smoke reaches
phase **51**, including comparison validation, then performs the fresh-process
settings restart. Packaging uses the existing dependencies; no new packages.

```powershell
uv run --frozen --all-extras python .github/run_tests.py
uv build
uv run --isolated --no-project --with ./dist/equipment_data_manager-0.2.0-py3-none-any.whl python -I examples/create_comparison_demo.py --output data/comparison-wheel-demo
.\packaging\build.ps1
```

Linux checks do not establish native Windows executable or Power BI acceptance.
No monthly activation, append/rebuild, new classification, Graph integration,
automatic refresh or SharePoint publication is implemented.

## Local validation — 2026-11-19

- Full Linux runner on the feature tree: **970 passed, 0 failures, 0 errors,
  0 skipped** (896 core plus 74 isolated real-widget cases).
- sdist/wheel builds passed. Installed-wheel six-month demonstration created two
  identical exports: 18 repair, 12 service, 13 TMA and 6 financial-summary rows.
  The final installed-wheel comparison verifier passed.
- Source and isolated installed-wheel phase-51 desktop/restart smokes passed.
- Native Linux PyInstaller build passed. Its first executable launch failed with
  missing `libtcl9tk9.0.so`; build diagnostics also identified `libtcl9.0.so`.
  Both are supplied by this image's Python runtime outside the system loader path.
  With that runtime's lib directory in LD_LIBRARY_PATH, the frozen phase-51 smoke
  and restart passed. This is not proof of standalone Linux distribution readiness.
- An earlier full run had one existing focus-help assertion fail (968 passed,
  1 failed). Parking the virtual pointer outside controls resolved the affected
  test, and the fresh full runner above passed without test/behavior changes.
- Native Windows packaging, hosted CI outcomes, actual M/DAX execution, real-data
  comparison and owner acceptance remain unverified. Linux is not Windows evidence.

No cleaner, financial calculation, canonical snapshot schema or dependency file
was changed. Local generated artifacts contain synthetic data only.
