# Power BI compatibility audit — November 24, 2026

## Evidence and limits

Directly inspected current `comparison_export.py` FIELDS/FIELDS_V2/FIELDS_V3,
`comparison_enrichment.py`, `comparison_classification.py`, the 53-line
`powerquery/fnReadComparisonPreviewV3.pq`, existing canonical contracts, independent
acceptance tooling and relevant tests/docs. No PBIX, BIM, TMDL or current extracted
model artifact was available in the repository or present uploaded attachments.
No Power BI/M/DAX engine was executed; no model or departmental file was changed.

[Historical compatibility findings](../historical_powerbi_compatibility.md) record
an earlier read-only inspection of four owner-supplied backups, including selected
M, measure and relationship observations. Those are **recorded prior evidence**, not
newly re-extracted or proof of today's live model. The older backup-migration guide's
“no metadata” wording must be read as lack of raw/current artifacts, not a denial
of those recorded findings. Do not invent missing formulas/queries/relationships.

## Verified V3 import contract

- Exactly five datasets: Repairs_History.csv, ServiceOrders_History.csv,
  TMAWorkOrders_History.csv, RepairFinancialSummaries.csv, Equipment_History.csv.
- Repairs/services have normalized text EquipmentId, preserved RawEquipmentId,
  resolved EquipmentName, ObservedEquipmentName, EquipmentType, Building and
  MaintenanceType. TMA has only ReportMonth, WorkOrderId, RequestDate, Requestor,
  Request, AssignedTo: no equipment/building/maintenance enrichment is promised.
- Equipment is an **observed** lookup: EquipmentId/Name/Type, FirstObservedMonth,
  LastObservedMonth, ObservationCount, NameConflict. It is not an authoritative
  asset inventory, including inactive/unobserved assets or current asset locations.
- Financial fields retain separate reported, estimated and Legacy* meanings. Null
  amounts remain null; IDs stay text; legitimate repeated events remain.
- Private lineage maps each exported fact to exact canonical/candidate/source
  evidence. The equipment lookup has one-to-many observation lineage. V3 cannot
  be treated as a canonical schema replacement or a production approval artifact.

The M helper requires explicit `AllowDevelopmentComparison=true`, exact V3 purpose/
status/schema, filenames, ordered headers/types and dataset-entry structure. It
parses text IDs, nullable ISO dates/numbers, integers/logicals and checks row and
month counts. Equipment counts group on **FirstObservedMonth**, not every month
of inventory presence. It uses exact File.Contents paths, not recursive Folder.Files.
Decimal fields are declared `type nullable number`, not a promised fixed-currency
model type. Check precision, scale and rounding against the actual model before
finance sign-off; no automatic type or calculation change is proposed.
It does **not** verify SHA-256, approve data, validate dimension authority or certify
relationships/DAX. Run Python verification and the independent analyzer first;
the documented Python scalar-type defect remains separately owner-gated.

## Proposed migration mapping — backup PBIX only

Mappings below are candidates for a disconnected comparison layer. Retain existing
model table identities/calculated columns/relationships/measures; a future approved
source-step change must preserve the exact reviewed legacy headers/types. Never
silently replace the production query or automatically recreate model tables.

| Existing model object | Proposed V3 input and aliases | Required decision or blocker |
|---|---|---|
| Compuclean list | repairs; Completed Date ← CompletedDate; Equipment ID ← EquipmentId; Location ← Location; Service Vendor ← ServiceVendor; # of Repairs ← RepairCount; Repair Person-Hrs ← RepairPersonHours | V3 EquipmentName is resolved; ObservedEquipmentName retains the observation. Choose legacy-observed versus resolved display meaning explicitly. Preserve RawEquipmentId; do not apply legacy normalization twice. |
| Compuclean list financial columns | Parts Cost $ ← LegacyPartsCost; Total Labor $ ← LegacyLaborCost; Est. Total $ ← LegacyEstimatedTotalCost **only for labeled legacy comparison** | These aliases do not mean actual per-repair parts/labor. ReportedTotalCost is distinct; monthly reported parts/labor exist only in summary. No silent DAX semantic switch or monthly allocation. |
| Service_Orders | service_orders; EquipmentId1 ← EquipmentId; EquipmentName1 requires observed/resolved choice; ScheduledDate/CompletedDate/Description ← same-name fields; Textbox21 ← RawStatus; AccountName2 ← AccountName; VendorName ← SourceVendorName | Preserve RawDescription and Status separately. EstimatedPrice is nullable; Textbox56 is not a per-order price. V3 has no direct Source.Name column; use private lineage for provenance, not a fabricated business field. Source grain/date OR-inclusion and old exclusions need comparison. |
| Equipment | equipment; Equipment ID ← EquipmentId; Equipment Name ← EquipmentName; Equipment Type ← EquipmentType | Stage disconnected first. Confirm unique normalized keys, aliases, name conflicts, missing and unobserved assets. Do not replace authoritative inventory or use ObservationCount as asset count. |
| Requests | tma_work_orders; Work Order # ← WorkOrderId; Request Date/Request Date Only ← RequestDate (date-only); Requestor/Request/Assigned To ← Requestor/Request/AssignedTo | Confirm intended event grain and actual monthly coverage. No time-of-day restoration, invented EquipmentId or deduplication. Preserve blanks/legitimate repeats. |
| Work Order | Same TMA file is only a fact-input candidate, **not** an approved unique-side lookup | Do not independently connect both Requests and Work Order to identical TMA rows. Prior recorded M has different August inclusion. Establish key uniqueness, lookup/event role and one-side policy; repeated IDs cannot be arbitrarily removed. |
| Building_Dim | Retain existing owner-authorized dimension; compare fact Building keys against a private approved key export | No authoritative dimension is supplied. New derivation differs from legacy repair/service M; normalization is not membership proof. Do not add Clark/BCTR aliases or infer current asset location. |
| Calendar | Retain existing dimension and explicit date/reporting roles; compare CompletedDate/ScheduledDate/RequestDate and ReportMonth coverage | Preserve active/inactive links and date versus datetime types. Do not invent fiscal rules or replace the Calendar with observed dates. Missing history outside shared periods remains a blocker. |
| Existing DAX measures | Preserve expressions and identities while staging new tables | Current expressions/dependency graph are unavailable. Record expected values by page/filter context before any model change; proposed aliases alone do not prove equivalent financial or date behavior. |

The separate repair financial summary has one row/month. Do not join its monthly
reported costs onto every repair/equipment row or sum a known partial subtotal as a
complete actual total. A month-role relationship requires model-owner review.

## Recorded legacy differences requiring explicit reconciliation

The earlier inspection recorded repair M exclusions on **2026-03-09** and
**2026-03-18**, distinct repair/service Building derivations, service test-description
filters, Requests including August and Work Order omitting August, and a Requests →
Work Order active many-to-one key relationship. It also recorded an inactive Work
Order request-date calendar link and a September-query bidirectional 1:1 link.
Only a subset of relationships was extracted. Preserve the owner-supplied remaining
constraints; do not claim that subset is the complete current relationship graph.

Recorded measure dependencies include Total Repair Cost/Total Estimated Repair Cost
on legacy Est. Total $, Parts Cost and Labor Cost on legacy money columns, Total
Repairs on # of Repairs, repair hours on Repair Person-Hrs, COUNTROWS-based service/
request measures, and a completion-rate measure filtering a service calculated
column. These are dependency findings, **not formulas supplied or revalidated here**.
Rate, capacity, budget and calendar assumptions still need the actual model.
Existing calculated Maintenance Type must not be silently replaced by V3
MaintenanceType; compare rule evidence/unknowns first. Kaivac precedence and all
classification policies remain unchanged.

## Safe comparison procedure and missing evidence

1. Keep production closed/unchanged. Use a separately saved backup (or a blank PBIX
   for fully offline imports); a backup may still have live queries until isolated.
2. Validate exactly one completed V3 export and matching canonical snapshot; run
   analyzer, optionally with private approved Building keys. Do not concatenate
   versions or use canonical and V3 tables as two sets of the same transactions.
3. Add fnReadComparisonPreviewV3 and import NEW disconnected tables with explicit
   development opt-in. Keep old model queries/relationships/DAX unchanged.
4. Restrict comparisons to identical reporting coverage and filter context. Compare
   each monthly row/repair count, hours, identifiers/repeats, nulls, every distinct
   financial meaning, name resolution, Building unmatched keys and warning policy.
5. Test the March exclusion view separately, and separately compare Requests/Work
   Order coverage and key cardinality. Record differences rather than forcing totals.
6. Inventory all pages/visuals, measures, calculated objects, sort columns, RLS,
   relationships/directions/cardinalities/date roles and refresh credentials/settings
   in a private current model export. A simple text search is not full dependency proof.
7. Obtain finance/data/model-owner decisions. Only then propose a specific source
   migration on the existing backup table identities; production remains separate.

Still needed: current private model metadata (M/DAX/relationships/visual dependencies),
authorized same-period baseline and totals, complete intended history (not assumed
January–June equals full year), approved inventory/Building authority, observed versus
resolved name policy, TMA unique-side/grain policy and actual Desktop execution.
No blocker requires changing financial or classification rules autonomously.
