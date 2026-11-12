# Historical snapshot compatibility: backup PBIX only

Status: CandidateUnverified. No approval, publication, refresh or PBIX edit.
This specification compares the actual EDM contracts with the owner's model
requirements and read-only metadata inspection of all four supplied PBIX backups.
All four had matching extracted schemas, M queries, DAX and relationship metadata;
file bytes differed. No private data, tenant URLs or PBIX files belong in Git.
The inspection used an isolated PBIXRay installation, not a runtime dependency.
Power Query and DAX were inspected, not executed or validated in Desktop here.

## Verified candidate contracts and proposed model mappings

Canonical CSVs keep every existing column, in its original order, followed by
ReportingMonth, CandidateRevisionId, CandidateOutputSHA256, CandidateCleanerVersion.
ReportMonth remains unchanged; ReportingMonth is its explicit snapshot alias.
Repairs require powerbi-v2 / schema 2; services and TMA retain powerbi-v1 / schema 1.
UTF-8, header-first, ISO dates, text IDs, decimal strings and empty numeric nulls
are preserved. No source data is re-cleaned. Repeated transactions stay present.
Cleaner versions must match the versions supported by this application. Unsupported
selected revisions require individual reprocessing review; never use an older fallback.

The following are verified **available fields** and proposed compatibility aliases.
They do not establish that the entire dashboard is interchangeable.

| Existing table/column | Canonical column | Type / qualification |
|---|---|---|
| Compuclean list[Completed Date] | Repairs.CompletedDate | date; model metadata datetime, date-only midnight cast for backup comparison |
| Compuclean list[Equipment ID] | EquipmentId | text, retain zeros; legacy R/E/Z spacing policy is a separate mapping |
| Compuclean list[Equipment Name] | EquipmentName | text |
| Compuclean list[Location] | Location | text, do not replace with Building |
| Compuclean list[Service Vendor] | ServiceVendor | text |
| Compuclean list[# of Repairs] | RepairCount | integer; keep SUM semantics separate from row counts |
| Compuclean list[Repair Person-Hrs] | RepairPersonHours | numeric, no hour recalculation |
| Compuclean list[Parts Cost $] | LegacyPartsCost | legacy arithmetic compatibility ONLY; this is NOT verified source parts cost |
| Compuclean list[Total Labor $] | LegacyLaborCost | legacy estimate compatibility, not source-reported labor |
| Compuclean list[Est. Total $] | LegacyEstimatedTotalCost | legacy estimate compatibility, NOT ReportedTotalCost |
| Service_Orders[EquipmentId1] | EquipmentId | text |
| Service_Orders[EquipmentName1] | EquipmentName | text |
| Service_Orders[Location] | Location | text |
| Service_Orders[ScheduledDate], [CompletedDate] | ScheduledDate, CompletedDate | date, nullable; preserve OR-period inclusion and cross-period completions |
| Service_Orders[Description] | Description | cleaned source-derived description; RawDescription retained for comparison |
| Service_Orders[Textbox21] | RawStatus | original source status text; Status is the cleaner's separate value |
| Service_Orders[AccountName2], [VendorName] | AccountName, SourceVendorName | text |
| Service_Orders[Source.Name] | SourceFileName | filename/provenance, not a business key |
| Service_Orders estimated price (requested requirement) | EstimatedPrice | nullable decimal; absent from inspected model's actual columns |
| Requests / Work Order[Work Order #] | WorkOrderId | text; repeated IDs NOT deduplicated |
| Requests / Work Order[Request Date] | RequestDate | date only; original time-of-day already lost by existing cleaner |
| Requests[Request Date Only] | RequestDate | date, preserve existing DATEVALUE calculated-column role |
| Requests / Work Order[Requestor], [Request], [Assigned To] | Requestor, Request, AssignedTo | text; May/June missing assignments remain blank |

The legacy generated-filename column in Requests is an import artifact. SourceFileName
is meaningful provenance, not a semantic replacement for a monthly filename column.
Service Textbox56 is a repeated source-summary string, not an individual estimated
price; it has no direct canonical field. Do not synthesize it from row counts.
No TMA candidate field gap exists for the six requested basic fields; **request time**
is a real fidelity gap. A future optional backward-compatible datetime export would
need source fixtures, a versioned contract and approval; do not change this cleaner.

## Building, identifiers and dashboard-only exclusions

Verified repair M derives Building using trimmed Location text before its first
digit (Text.SplitAny). Service M instead takes text before the final space.
These are different policies. Neither proves a reliable building key for every
location. Preserve Building_Dim and compare unmatched keys before changing sources.
Existing Equipment has text Equipment ID, Equipment Name and Equipment Type; no
inventory derivation is added by this feature. Existing R/E/Z-plus-space replacements
should be reproduced only in an explicitly reviewed Power Query compatibility layer;
retain canonical RawEquipmentId and EquipmentId, never numeric-cast identifiers.

Repair M explicitly excludes March 9 and March 18, 2026. Canonical snapshots retain
those records. Policy in the snapshot manifest is canonical_no_dashboard_exclusions.
To compare legacy totals in a backup, create a separately named compatibility view
with those **two exact dates** excluded and document the affected row/count/hour/cost
difference. Owner confirmation is required before adopting or removing that rule.
Service M also filters three specific test descriptions; the existing cleaner's
exclusions remain unchanged. Compare effects rather than copying dashboard filters
into canonical data. No automatic maintenance classification is added.

## Financial meanings and measure dependencies (DAX inspected)

RepairFinancialSummaries has one bound summary per selected repair month. Reported
monthly labor, parts and total are source-reported; KnownRepairTotalCost is explicitly
a known subtotal when UnavailableRepairCostCount > 0. RepairTotalDifference is blank
when reconciliation is incomplete. Monthly source totals cannot be allocated to
individual repairs. EstimatedLaborCost and Legacy* remain separate from source costs.
Four additional *Sum/*MissingCount pairs summarize existing estimated/legacy fields;
a sum is blank when any contributing value is missing. Do not sum a partial known
subtotal and label it a complete historical total.

Observed DAX impacts:

- Total Repair Cost, Total Estimated Repair Cost and Parts Budget Remaining depend
  on Est. Total $. Map to LegacyEstimatedTotalCost only for legacy comparison;
  changing to ReportedTotalCost changes their meaning and missing-value behavior.
- Parts Cost sums Parts Cost $; Labor Cost sums Total Labor $. Total Repair Cost real
  and Total Estimated Repair Cost (using parts) add those two measures. The label
  "real" does not establish source accuracy; legacy source-total-as-parts arithmetic
  can double-count estimated labor. Do not silently remap or rename those measures.
- Equipment Repair Hours sums Repair Person-Hrs; Total Repairs sums # of Repairs.
  Avg Labor Hours per Repair divides hours by that repair count. Preserve these
  identities; COUNTROWS is a separate diagnostic.
- Estimated Labor Cost applies its own DAX hourly rate, while the cleaner has its
  preserved estimate assumptions. Compare both; do not replace one with the other.
- Total Requests and Total Service Orders use COUNTROWS. Changing coverage or
  deduplicating WorkOrderId changes those results.
- Completed Service Orders counts nonblank CompletedDate. Avg Scheduled-to-Completion
  Hours ignores missing/reversed dates and uses date differences times 24; candidate
  dates have no time precision. Work Order Completion Rate actually filters
  Service_Orders[Is Valid Completion Order], not the Work Order table.
- Monthly Labor Capacity, Available Labor Hours, Hours Remaining, Capacity Used %
  and budget measures contain additional existing assumptions. Preserve and verify
  their reference-period/budget/rate policies with the owner.

The model has calculated Maintenance Type and Is Valid Completion Order columns
on services and Work Order, based on substring rules in Description/Request. Keep
those calculated columns in a backup migration; they are not canonical EDM fields.

## Requests versus Work Order: confirmed query differences, unresolved grain

Requests imports January–July raw folders, strips non-record rows, then appends
August and September. Work Order appends individual January–July queries and
September, **omitting August**. It is not a distinct-ID query. Neither inspected M
explicitly deduplicates. Read-only key checks found unique IDs in both tables in
the supplied backup inspected; that observation does not prove a future uniqueness
policy, an intended lookup role or equivalence of the two tables. Matching field names do not prove identical rows or grain.
Preserve all repeated events in TMAWorkOrders_History. Do not generate a deduplicated
Work Order dimension or independently replace both tables from this CSV.

The extracted relationships explicitly show Requests[Work Order #] -> Work Order
[Work Order #], active M:1 single-direction; September work-order query -> Work Order
is active 1:1 bidirectional. The owner's supplied date/equipment/building relationships
remain required constraints even though this inspection exposes only those two
business relationships. Verify the complete graph in Desktop before migration;
do not claim the extraction proves all expected relationships are present.

Owner-supplied constraints to retain and inspect:

| From | To | Status / risk |
|---|---|---|
| Compuclean list[Building] | Building_Dim[Building] | active; unmatched/blank buildings |
| Compuclean list[Completed Date] | Calendar[Date] | active; date/datetime and shared range |
| Compuclean list[Equipment ID] | Equipment[Equipment ID] | active; text normalization and unique equipment key |
| Service_Orders[Building] | Building_Dim[Building] | active; different Building derivation |
| Service_Orders[CompletedDate] | Calendar[Date] | active; completion may be outside reporting month |
| Service_Orders[EquipmentId1] | Equipment[Equipment ID] | active; leading zeros |
| Requests[Request Date Only] | Calendar[Date Only] | active; date-only |
| Requests[Work Order #] | Work Order[Work Order #] | active; many-to-one requires unique one-side key |
| Work Order[Request Date] | Calendar[Date] | inactive; retain intentional measure activation |
| September query[Work Order #] | Work Order[Work Order #] | extracted active 1:1 Both; must inspect before changing TMA |

Repetition counts in the manifest identify key risks without exposing identifiers.
A repeated WorkOrderId may be legitimate; never resolve cardinality by arbitrary
deduplication. Determine lookup/event role, unique-side policy and orphan handling
with the model owner before switching either TMA table.

## Backup-only connection strategy and coverage gates

1. Save a separately named PBIX copy. Do not refresh or publish the production file.
2. Select one completed snapshot/snapshot folder explicitly. Use exact four filenames,
   never Folder.Files over candidate versions or a directory of snapshots.
3. Import with the companion typed M function. It rejects unexpected headers; text
   identifiers, nullable decimals and ISO dates stay explicit. Python snapshot hashes
   establish integrity; M examples do not claim cryptographic integrity verification.
4. Initially load NEW comparison tables, without relationships. Limit both old and new
   data to the same months and compare per-month counts, IDs, hours, nulls and each
   financial meaning. Preserve warnings/reconciliation gaps, including missing prices.
5. Compare March exclusions separately; compare TMA request-time loss and repeated keys.
   January/February current TMA revisions must actually be selected and valid.
6. January–June does NOT supply July–September. Existing Requests includes August,
   while Work Order does not. Restrict all comparisons to shared coverage; do not
   remove those old monthly queries or claim a full-year replacement.
7. Preserve existing table identities, calculated columns, DAX, dimensions, date types,
   active/inactive relationships and slicers. Only after explicit model-owner approval
   consider editing a backup query's Source step; do not delete/recreate model tables.
8. Record all page/visual/relationship/DAX comparisons and finance/model decisions.
   Production migration, publication and refresh require a separate authorization.

Unresolved: Requests/Work Order grain and one-side uniqueness; exact building/key
policies; dashboard-only exclusions; July–September coverage; time-of-day fidelity;
rate/budget assumptions; finance approval; complete relationship graph in Desktop.
These gaps require explicit acknowledgement for local generation and block a claim
of complete dashboard compatibility. They do not authorize publication.
