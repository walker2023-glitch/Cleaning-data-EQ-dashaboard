# Comparison export v2 — equipment IDs and Building (Milestone 1b)

> Current desktop generation uses [comparison-preview-v3](comparison_exports_v3.md).
> This document describes the retained historical contract.


Contract: **comparison-preview-v2**. Purpose: **DevelopmentComparison**.
This feature starts from verified main **720dfb2** (owner-merged PR #25, Milestone
1a). It extends only comparison projections. Canonical historical-powerbi-v1,
financial schema 2, source files, selected candidate revisions and history stay
unchanged. No new dependencies or Settings schema are introduced.

The existing collapsed Development tools action now generates v2. There is no new
employee format choice or parallel permanent workflow. [The v1 contract and guide](comparison_exports.md)
and `fnReadComparisonPreview.pq` remain available; existing v1 bundles still validate.
Use the version-specific **fnReadComparisonPreviewV2.pq** for v2.

## Equipment ID policy — rez-spacing-v1

One function applies to Repairs and Service Orders. It accepts the entire canonical
EquipmentId only when it consists of uppercase R, E or Z, optional whitespace,
then one or more ASCII digits. It removes only that interstitial whitespace.
Leading zeros, prefix case and all other characters are preserved. Tabs, repeated
spaces, NBSP and even a source line break between prefix and digits are whitespace.
No outer trimming, punctuation removal, case conversion, numeric casting, missing
prefix inference or unrelated-format conversion is performed. Whitespace-only IDs
become blank and are reported missing.

| Input | v2 EquipmentId | Treatment |
|---|---|---|
| R 123 | R123 | Normalized |
| E 456 | E456 | Normalized |
| Z 007 | Z007 | Normalized; zeros retained |
| E 00045 | E00045 | Normalized; zeros retained |
| R123 | R123 | Already normalized |
| Q 123, r 123, R-123, 00045 | Unchanged | Outside this normalization policy; review, not proof of an invalid equipment ID |
| R 12 3, or outer whitespace | Unchanged | Unsupported; no broad space removal |
| Empty | Blank | Missing; no prefix inferred |

RawEquipmentId copies the canonical raw source field verbatim. In repairs it may
include the original `Equipment Id:` label; services usually contain the literal
ID. Normalization therefore uses canonical EquipmentId, not the labeled raw cell.
The exact pre-normalization canonical ID is retained as CanonicalEquipmentId in
lineage, alongside RawEquipmentId. No cleaned or raw value is overwritten upstream.

Collision detection spans both fact tables and all included months. Different
**pre-normalization canonical IDs** converging on one supported ID form a collision
group (for example R 123 and R123). Repetition of the same original ID alone is not
a collision. Different source label wrappers alone are not different logical IDs.
Every affected transaction is flagged, with its normalized ID and sorted original
variants. No transaction is merged or deduplicated and no equipment lookup is made.

## Building policy — room-suffix-v1

The shared resolver reads canonical Location and preserves it exactly. It accepts
a likely building label followed by horizontal whitespace and a room token of
1–4 ASCII digits with an optional single letter suffix. Building labels contain
letters, spaces, apostrophes, periods, internal hyphens or ampersands; no digits or
multi-location delimiters. Generic standalone labels such as Building, Room and
Floor do not establish a building. Numbers in building names, room ranges, slashes,
multiple locations, line breaks and unsupported suffixes remain unresolved.

| Location | Building | Qualification |
|---|---|---|
| MC 188 | MC | Likely label from room pattern |
| Library 204 | Library | Same rule |
| STC 101A | STC | Single suffix letter allowed |
| Ricks 125 | Ricks | Same rule |
| Science and Technology Center 201 | Science and Technology Center | Multiword label retained |
| M.C. 188 | M.C. | Abbreviation retained; no expansion |
| MC | MC, conditionally | Only if MC is also observed in an unambiguous room-qualified location in this snapshot |
| Unknown building-only text | Blank | Unresolved |
| Building 2, Building 2 101, MC 188/190 | Blank | Ambiguous; no number/room guessing |
| Empty | Blank | Missing |

No authoritative Building_Dim or approved alias map was found in the repository.
The illustrative MC/Library/STC/Ricks names are **not a hardcoded departmental
vocabulary**. Building-only recognition uses exact, case-sensitive labels observed
in room-qualified locations across the same canonical snapshot. This is recorded
as ObservedPatternsNotAuthoritativeDimension, not validated departmental membership.
Adding/removing source observations can change whether a building-only label is
recognized. Repeated exports of the same input snapshot are deterministic.

Preserve Building_Dim and compare unmatched keys before creating relationships.
Numbered building names need reviewed dimension/alias evidence in a future policy;
the current resolver deliberately leaves them blank rather than truncating a name.
Only canonical Location is available to this layer; literal raw Location labels
already extracted by the cleaner are not reconstructed or invented.

## Legacy Power BI differences

Diagnostics retain separate reference derivations:

- Repairs: trim Location, take text before its first ASCII digit, trim the result.
- Services: take text before the final literal space, with no new trimming rule.
  No-space inputs have a blank reference; the original M error/fallback handling
  is not available to verify here.

These implement the documented reference descriptions, not executed Power Query.
For `Building 2 101`, the repair reference is `Building`, the service reference is
`Building 2`, and v2 leaves Building blank. For an unrecognized building-only label,
the legacy repair rule may retain the whole label while v2 leaves it unresolved.
Differences are reported rather than forcing the two policies to agree. Do not
reapply old Building or ID transformations to v2 imports.

## Exact schema and evidence

The four filenames remain unchanged, in a new immutable comparison container.
All unchanged business columns retain v1 order and types. The **only added fact
column is Building, immediately after Location**, in Repairs and Service Orders.
The **only changed existing field meaning is EquipmentId**, normalized as above.
RawEquipmentId and Location remain unchanged text; Building is text with empty
unresolved values. TMA and financial-summary CSV schemas/values are unchanged.

| File | Exact ordered v2 columns |
|---|---|
| Repairs_History.csv | ReportMonth, CompletedDate, EquipmentName, EquipmentId, Location, Building, ServiceVendor, RepairCount, RepairPersonHours, ReportedTotalCost, ReportedTotalCostStatus, EstimatedLaborCost, LegacyPartsCost, LegacyLaborCost, LegacyEstimatedTotalCost, Description, Details, AccountName, RawEquipmentId |
| ServiceOrders_History.csv | ReportMonth, EquipmentId, EquipmentName, ScheduledDate, CompletedDate, Location, Building, Description, Status, RawStatus, EstimatedPrice, RawDescription, SourceMaintenanceTag, AccountName, SourceVendorName, RawCost, RawEquipmentId |
| TMAWorkOrders_History.csv | Identical to comparison-preview-v1 (6 columns); no Building is inferred |
| RepairFinancialSummaries.csv | Identical to comparison-preview-v1 (20 columns); no amounts, totals or nulls are recalculated |

V2 adds `comparison_warnings.txt` at the top level and `audit/diagnostics.csv`.
The manifest binds both hashes, warning counts, ID/Building policy versions and
the observed-only Building knowledge policy. Existing canonical-copy integrity,
exclusive staging/finalization, path checks, failure cleanup and non-overwrite
guarantees apply unchanged. Python validation recomputes the entire projection,
lineage, collisions, diagnostics and report from retained canonical bytes.

Lineage retains all v1 columns and appends CanonicalEquipmentId, EquipmentId,
RawEquipmentId, Location, Building, BuildingStatus, EquipmentIdStatus,
LegacyBuilding, LegacyBuildingPolicy and Collision. TMA/summary extra fields stay
blank. Record numbers are parsed CSV ordinals, not physical multiline text lines.

Diagnostics columns: Dataset, ExportRecordNumber, ReportMonth, Issue,
CanonicalEquipmentId, RawEquipmentId, EquipmentId, OriginalVariants, Location,
Building, LegacyBuilding, LegacyBuildingPolicy, Explanation. There may be multiple
issues per occurrence. Categories cover missing/unsupported IDs, collisions,
missing/unresolved/ambiguous buildings and legacy-reference differences. Reports
are private operational evidence; do not share actual department rows in GitHub.

The desktop completion panel shows short counts/actions, without hashes or stack
traces. Read comparison_warnings.txt first; open audit/diagnostics.csv for affected
values and record references. Confirm ID aliases and Building_Dim matches with the
data owner before a model join. Warnings do not authorize corrections, approval,
activation, deduplication or changing source data merely to clear a warning.

## Windows acceptance

On this feature commit/review build, generate a NEW disposable invented demo:

```powershell
uv run --frozen --all-extras python examples/create_comparison_enrichment_demo.py --output data/comparison-v2-demo
uv run --frozen --all-extras python -m equipment_data_manager.comparison_export --verify data/comparison-v2-demo/comparison-1/comparison
uv run --frozen --all-extras python -m equipment_data_manager.ui.app
```

In Settings import the demo's workspace.toml, choose SharePoint year/month layout,
confirm local storage and save. Historical Data → Power BI snapshot → Development
tools → Create simplified comparison export. Select the demo's canonical/snapshot
folder and a separate local output parent. Check these synthetic expectations:

1. R 123 → R123 and E 00045 → E00045; RawEquipmentId remains literal.
2. MC 188 → MC, Science and Technology Center 201 → full name, observed MC → MC.
3. Building 2 101 remains blank; Q 123 remains unchanged and is reported.
4. R 123/R123 convergence is reported across facts/months; no transactions disappear.
5. The 18 repairs, 12 services, 13 TMA records and 6 monthly summaries match canonical
   counts. Six missing repair costs remain blank. Repeat to a fresh directory and
   compare CSV/evidence hashes. Cancel and try a corrupt source; old outputs survive.
6. Check the readable warning summary and trace an issue through lineage into the
   retained canonical file. Original candidate revision IDs/hashes remain unchanged.

The packaged UI performs validation itself; CLI commands are maintainer checks.
Do not run GUI suites and smokes concurrently on one display.

## Backup-PBIX checklist

- Save a separate PBIX copy; keep production PBIX/SharePoint untouched.
- Verify the completed comparison using Python first. M does not verify hashes.
- Import `fnReadComparisonPreviewV2.pq` as fnReadComparisonPreviewV2. Set a text
  ComparisonFolder parameter to one completed v2 comparison directory.
- Create four NEW disconnected queries:

```powerquery
= fnReadComparisonPreviewV2(ComparisonFolder, "repairs", true)
= fnReadComparisonPreviewV2(ComparisonFolder, "service_orders", true)
= fnReadComparisonPreviewV2(ComparisonFolder, "tma_work_orders", true)
= fnReadComparisonPreviewV2(ComparisonFolder, "repair_financial_summary", true)
```

- Keep text IDs/leading zeros and date/numeric nulls. Compare identical month coverage,
  row counts, hours, each financial meaning and missing values against canonical/v1.
- Inspect collision groups before joining Equipment; normalized-key agreement is
  not proof that two equipment observations refer to one asset.
- Compare Building against Building_Dim, missing/unmatched keys and each report's
  retained legacy reference. Do not chain legacy extraction/ID replacements onto v2.
- Preserve existing DAX, relationships, March exclusions and TMA Requests/Work Order
  semantics. No source-step replacement is authorized by this preview milestone.
- V1 helper accepts only v1; V2 helper accepts only v2. CLI regeneration of the
  original profile is supported by `--export-schema comparison-preview-v1`.

Native Windows packaging, real M/DAX evaluation, departmental aliases and owner
acceptance remain separate verification steps. No Equipment Type, MaintenanceType,
Equipment_History.csv, update mode, activation, Graph or automatic refresh is added.

## Local validation — 2026-11-19

- Final full Linux runner: **1,037 passed, 0 failures, 0 errors, 0 skipped**
  (963 core and 74 isolated real-widget cases).
- Final enrichment suite: **67 passed**. The broader focused export/historical/
  financial/help run earlier passed 168 cases; the final full run includes the
  additional line-break boundary regression.
- sdist and wheel builds passed. Source and isolated installed-wheel enrichment
  demos created repeatable six-month comparisons: 18 repair, 12 service, 13 TMA,
  6 summary rows. Counts: 12 normalized rows, 1 collision group/18 affected rows,
  6 unsupported IDs, 6 unresolved buildings and 6 legacy-reference differences.
  Six unavailable repair costs stay blank. The final wheel verifier passed.
- Source, isolated installed-wheel and frozen Linux executable phase-51 smokes
  and fresh-process settings restarts passed. Linux PyInstaller analysis used the
  image's Python runtime library directory to collect Tcl 9 dependencies; the
  resulting executable ran without a runtime library-path override. This is Linux
  evidence, not native Windows or departmental distribution acceptance.
- An existing Milestone 1a v1 bundle still validates. The original v1 regression
  suite/helper remain intact; v1 tests explicitly request that original profile.
- `git diff --check` passed. Cleaner/financial, canonical-generator, Settings,
  dependency and original Power Query helper files were unchanged.

Only invented test/demo data was written. Windows/hosted CI and actual M/DAX/model
results are not claimed; follow the owner acceptance checklist above.
