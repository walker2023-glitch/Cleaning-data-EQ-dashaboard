# Data contracts: provisional, source-derived

**No report contract is verified yet.** The following columns come from inspected
source code, not sanitized exports. Synthetic fixtures characterize limited code
paths; they are not business approval or proof that source layouts match.

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

Unknown: actual raw row grain/header/export version, required versus optional
fields, ID normalization, period selection, units/currency approval, acceptable
duration defaults, exclusions and comparable source/Power BI totals.

## CompuClean service orders

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

Unknown: which layout(s) are in use, official record grain, required fields,
scheduled/completed inclusion rules including last-day timestamps, cost meaning,
description exclusions, status semantics, totals and target Power BI types.

## Requests / TMA work orders

The uploaded request reader finds a `Work Order #` header within the first 25
rows of CSV/XLS/XLSX inputs. The transform selects exactly `Work Order #`,
`Request Date`, `Requestor`, `Request`, `Assigned To`. It requires the work-order
column, filters blank/total IDs and invalid dates, fills a missing assignee with
an empty string, and writes dates MM/DD/YYYY. Its file writer prepends a title.

**Association with TMA is unconfirmed.** No separate TMA schema, date semantics,
cleaner, real export or approved cleaned output is available. Do not label the
synthetic request fixture as a TMA contract.

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
