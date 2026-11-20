# Comparison export v3 — observed equipment and maintenance (Milestone 1c)

Contract: **comparison-preview-v3**, purpose **DevelopmentComparison**, status
**CandidateUnverified / NotApproved**. Built from verified main
`d7e9d0c39d4a8600dd4d03fd3a6c96c7d0f9d72c`. Milestone 1c is owner-approved for
implementation and review; it is not production activation or business signoff.

The same Process Multiple Months → Power BI snapshot → Development tools → **Create
simplified comparison export** action now generates v3. There is no permanent
format selector or competing employee workflow. Choose one validated completed
canonical snapshot, confirm backup-test intent, and choose a NEW separate trusted
local output parent, outside source/candidate/approved/production folders.
Only the completed `comparison` directory is importable. Five top-level CSVs are
accompanied by a manifest, readable warnings and private `audit` evidence.

V1 and V2 contracts, helpers and Python verification remain supported unchanged.
Maintainers can explicitly regenerate old profiles with
`--export-schema comparison-preview-v1` or `comparison-preview-v2`.
The canonical historical four-table contract, cleaning engine, financial schema 2,
Building/ID policies, candidate revisions and original source files are unchanged.

## Ordered schemas and types

All identifiers and YYYY-MM month fields are text, preserving leading zeros.
Dates are ISO YYYY-MM-DD, nullable. Financial/hour decimals and counts retain the
canonical serialized values and nulls; blank is never zero. NameConflict is a
logical `true`/`false` field and ObservationCount is an integer. Full ordered
schemas follow; the manifest repeats every column and type.

| CSV | Ordered columns (type) |
|---|---|
| Repairs_History.csv | ReportMonth (text), CompletedDate (date), EquipmentName (text), EquipmentId (text), Location (text), Building (text), ServiceVendor (text), RepairCount (integer), RepairPersonHours (decimal), ReportedTotalCost (decimal), ReportedTotalCostStatus (text), EstimatedLaborCost (decimal), LegacyPartsCost (decimal), LegacyLaborCost (decimal), LegacyEstimatedTotalCost (decimal), Description (text), Details (text), AccountName (text), RawEquipmentId (text), ObservedEquipmentName (text), EquipmentType (text), MaintenanceType (text) |
| ServiceOrders_History.csv | ReportMonth (text), EquipmentId (text), EquipmentName (text), ScheduledDate (date), CompletedDate (date), Location (text), Building (text), Description (text), Status (text), RawStatus (text), EstimatedPrice (decimal), RawDescription (text), SourceMaintenanceTag (text), AccountName (text), SourceVendorName (text), RawCost (text), RawEquipmentId (text), ObservedEquipmentName (text), EquipmentType (text), MaintenanceType (text) |
| TMAWorkOrders_History.csv | ReportMonth (text), WorkOrderId (text), RequestDate (date), Requestor (text), Request (text), AssignedTo (text) |
| RepairFinancialSummaries.csv | ReportMonth (text), ReportedLaborCost (decimal), ReportedPartsCost (decimal), ReportedTotalCost (decimal), ReportedRepairCount (integer), SourceRecordCount (integer), RetainedRepairCount (integer), KnownRepairTotalCost (decimal), UnavailableRepairCostCount (integer), RepairTotalDifference (decimal), SummaryComponentsDifference (decimal), ReconciliationStatus (text), EstimatedLaborCostSum (decimal), EstimatedLaborCostMissingCount (integer), LegacyPartsCostSum (decimal), LegacyPartsCostMissingCount (integer), LegacyLaborCostSum (decimal), LegacyLaborCostMissingCount (integer), LegacyEstimatedTotalCostSum (decimal), LegacyEstimatedTotalCostMissingCount (integer) |
| Equipment_History.csv | EquipmentId (text), EquipmentName (text), EquipmentType (text), FirstObservedMonth (text), LastObservedMonth (text), ObservationCount (integer), NameConflict (boolean) |

V3 Repairs/Services append ObservedEquipmentName, EquipmentType and MaintenanceType
to the V2 columns. **EquipmentName now means the shared resolved name**; the
transaction's canonical observed name is retained verbatim in ObservedEquipmentName.
This is a deliberate new contract, not a changed V1/V2 field. RawEquipmentId,
Location, Description, RawDescription and SourceMaintenanceTag are retained.
Repairs' Description is already the original source description in the canonical
contract. Service orders' RawDescription supplies the original, with cleaned
Description as secondary evidence. No missing raw field is reconstructed.
TMA and financial summaries have identical columns and values to V1/V2.

## Observed equipment, resolution and compatibility

One lookup row is generated per distinct nonblank V2-normalized ID observed in
selected Repairs and Service Orders. IDs are sorted as text. Unsupported IDs
remain literal keys with existing warnings. Whitespace-only IDs become blank
under V2 policy; blank-ID transactions remain in facts and have no lookup row.
Names never merge different IDs. Existing ID collisions remain warnings and must
be reviewed before joins; normalization does not prove two observations are one asset.

ObservationCount counts **every source fact occurrence**, including legitimate
repetitions, across both reports and all selected months. It is not a count of
unique repairs, assets or inventory movements. First/LastObservedMonth include
blank-name observations. Manifest equipment rows_by_month counts lookup rows by
**FirstObservedMonth**, not activity per month. No fictitious ReportMonth is added.

Name policy `recent-nonblank-month-repairs-first-v1`:

1. Select the latest ReportMonth with a nonblank name, independently of file times.
2. Same-month precedence is Repairs before Service Orders.
3. Within that report/month use ascending RecordId, SourceFileSHA256,
   SourceRecordNumber, CandidateRevisionId, observed name, then canonical ordinal.
   Identical observations tied at every stable key have the same resulting name.
4. Remove one z from case-insensitive Puzzi spelling (Puzzi → Puzi, puzzi → puzi).
   Other characters/case/whitespace remain. All-blank names resolve to empty text.

NameConflict flags more than one distinct nonblank **verbatim observed** name,
including case/spacing/spelling variants. All alternatives, blank observations,
source identifiers and selected results remain in audit/equipment_observations.csv.
The same resolved name and classification are used in both facts and lookup.
Blank-ID facts use their own observed name without inventing a shared lookup entry.

The owner's old DAX selects a lexical MAXX name. V3 deliberately uses the above
most-recent-nonblank policy, so some names and categories will differ. This observed
lookup is provisional, limited to the selected history, and **not a complete or
authoritative departmental inventory**.

Equipment policy `owner-dax-ordered-v1` preserves the supplied case-insensitive
substring order and exact labels: Battery-powered backpack vacuum;
Battery-powered vacuum; Backpack Vacuum; Vacuum Trash can; Vacuum;
Carpet Cleaner Head; Carpet Cleaning Machine; Carpet Cleaning; Upholstery Cleaner;
Upholstery machine; Scrubber; Burnisher; Buffer; Chariot; Agitator; Swing Arm;
Kaivac; Chemical Dispenser; Floor Fan; Ladder; Lift; Steamer; otherwise Other.
The exact predicates live in comparison_classification.EQUIPMENT_RULES.

Broad Vac, ICE and Trash matches are flagged even when legitimate. For example
Office Cart matches ICE → Scrubber, and Kaivac matches earlier Vac → Vacuum,
leaving the later Kaivac category unreachable under the supplied precedence.
No category was silently corrected. Refining boundaries, moving Kaivac, aliases,
case/space name equivalence and tie precedence changes require owner review.

## Maintenance evidence and uncertainty

Policy `source-evidence-conservative-v1` uses exact recognized source tags first,
original descriptions second and cleaned descriptions third. It never defaults
by report type. Recognized tags: PM, preventive/preventative, preventive/preventative
maintenance; Repair, Needed Repair, corrective/corrective maintenance (case-insensitive,
outer whitespace ignored). The literal tags/descriptions are preserved.

Preventive terms use word boundaries: PM, preventive, preventative, routine,
inspection, tune-up/tune up, scheduled, annual, quarterly. Corrective evidence
includes repair/repairs/repaired/repairing, replace/replaced/replaces/replacing/replacement(s), broken,
fault/faulty, failed/failure, leak/leaks/leaking, fix/fixed/fixing, damage/damaged,
and malfunction/malfunctioning. No PM match occurs inside equipment or shipment.

- **Preventive Maintenance**: preventive evidence without conflicting/negated evidence.
- **Needed Repair**: corrective evidence without conflicting/negated evidence.
- **Unclassified**: insufficient recognized evidence; a generic description is not proof.
- **Needs Review**: mixed preventive/corrective signals, negated/uncertain indicators or an
  unrecognized explicit tag. Negation is deliberately conservative: no, not,
  never, without, non, cancelled/canceled, didn't plus an indicator in that
  evidence field. Uncertainty markers (question marks, maybe/possible/possibly,
  unclear/unsure/suspected/might/may/whether, check if) with an indicator also
  require review. This flags rather than attempts to parse natural-language scope.

Lower-priority contradictions cannot be hidden by a higher-priority tag. Read
MaintenanceEvidence in the observation audit for the original inputs and signals.
This is a provisional keyword policy, not a validated maintenance decision.

Old DAX maps any substring pm/positive keyword to Preventative and **everything
else** to Needed Repair. V3 adds word boundaries, explicit tags, corrective
evidence and uncertainty. Compatibility mapping for comparisons only:

| V3 | Old model comparison label |
|---|---|
| Preventive Maintenance | Preventative |
| Needed Repair | Needed Repair |
| Unclassified | No faithful equivalent; compare separately |
| Needs Review | No faithful equivalent; review separately |

Do not collapse uncertainty into Needed Repair or overwrite the old DAX field.

## Audit, warnings and blocking errors

Existing audit/diagnostics.csv still holds ID/Building issues. New
**audit/classification_diagnostics.csv** flags conflicting names, Other equipment,
broad keyword matches, Unclassified maintenance and Needs Review maintenance.
Missing IDs remain in the existing diagnostics. comparison_warnings.txt summarizes
counts in plain language. Counts describe affected observations, not distinct assets.

**audit/equipment_observations.csv** preserves every fact's observed/resolved name,
rule, broad terms, conflict flag, lookup ordinal, original tag/descriptions and
maintenance signals. **audit/lineage.csv** retains original transaction provenance
and adds CanonicalDataset, ObservedEquipmentName, ResolvedEquipmentName,
EquipmentType and MaintenanceType. Each original fact has one link. Each equipment
row has **one link per contributing observation**, with CanonicalDataset and
CanonicalRecordNumber referring to retained audit/canonical. Thus lineage row
count intentionally exceeds business CSV row count. Parsed record numbers are
one-based excluding headers, not physical lines. Audit files contain private data.

Manifest binds CSV and audit hashes, counts, schemas and all policy versions.
Python verification reprojects every field and evidence file from the retained
canonical bytes. Schema/integrity failures and lookup/fact ID, name, type or count
mismatches block generation (`comparison_equipment_mismatch`); uncertainty is a
warning. Exclusive staging, atomic same-filesystem finalization, collision refusal,
path safety and failure cleanup reuse the existing pipeline. No transaction is
filtered/deduplicated, and no financial value or reconciliation is recomputed.
Caught failures remove only the newly owned container. Abrupt process/OS failure
can leave `.s`; never import it. Hashes are integrity checks, not signatures.

## Windows acceptance — synthetic first, then unchanged January–June

Use this review branch/commit, a NEW synthetic folder and a **backup PBIX only**.
Do not run GUI tests/smokes concurrently on one display.

```powershell
uv sync --frozen --all-extras
uv run --frozen --all-extras python examples/create_comparison_classification_demo.py --output data/comparison-v3-demo
uv run --frozen --all-extras python -m equipment_data_manager.comparison_export --verify data/comparison-v3-demo/comparison-1/comparison
uv run --frozen --all-extras python -m equipment_data_manager.ui.app
```

1. Import the synthetic workspace.toml in Settings/Advanced; choose SharePoint
   year/month layout, confirm trusted local storage and save. Generate v3 through
   the existing Development tools action, selecting the demo canonical/snapshot.
   Use a separate local comparison-output parent. Reopen the application to check
   restored settings and readable bundled help. A packaged app needs no Python.
2. Expect 18 Repairs, 12 Services, 13 TMA, 6 summaries and 3 Equipment rows; the demo
   contains 24 conflicting-name observations and 12 maintenance review observations.
   Six unavailable repair reported costs stay blank. E00045 retains leading zeros.
   Repeat to a fresh destination and compare hashes. Cancel once and try a corrupted
   COPY of a source snapshot; previous outputs and real inputs must remain unchanged.
3. Check matching lookup/fact names and types, normalized IDs and observation counts.
   Trace a name conflict and maintenance warning through audit files to canonical
   records. Existing ID collision and Building warnings should still be present.
4. Repeat using the **actual completed January–June canonical snapshot as read-only
   input**, with a separate new output folder outside department/raw/candidate/
   approved/production roots. Record source hashes before/after. Do not edit sources
   to clear warnings. Verify the bundle before importing. Actual Equipment row counts
   depend on the source; synthetic counts above do not predict departmental counts.
5. Compare original transaction counts by month/report, legitimate repeats, repair
   counts/hours, each reported/estimated/legacy financial field, totals and blanks.
   Keep reported totals separate from estimates; missing values are not zero.
6. Compare Building values against V2 and Building_Dim unmatched keys. BCTR and
   Clarke South Stair are owner-confirmed locations, not proof of dimension membership.

## Typed Power BI comparison

In a newly saved backup PBIX, paste powerquery/fnReadComparisonPreviewV3.pq as a
Blank Query named fnReadComparisonPreviewV3. Set a text ComparisonFolder parameter
to exactly one completed v3 comparison directory. Create five NEW disconnected
queries (no recursive folder import and no combination of export directories):

```powerquery
= fnReadComparisonPreviewV3(ComparisonFolder, "repairs", true)
= fnReadComparisonPreviewV3(ComparisonFolder, "service_orders", true)
= fnReadComparisonPreviewV3(ComparisonFolder, "tma_work_orders", true)
= fnReadComparisonPreviewV3(ComparisonFolder, "repair_financial_summary", true)
= fnReadComparisonPreviewV3(ComparisonFolder, "equipment", true)
```

Check explicit text IDs/months, nullable date/decimal values, integer counts and
logical NameConflict. The helper supports an empty header-only equipment table,
checks exact headers/types/counts and gates the development contract. It does not
verify hashes: run Python --verify first. Actual M evaluation requires Power BI
Desktop; static contract tests are not execution evidence.

Compare resolved versus observed names and old MAXX names; compare category
frequencies and inspect broad matches. Compare maintenance with the mapping above,
retaining uncertainty as separate categories. Disable auto-detected relationships
for these test tables; inspect that no unintended relationships were created.
Preserve existing DAX, relationship/filter settings, March exclusions and TMA
Requests/Work Order grains. Do not replace production source steps, reapply legacy
ID/Building rules, publish, refresh production or modify the production PBIX.
The backup PBIX and real-data acceptance are owner steps, not completed by CI.

## Developer validation

Implementation: comparison_classification.py is pure, called after unchanged V2
enrichment. comparison_export.py owns the versioned registry, serialization,
manifest, lineage and safe writing. No dependencies were added. Tests:
test_comparison_classification.py, existing V1/V2 suites, widgets and phase-51
packaged desktop/restart smoke. Equipment lookup is derived in the export layer,
not added to the canonical reader or cleaners.

```powershell
uv run --frozen --all-extras python .github/run_tests.py
uv build
uv run --isolated --no-project --with ./dist/equipment_data_manager-0.2.0-py3-none-any.whl python -I examples/create_comparison_classification_demo.py --output data/comparison-v3-wheel
.\packaging\build.ps1
.\dist\EquipmentDataManager\EquipmentDataManager.exe --smoke-test --smoke-dir data/comparison-v3-packaged-smoke
```

Windows CI is configured to run packaging/smoke on pushes of this feature branch
as well as PRs, including when GitHub API permissions prevent PR creation. Hosted
results, Windows executable tests and actual M/DAX/department data acceptance must
be recorded separately from local Linux results. See the local validation record below.

## Remaining owner decisions

Review broad equipment predicates and unreachable Kaivac; approve any refinements
separately. Confirm same-month report precedence and name-equivalence policy against
business expectations. Review maintenance vocabulary/negation and conflict outcomes
with departmental examples. Validate Building dimension keys, ID aliases and actual
PBIX comparisons. The existing report exclusions, financial rate/default policies,
coverage/grain and business accuracy still need their established reviews.

No monthly append/rebuild, activation/rollback, interface redesign, Workday, LLM,
new cloud service or automatic publishing/refresh is implemented. Do not begin the
next milestone without separate owner approval.


## Local validation — 2026-11-20

- Final full Linux/Python 3.12.14 runner: **1,137 passed, zero failures, errors or
  skips** (1,063 core plus 74 isolated real-widget cases), including 100 new
  classification/export tests. The final run includes uncertainty/negative phrase
  cases and synchronized bundled documentation.
- sdist and wheel builds passed. Installed-wheel six-month demo and verifier
  passed: 18 repairs, 12 services, 13 TMA, 6 summaries, 3 observed equipment rows.
  Repeated exports have identical file bytes, including audit evidence.
- V1/V2 projections, lineage, warning/diagnostic bytes, counts and manifests were
  compared directly with the verified-main implementation and matched for the
  same synthetic canonical snapshot. Original profile regression tests passed.
- Cleaner, financial, canonical-generator, Settings, dependency and original
  Power Query helper paths are unchanged. Only invented data was written.
- Source, isolated-wheel and native Linux PyInstaller desktop/restart results are
  recorded in docs/testing.md. Linux checks do not establish native Windows,
  actual M/DAX evaluation, departmental data or owner acceptance.
