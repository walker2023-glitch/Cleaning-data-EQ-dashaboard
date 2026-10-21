# Data contracts: provisional, source-derived

**No report contract is verified yet.** The following columns come from inspected
source code and the observed February service export. Synthetic fixtures characterize
limited code paths; they are not business approval or proof of production accuracy.

M1 enables only header-first UTF-8 CSV repair and flat service candidates. The
repair gate requires all seven input lookup fields listed below. The older priced flat service layout
requires `EquipmentId1`, `EquipmentName1`, `ScheduledDate`, `CompletedDate`,
`Description`, `Cost`, `Textbox21`, and exactly one of `Name`/`Location`. These
conservative guards define a supported subset; they do not declare organizational
required/optional fields. Duplicate/blank headers, competing aliases and malformed
row widths fail. Existing transformations/exclusions remain unchanged. Repair
results outside the confirmed month fail before artifact selection instead of
adding a new filtering rule. Invalid source dates/money produce diagnostics while
retaining original exclusion/zero behavior. See `cleaning_architecture.md` for policy.

## CompuClean repairs

Observed input lookups: `PersonnelId5` (labelled equipment name), `PersonnelId1`
(labelled equipment ID), `CompletedDate1`, `PersonnelId4` (location), `PersonnelId3`
(vendor), `Textbox38` (parts dollars), `Details` (duration). The code uses `.get`
and skips rows rather than declaring a complete required schema. Do not infer
that missing fields are acceptable to a production adapter.

Observed output order: `#`, `Completed Date`, `Equipment Name`, `Equipment ID`,
`Location`, `Service Vendor`, `# of Repairs`, `Repair Person-Hrs`, `Parts Cost $`,
`Total Labor $`, `Est. Total $`. Each accepted row emits one repair; dates are
ISO strings, hours numeric, labor rounded from hours × 12.5, and estimated total
is parts plus labor. The file writer adds three preamble rows before the header.

Observed: January has the 14-column summary layout in the compatibility matrix.
Its reported and calculated financial totals differ. Still unknown: export version,
business-required versus optional
fields, ID normalization, period selection, units/currency approval, acceptable
duration defaults, exclusions and comparable source/Power BI totals.

## CompuClean service orders

The observed no-price February export now has a specific adapter: exactly
`AccountName2, EquipmentId1, EquipmentName1, VendorName, ScheduledDate,
CompletedDate, Name, Description, Textbox21, Textbox56`. It reads equipment IDs
as text, validates the repeated `Total Service Orders` value against raw row count,
and emits the original eight-column schema with blank Estimated Price. It does
not infer cost from the summary. See `service_orders_february_fix.md` for mappings,
sanitized regression provenance, limitations and VS Code testing instructions.

Flat-layout detection uses `EquipmentId1` or `EquipmentName1`. Aliases:
`EquipmentId1` → `EquipmentId`, `EquipmentName1` → `EquipmentName`, `Textbox21`
→ `StatusRaw`; `Name` becomes `Location` when no location exists. Other lookups:
`ScheduledDate`, `CompletedDate`, `Description`, `Cost`. Legacy layout instead
carries equipment context across rows using `EquipmentId`, `Name`, `Location`,
and `Cost`.

Observed output order: `Equipment Id`, `Equipment Name`, `Sched. Date`,
`Completed Date`, `Location`, `Description`, `Status`, `Estimated Price`.
Dates are ISO or blank; status is Scheduled/Completed; nonpositive price is blank.
An accepted row must match the supplied month in schedule OR completion when a
month is passed; this is not yet an approved reporting-period rule. Output writer
emits a plain header-first CSV.

Observed: January and February use the ten-column summary layout. Still unknown:
official record grain, business-required fields,
scheduled/completed inclusion rules including last-day timestamps, cost meaning,
description exclusions, status semantics, totals and target Power BI types.

## Requests / TMA work orders

The supplied January TMA XLSX matches the original requests reader/transform:
a report title, five headers on row two, work-order rows and a final total row.
The strict adapter enables only this shape, not every layout the original reader
could scan. See [the compatibility matrix](format_compatibility.md).

Input/output columns: `Work Order #`, `Request Date`, `Requestor`, `Request`,
`Assigned To`. Existing logic excludes blank/`total` IDs and invalid dates, formats
dates MM/DD/YYYY and retains blank assignees. The original writer prepends its
`CU Repair WO History — <Month YYYY>` title. The adapter validates/excludes the
footer and requires the title/retained dates to match the confirmed month.

This establishes input compatibility, **not** approved TMA output accuracy or
Power BI loader compatibility. No trusted cleaned example was supplied. Legacy
XLS and other workbook/CSV variations require actual samples before enabling.

## Comparison baseline to complete

For each approved pair record: source/export version and format, encoding,
delimiter, preamble/header row, column order/types/aliases, row grain and key
semantics, confirmed YYYY-MM, timezone/date interpretation, full last-day
inclusion, raw/accepted/rejected counts with reasons, expected output name and
bytes/schema, and evidence of approval. Document repair counts, hours, parts,
labor and estimated totals where comparable; use approved numeric tolerances
rather than assuming exact floating-point equality. For service/TMA document
applicable counts/status/cost totals without inventing metrics. Preserve unknown
columns or explain approved handling. Supply boundary and failure cases listed
in [inputs_needed.md](inputs_needed.md).

The desired `Source_ReportType_YYYY-MM.csv` convention is a design target;
legacy writers differ. Resolve the header/preamble/type contract with the
existing Power BI baseline before any adapter changes or PBIX modification.

## Opt-in normalized candidate contracts (schema v1)

The separate export design in [powerbi_output_design.md](powerbi_output_design.md)
defines ordered header-first Repair History, Service Orders and TMA tables with
ISO dates, typed numeric contracts, text identifiers, ReportMonth and provenance.
Legacy cleaners/CSV contracts above remain available and unchanged. Missing source
money is represented as null in the normalized business fields, with explicit
legacy calculated columns retained for comparison. Description/tag metadata is
preserved; no classifier is implemented. Publication remains blocked pending
financial reconciliation, trusted outputs and schema approval.
