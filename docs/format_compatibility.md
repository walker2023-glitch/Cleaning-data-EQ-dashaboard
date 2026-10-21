# Report-format compatibility

This matrix describes candidate processing, not approved production contracts.
All supplied attachments were **raw inputs**, not trusted cleaned outputs. The
January repair/service CSVs and January TMA XLSX were inspected locally; the earlier
February service CSV was checked in the preceding fix. No private file is committed.

| Type / layout | Extensions and layout gate | Required fields / optional values | Dates and exclusions | Candidate output | Unsupported |
|---|---|---|---|---|---|
| CompuClean repairs, observed summary export | UTF-8/BOM `.csv`, header first; exact 14-column set below enables summary checks | All 14 headers; equipment ID read as text, labels extracted by original cleaner; blank Details/cost/vendor follow original defaults | CompletedDate1 parsed by original scalar pandas parser; invalid dates or both ID/name empty excluded; all retained dates must match confirmed month | Original 11 columns and three preamble rows; original hours/rate/cost arithmetic | Excel, non-UTF-8, preambles, malformed widths/headers; mismatched count or inconsistent summaries |
| Repair source-derived subset (pre-existing) | Header-first UTF-8/BOM `.csv`; requires seven lookup headers | PersonnelId5, PersonnelId1, CompletedDate1, PersonnelId4, PersonnelId3, Textbox38, Details; additional columns warned | Same repair rules; old inference retained outside exact 14-column layout | Same repair schema/preamble | Missing lookup fields; summary reconciliation is only available for the exact observed layout |
| CompuClean service, no-price summary export | UTF-8/BOM `.csv`; exact ten-header set below, order may vary | All ten headers; VendorName may be blank; ID text; no Cost required or invented | ScheduledDate must be nonblank; at least one parseable scheduled/completed date; either date must belong to confirmed month; original description/status exclusions and fallback | Original eight columns; blank Estimated Price; summary/count metrics and warnings | Extra/missing headers for this new layout, conflicting/repeated count metadata, separate summary-only rows |
| Service, pre-existing priced flat export | UTF-8/BOM `.csv`; EquipmentId1, EquipmentName1, ScheduledDate, CompletedDate, Description, Cost, Textbox21 and exactly one Name/Location | Cost header required, values may be blank; extra source fields warned; conflicting EquipmentId/EquipmentName/StatusRaw aliases rejected | Same original service rules; pandas inference unchanged (bare numeric IDs can lose zeros here) | Same eight columns | Context-carrying legacy Equipment Details layout; Excel; missing Cost outside exact no-price layout |
| TMA, observed title/header/body/footer | `.xlsx`, exactly one sheet; exact five headers on second row; first row title `CU Repair WO History — <Month YYYY>`; last row `Total: N records` alone | All five headers required; Assigned To may be blank; textual IDs preserved; numeric Excel IDs cannot recover zeros already absent from stored values | Original vectorized requests date parsing, invalid dates / blank IDs / IDs starting `total` excluded; retained dates must match confirmed month | Existing requests writer: title row, five columns, MM/DD/YYYY dates, quoted CSV; explicitly provisional | `.csv`, `.xls`, alternate titles/preamble positions, multiple sheets, footer mismatch, missing/extra/duplicate headers |

Repair headers:

```text
AccountName2,PersonnelId5,PersonnelId1,PersonnelId3,PersonnelId4,CompletedDate1,Textbox38,Description,Details,Textbox16,Textbox10,Textbox11,Textbox12,Textbox13
```

Service summary headers:

```text
AccountName2,EquipmentId1,EquipmentName1,VendorName,ScheduledDate,CompletedDate,Name,Description,Textbox21,Textbox56
```

TMA headers:

```text
Work Order #,Request Date,Requestor,Request,Assigned To
```

## Output schemas and field limits

Repairs: `#, Completed Date, Equipment Name, Equipment ID, Location, Service Vendor,
# of Repairs, Repair Person-Hrs, Parts Cost $, Total Labor $, Est. Total $`.
The preamble/title is unchanged. Description, Textbox16 and AccountName2 are not
added to this fixed schema; raw inputs are preserved and unmapped fields warned.
Description/other cells may affect the original `found` duration heuristic.

Services: `Equipment Id, Equipment Name, Sched. Date, Completed Date, Location,
Description, Status, Estimated Price`. Suffixes `(Repair)`/`(PM)` are stripped as
before; placeholder descriptions and `delete duplicate...` descriptions are
excluded. Identical legitimate rows are **not** deduplicated. Blank/unrecognized
status values use the original Completed-if-completion-date-else-Scheduled rule,
with a new diagnostic for the summary layout. Explicit recognized status wins even
if it disagrees with date presence. AccountName2/VendorName stay in the raw input.

TMA: the five input columns in the same order. Its title is produced by the
existing requests writer. The source footer is validated/excluded before cleaning,
so input_rows counts work orders, not title/header/footer rows. This source shape
establishes compatibility with `requests_row_clean.py`; it does not prove the
candidate CSV matches an approved Power BI loader or expected cleaned result.
Legacy XLS needs a real sample and schema review. `xlrd` remains installed only
through the discovery extra; XLS is never decoded as CSV or inferred from XLSX.

## Reconciliation and the repair blocker

Service `Textbox56` and repair `Textbox13` report counts must repeat consistently
and match raw record counts. Repair `Textbox10/11/12` each provide one reported
labor/parts/cost metric, never a sum over repeated cells. Metrics distinguish
reported amounts from calculated output totals. Different values trigger
`repair_source_totals_differ`; equality is not production approval.

In January, the source's reported labor/parts/total disagree with the unchanged
cleaner's calculated amounts. It maps Textbox38 to parts and derives labor from
Details/default hours × 12.5. The raw Textbox38 and Textbox16 sums both match the
reported overall cost in this sample, which calls that parts mapping into
question. Privately derived financial amounts are omitted from this document.
Field meanings and the intended labor policy are unresolved. No field remapping,
rate/default adjustment or source-total substitution was made. Review candidates
before use; a trusted cleaned repair example and explanation of these fields are
required to resolve this.

See [edge-case evidence](edge_case_validation.md), [input requests](inputs_needed.md)
and [VS Code instructions](development.md#test-the-multi-month-branch-in-vs-code).

## Separate normalized output mode

The input matrix above is unchanged. An opt-in export layer produces the schema-v1
header-first UTF-8 candidates in [powerbi_output_design.md](powerbi_output_design.md)
only after the existing adapter succeeds. It does not enable new raw layouts/XLS,
change cleaning rules or approve financial totals. Legacy mode remains available.
Normalized candidate history is separate from legacy history and from any future
approved-current Power BI ingestion folder. The maintenance classifier is design
only: see [maintenance_classification_design.md](maintenance_classification_design.md).
