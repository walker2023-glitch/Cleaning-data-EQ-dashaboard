# Repair financial schema v2 and migration

## Evidence, implemented mapping and unresolved grouping

The owner has confirmed that the formatted report labels individual repair amounts
**Total Cost**, not parts. Local read-only inspection of the previously attached
January CSV found 29 retained records, Textbox38 equal to Textbox16 on every record,
and their sum equal to the owner's monthly reported total. Its repeated monthly
labor/parts/total/count fields are consistent and read once. Original bytes were
unchanged; actual financial values and source files are not committed here.

The formatted repair XLSX and February raw repair export are **not available** in
the current attachments. The January groups with multiple records all have zero
amounts; that cannot establish which field is a nonzero equipment subtotal. No
formatted Excel labels, merged cells or nonzero group semantics have been inspected
by this implementation. Supply those files privately to complete that work.

For the exact known 14-column CSV layout, v2 assigns ReportedTotalCost only when
both raw financial cells are valid money and their values agree. This implements
the newly confirmed total-cost meaning for that observed row shape. It does not
claim that equality alone establishes grain in every future export. Unequal cells
produce blank reported totals and `field_relationship_unverified`; missing or
malformed cells produce blank values, never zero. Other layouts retain processing
support, but leave source cost unassigned with `layout_unverified`. Do not restore
costs by guessing from equipment IDs, monthly summaries, or whichever field matches
a grand total. Nonzero equipment-subtotal layouts remain blocked pending evidence.

Legitimate repeated transactions remain separate, including identical transactions
and multiple repairs on the same equipment. No deduplication or allocation is
introduced. An overcount caused by repeated subtotal-shaped amounts will be exposed
by monthly reconciliation rather than silently corrected. A matching monthly total
is arithmetic evidence, not production approval or proof of each row's grain.

## Output contracts

Recommended desktop Power BI mode and CLI `--output-format powerbi` now use repair
schema **2**, ExportVersion **powerbi-v2**. Service/TMA remain schema 1/powerbi-v1.
The old schema-v1 Python factory remains available in processing.powerbi, and CLI
`--output-format powerbi-v1` explicitly selects compatibility output. Legacy mode
and all original/vendored cleaners, dates, exclusions, hours, rounding and labor
rate remain unchanged. The old field mapping survives only as labeled comparison
values; it is not silently used as current source financial meaning.

Repair v2 ordered business columns, followed by the unchanged COMMON provenance
columns documented in powerbi_output_design.md:

```text
LegacyRowNumber,CompletedDate,EquipmentName,EquipmentId,Location,ServiceVendor,RepairCount,RepairPersonHours,ReportedTotalCost,ReportedTotalCostStatus,EstimatedLaborCost,LegacyPartsCost,LegacyLaborCost,LegacyEstimatedTotalCost,RawTextbox38,RawTextbox16,Description,Details,AccountName,RawEquipmentId,FinancialSummarySHA256
```

ReportedTotalCost is nullable source dollars, **not plus estimated labor**.
ReportedTotalCostStatus is `source_fields_agree`, `field_relationship_unverified`,
`missing_or_malformed` or `layout_unverified`. EstimatedLaborCost copies the existing
hours/rate estimate exactly. LegacyPartsCost is the original calculation's mislabeled
parts value; LegacyLaborCost and LegacyEstimatedTotalCost are the original arithmetic,
not source charges. No per-repair actual parts/labor columns are offered. RawTextbox38
and RawTextbox16 preserve literal source cells, including malformed/blank values.
RawPartsCost is removed because its name incorrectly implies source parts semantics.

CompletedDate is ISO date; equipment IDs/text/descriptions and source ordinals are
preserved. Numeric costs/hours use finite base-10 numbers and blank nulls. Zero is
valid. LegacyRowNumber/RepairCount/ordinals remain whole numbers. ReportedTotalCostStatus,
raw fields, hashes and other metadata are text. ValidationStatus remains
CandidateUnverified. Source-derived RecordId remains an occurrence/provenance key;
it is not an approved business join key or a model relationship identifier.

### Separate monthly financial summary

Each repair revision also writes `CompuClean_RepairFinancialSummary_YYYY-MM.csv`,
one row only, header-first UTF-8, with ordered columns:

```text
ReportMonth,ReportedLaborCost,ReportedPartsCost,ReportedTotalCost,ReportedRepairCount,SourceRecordCount,RetainedRepairCount,KnownRepairTotalCost,UnavailableRepairCostCount,RepairTotalDifference,SummaryComponentsDifference,ReconciliationStatus,SourceSystem,ReportType,SourceFileName,SourceFileSHA256,LegacyCandidateSHA256,CleanerVersion,ExportVersion,SchemaVersion,ValidationStatus
```

ReportType is repair_financial_summary, schema 2/export powerbi-v2. Costs/differences
are nullable numbers, counts nullable whole numbers and other fields text. Repeated
Textbox10/11/12/13 values provide one monthly labor/parts/total/count, not a sum of
repeated cells. Source fields must remain consistent and count must match raw records
under existing strict validation. A layout without those fields yields blank reported
monthly values and `source_summary_unavailable`; nothing is inferred.

KnownRepairTotalCost sums only available retained individual totals. Missing values
are counted, not zero-filled. RepairTotalDifference = retained individual sum minus
reported monthly total, **only if every retained cost is known and no source records
were excluded**. Otherwise the difference is blank and reconciliation incomplete.
SummaryComponentsDifference = monthly labor + monthly parts minus monthly total
where all are available. Neither comparison changes source values or allocations.
Statuses: arithmetic_match, difference, incomplete_repair_costs_or_excluded_records,
source_summary_unavailable. Do not count a partial known sum as a complete total.

The companion's SHA-256 is embedded in the main CSV, whose hash is bound to the
manifest/replacement token. Both files must finish writing before selecting a
revision. Missing/changed companions block skips, corrections and review packets.
Failed writes keep the prior selection; an unselected orphan revision may remain.
This is application-level staged selection, not a two-file filesystem transaction.
No approved files/destinations are written. History and older schema-v1 artifacts
stay intact. Existing months require explicit correction review to select v2.

## Preview in VS Code

Close running desktop windows before syncing. Use the cloned repository, not an
extracted executable ZIP:

```powershell
cd C:\path\to\Cleaning-data-EQ-dashaboard
git fetch origin
git switch feature/repair-financial-mapping
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app
```

Select Power BI candidate mode and the confirmed month; preview a repair CSV.
Review source-cost availability/reconciliation warnings. Existing v1 selections
need explicit correction confirmation; original inputs and prior revisions remain.
Open the selected output folder to find the separate monthly summary. CLI results
also expose supplemental_output_locations. To preview privately without writing:

```powershell
python -m uv run --frozen equipment-data-manager process "C:\authorized-local\repairs.csv" --report-type repairs --period 2026-01 --output-dir data/private-v2-preview --output-format powerbi --preview
```

Never post private diagnostics, source rows, financial values or real provenance to
GitHub. Repository regression records/dollar amounts are invented; January/February
shapes use 29/5 records and synthetic monetary totals. The real January was checked
locally without committing it; actual February/Excel/grouped validation is pending.

## Multi-month Power Query pilot and model migration

Generate a new synthetic trial (the February example deliberately has a missing
individual cost to demonstrate incomplete reconciliation):

```powershell
python -m uv run --frozen python examples/create_powerbi_pilot.py --repair-financial-v2 --output data/financial-v2-pilot
python -m uv run --frozen python -m equipment_data_manager.powerbi_pilot check data/financial-v2-pilot/pilot/snapshot
```

Alternatively assemble explicit current monthly review packets with the existing
pilot commands. v2 packets now include a separately hashed financial summary in
repair_financial_summary/. Snapshots copy that separate folder under tables/.
The checker verifies hashes, provenance, exact file/month coverage, main-to-summary
hash binding, and rejects mixed repair schema versions. New baseline templates and
reconciliation use reported_total_cost/estimated_labor_cost and explicit legacy
metrics; they do not offer inferred per-repair actual parts/labor. Historical
snapshots/packets/versions remain outside the selected ingestion folder.

Follow powerbi_pilot.md's blank/backup PBIX safety steps. Existing schema-v1 queries
intentionally reject v2 repairs. In a separate review PBIX:

1. Load fnReadMonthlyFolderV2.pq as fnReadMonthlyFolderV2; keep v1 functions/queries
   only for explicit comparison. Set PilotSnapshot to the exact new snapshot folder.
2. Load PilotRepairsV2.pq as PilotRepairsV2, and PilotRepairFinancialSummary.pq as
   PilotRepairFinancialSummary. Use the existing service/TMA pilot queries (their
   schemas are unchanged). Set expected-month lists consistently to the snapshot.
3. Load fnMonthlyControlTotalsV2.pq as fnMonthlyControlTotalsV2 and
   PilotControlTotalsV2.pq as PilotControlTotalsV2. Review null coverage and statuses
   alongside every sum. Do not merge monthly totals into repair records or sum both
   a monthly total and individual totals as separate charges.
4. Keep pilot tables disconnected initially. Reconcile ReportedTotalCost from repair
   facts against the **single-row-per-month** summary. Monthly ReportedLaborCost and
   ReportedPartsCost belong at month grain; equipment/person/vendor visuals cannot
   receive actual parts/labor through an invented allocation.
5. Inventory impacted DAX and visuals before any migration. Existing PartsCost,
   LaborCost, EstimatedTotalCost and RawPartsCost columns are removed in v2; do not
   blindly rename them to new source fields. LaborCost was an estimate, not actual
   monthly reported labor. ReportedTotalCost already includes source costs; adding
   EstimatedLaborCost double counts. Legacy fields exist for reconciliation only.
6. Example new pilot measures, subject to model-owner review: SUM of
   PilotRepairsV2[ReportedTotalCost] for known reported repair costs; SUM of
   PilotRepairsV2[EstimatedLaborCost] for the separate estimate; SUM of
   PilotRepairFinancialSummary[ReportedLaborCost]/[ReportedPartsCost] for month-level
   reported components. Accompany each with missing-count/status controls. SUM alone
   can conceal nulls. Verify month/calendar grain and filtering deliberately.
7. Preserve existing table identities, relationships/Building_Dim/date joins, RLS,
   DAX/filter context and all visuals in the production model. Test only a copy;
   any later change needs explicit model/finance approval and rollback plan.

M syntax/reference tests do not run the Power BI mashup engine or validate existing
DAX. Actual M/model evaluation, formatted XLSX/nonzero group semantics, February
raw reconciliation, trusted expected outputs, hours/rate policy, precision/null
policy and production approval remain open. No SharePoint/Power BI publication or
approval-state change is part of this correction.
