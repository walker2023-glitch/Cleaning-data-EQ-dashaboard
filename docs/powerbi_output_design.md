# Power BI candidate export design — schema v1

This milestone adds an opt-in **Power BI CSV candidate** mode after the existing
cleaner validates a supported input. Legacy mode remains the default and keeps its
original bytes, writers, manifest and revisions. The new layer does not authorize
publication, change Power BI, or close the financial/trusted-output gates.

## Current output investigation

| Observation | Cause / evidence | Action in the separate export layer |
|---|---|---|
| Repair introductory rows | Original `_write_repairs_csv` deliberately writes title, generated count and blank row before its eleven-column header | Parse that exact candidate schema; write only one normalized header |
| TMA introductory row / non-ISO dates | Original requests writer adds its title and formats dates MM/DD/YYYY | Parse the validated five-column candidate; explicitly convert that known date representation to ISO |
| Extra empty/unnamed columns | Current writers use `index=False` and fixed row widths; an extra column is not reproduced. Treating a title row as a header produces unnamed columns; a re-export can also add trailing separators | Require exact candidate headers and widths. Do not silently drop unknown columns |
| `BYUâ€“Idaho` | A correctly UTF-8-encoded en dash can be decoded as a Windows code page by the consumer. This is distinct from already-corrupted source text | UTF-8, no BOM, no report title; explicitly use Encoding=65001 in Power Query. Preserve Unicode content; never guess repairs to already-corrupted text |
| `439` versus `000439` | Older pandas inference or a spreadsheet's type inference can remove zeros. Observed summary layouts already read IDs as text | Read candidate cells as strings; use a reliably paired literal CSV ID when the legacy ID is present. Never pad `439` to an invented ID. Preserve RawEquipmentId. Numeric Excel cells cannot recover absent zeros |
| Numeric types / missing costs | CSV itself has no types. Original money parsing may turn invalid/missing parts into zero and derive a total; service writer blanks unavailable/nonpositive price | Publish schema types below. Missing/invalid source parts become blank PartsCost/EstimatedTotalCost; explicit LegacyPartsCost/LegacyEstimatedTotalCost retain the original calculated numbers. This is null presentation, not a financial recalculation |
| Repeated summaries | SSRS repeats monthly totals on every row | Keep source reconciliation metrics separately in result metadata, never add repeated report totals to transaction CSVs |
| Repair financial disagreement | Source cost-field meaning and duration/rate policy remain unresolved | Preserve formulas and warnings; add an unconditional publication-blocked warning to normalized candidates |
| Lost descriptions / tags | Repair writer omits Description/Details; service cleaner strips `(PM)`/`(Repair)` suffixes and excludes placeholders | Use the retained-record trace to pair accepted CSV records with original cells. Add raw fields and suffix metadata without changing exclusions or implementing classification |

## Schema contracts

Every CSV has exactly one header, explicit ordered columns, UTF-8 encoding, CRLF
record separators, CSV quoting for commas/newlines/quotes, blank nulls, finite
base-10 numeric values without currency symbols/thousands separators, and dates
`YYYY-MM-DD`. Row order and legitimate repeated transactions are preserved.
Schema changes require a version increment. No classification is assigned.

Each report has its business columns below, followed by these common columns in
this exact order:

```text
RecordId,ReportMonth,SourceSystem,ReportType,SourceFileName,SourceFileSHA256,SourceRecordNumber,CandidateRecordNumber,LegacyCandidateSHA256,CleanerVersion,ExportVersion,SchemaVersion,ValidationStatus
```

ReportMonth is text `YYYY-MM`; SourceSystem is CompuClean/TMA; ReportType is the
engine key. SourceFileName is basename only, not a local/SharePoint path. Hashes
are SHA-256. CleanerVersion identifies the original adapter; ExportVersion is
`powerbi-v1`, SchemaVersion `1`, ValidationStatus `CandidateUnverified`.
RecordId is a source-revision-bound hash including type, period, source hash,
cleaner version and candidate ordinal. It is **not** a business event ID or a
cross-correction matching key. Identical transactions remain separate occurrences.
Renaming identical raw input skips and retains the first revision's filename.

SourceRecordNumber is the 1-based CSV data record from the validated trace (not
physical line). For TMA it is known by order only when no body rows were excluded;
otherwise blank with a warning, rather than guessed. CandidateRecordNumber is
always the 1-based retained-record ordinal. LegacyCandidateSHA256 permits comparison
with a legacy run using the same raw bytes, cleaner version, type and month.

### Repair History

```text
LegacyRowNumber,CompletedDate,EquipmentName,EquipmentId,Location,ServiceVendor,RepairCount,RepairPersonHours,PartsCost,LaborCost,EstimatedTotalCost,LegacyPartsCost,LegacyEstimatedTotalCost,RawPartsCost,RawTextbox16,Description,Details,AccountName,RawEquipmentId
```

Dates: CompletedDate. Integers: LegacyRowNumber, RepairCount. Decimals:
RepairPersonHours, PartsCost, LaborCost, EstimatedTotalCost, LegacyPartsCost,
LegacyEstimatedTotalCost. Other columns are text. Original `#`, vendor default,
counts and hours/labor calculations remain available. PartsCost retains the
**unverified original Textbox38 mapping**, with null for unavailable/malformed
source money. EstimatedTotalCost is null in that case too; its legacy number is
retained explicitly. LaborCost remains the original estimate, including original
hour defaults. RawTextbox16 is deliberately not labeled parts/labor: its business
meaning is unconfirmed. Description/Details/AccountName are source text.

### Service Orders

```text
EquipmentId,EquipmentName,ScheduledDate,CompletedDate,Location,Description,Status,RawStatus,EstimatedPrice,RawDescription,SourceMaintenanceTag,AccountName,SourceVendorName,RawCost,RawEquipmentId
```

ScheduledDate/CompletedDate: nullable dates. EstimatedPrice: nullable decimal,
retaining the original blank/nonpositive convention. Other business columns: text.
RawStatus preserves Textbox21 before the existing status fallback.
Description is the existing cleaned description; RawDescription preserves the
entire source cell. SourceMaintenanceTag records a final `(PM)` or `(Repair)` token
as `PM`/`Repair`, otherwise blank. This is source metadata, not a maintenance class.
No-price exports remain null; no price is inferred from report summaries.

### TMA Work Orders

```text
WorkOrderId,RequestDate,Requestor,Request,AssignedTo
```

RequestDate: date, converted from the known candidate MM/DD/YYYY format, never
re-parsed from raw data with a new inference rule. All other business columns:
text, including WorkOrderId and blank assignees. The original five useful fields
remain. There is no new Excel format support or guessed equipment/location link.

## Validation and totals

First run the unchanged adapter. A failure cannot become a normalized success.
Require its exact output header/row widths, output count, period and source trace
alignment; reject unknown normalized schemas or nonfinite/invalid numbers/dates.
Copy known calculated values with decimal formatting; do not implement new formulas.
Reconcile row counts and numeric copies against the candidate in tests. Separate
metrics retain source count/totals once. An equality check is not financial approval.
Keep private fields in candidate artifacts only, not logs/public fixtures.

## Storage and future publication

```text
approved-local-source/                 raw files; never modified
local-output/versions/...              original legacy candidates/history
local-output/powerbi_candidates/
  manifest.sqlite3                    selected normalized CANDIDATE per type/month
  versions/<revision>/...csv           immutable normalized candidates/history
future-approved-current/<report>/     NOT CREATED by this milestone
future-approved-history/...           NOT CREATED; outside ingestion roots
```

GUI mode selection and CLI `--output-format powerbi` use an independent normalized
coordinator/store under powerbi_candidates, with the same hash/version idempotency,
month conflict confirmation, immutable revisions, integrity checks and failed-write
protection. Legacy mode is still available for byte-for-byte comparison/rollback.
A normalized-only run invokes the legacy cleaner in memory; run Legacy mode to
persist its comparison CSV if not already saved. There is no claim of a two-file
atomic commit. Neither candidate versions directory is a Power BI ingestion root.

**No publication API/approval bypass is implemented.** Every normalized output
warns production publication is blocked. A future publisher must require trusted
raw/expected comparisons, reconciled financial meanings/totals, explicit schema
and month approval and reviewer identity; then stage/validate complete exports,
archive old approved versions outside the ingestion root and atomically select
one approved revision per type/month. Stale correction approvals must fail. Local
filesystem replacement/lease is not a Graph transaction: future storage interfaces
need conditional ETag updates, shared concurrency and recoverable publication
manifests. Failure must leave the last approved export selected. Publishing a batch
requires an explicit complete-set selection; no partial batch may be presented as
approved. Microsoft identity and SharePoint work require separate authorization.

## Power Query folder ingestion (design/test guidance only)

Use a separate approved-current folder per schema/report type. Filter exact folder
and `.csv`, hidden/temp files out; never recursively combine candidates/history.
Promote each file's first row exactly once, verify the ordered schema, combine rows
once across distinct ReportMonth files and apply explicit column types. Use
`Csv.Document([Content], [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv])`;
set identifiers/hashes/ReportMonth to text before any automatic type inference,
ISO dates to date, counts to whole number and decimal fields to an approved numeric
type. Currency precision/rounding must be approved before choosing fixed-decimal
versus decimal-number types. CSV cannot force Excel to preserve text identifiers.

Tests simulate folder combination with invented files only; they do not modify a
PBIX or create a production approved-current folder. Current candidates are format
ready, **not production approved**.
