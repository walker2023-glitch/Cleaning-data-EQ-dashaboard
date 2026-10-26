# Offline cleaning architecture (M1)

Multi-month compatibility adds strict repair metadata and provisional TMA XLSX
candidates; see `format_compatibility.md` for current gates and evidence limits.
M2 adds a local desktop caller; see `desktop_architecture.md`. M1's calculations,
date rules, exclusions and source identity remain unchanged. The coordinator now
also exposes `preview(request)`, using the same decision path with a read-only
manifest and no artifact writes. `store.history()` returns recorded revisions.
Preview and history do not create an absent output folder or manifest.

```mermaid
flowchart LR
    Caller[CLI or future controller] --> Input[Explicit type, confirmed month, input bytes]
    Input --> Manifest[Lock manifest and check current revision]
    Manifest --> Adapter[Layout guards and original transformation]
    Adapter --> Candidate[CSV candidate plus counts and warnings]
    Candidate --> Review[Check replacement acknowledgement]
    Review --> Revision[Write immutable artifact]
    Revision --> Select[Commit current revision in SQLite]
```

## Python interface

```python
from pathlib import Path
from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import ProcessingRequest

engine = ProcessingCoordinator(Path("data/local-candidates"))
request = ProcessingRequest(
    report_type="repairs",
    period="2026-09",  # confirmed by operator/content, never filename alone
    input_path=Path("tests/fixtures/synthetic/repairs_input.csv"),
)
result = engine.process(request)
# Or pass raw_bytes=b"...", source_name="report.csv" instead of input_path.
# process_many([request, ...]) returns ordered results and continues on failure.
```

`ProcessingResult.status` is success, skipped, needs_review or failure. It includes
a safe category `code`, warnings, optional `cleaned` candidate, row counts,
`artifact`/`output_location`, previous revision metadata and a replacement token.
Unknown counts/locations on failures are `None`. `CleanResult` carries bytes,
schema, warnings, counts, confirmed period, cleaner version and calculated repair
metrics. Those metrics are not reconciled source/Power BI totals. Failure messages
omit raw exceptions/cell values. Candidate bytes may contain sensitive report
values; never log/repr the complete result in a real integration. The manifest
does not store raw input bytes or source filenames.

For a corrected month, the first request returns needs_review with previous
hashes/counts and proposed bytes/counts/metrics for caller inspection. No new
artifact or active revision is selected. Re-submit the same request with its
`replacement_token` after reviewing it. The token binds the current revision,
proposed source hash, cleaner version and output hash. Changing any of them
requires new review. This prevents stale acknowledgement; it does not authenticate
the operator or provide an automatic business-data diff.

## Existing logic and supported subset

The repair wrapper calls `clean_repairs_raw` and the original preamble writer.
The service wrapper calls `clean_service_raw` with the confirmed month and retains
the existing plain CSV serialization. Four modules are bundled under
`processing/_legacy`; only absolute `clean.row_clean_common` imports become
relative imports. Tests compare copies with the preserved originals and compare
wrapper outputs against the original transform/writer.

Older layout readers retain pandas type/NA inference. Duration defaults, 12.5 labor rate, repair
counts, costs, date parsing and exclusions are unchanged. Output names are the
year-qualified design names, inside revision directories. Filename month/year
inference and original local `main()`/`process_file()` workflows are never invoked.

Exception: the specific observed no-price Service Orders export now reads
`EquipmentId1` as text to retain leading zeros, checks repeated report-count
metadata and adapts the absent price to the original blank-price path. The older
priced-layout reader and original transforms remain unchanged. See
`service_orders_february_fix.md`; this is not an arbitrary missing-column fallback.

CompuClean accepts only UTF-8/UTF-8-BOM header-first CSVs. Required columns are a
conservative list of fields used by the supported transforms (`data_contracts.md`).
Flat service lists may have `Name` or `Location`; competing aliases fail.
CompuClean preambles, legacy service context layouts, Excel, unknown schemas,
duplicate/blank headers, malformed row widths and unsupported encodings fail
explicitly instead of guessing.

The exact 14-column repair layout reads the ID field as text and checks repeated
count and labor/parts/cost metadata. Each reported total becomes one separate
metric, not a per-row transaction. Disagreements with calculated totals warn;
original mappings/calculations are untouched. The observed January disagreement
is an unresolved business-data blocker, not a successful financial reconciliation.

`TmaXlsxCleaner` reads bytes with pinned openpyxl, requires one sheet and the exact
observed title/second-row headers/final summary, and calls the source-preserved
requests transform/writer. Title/header/footer are not input records. Footer count
must match body count; retained dates must match the confirmed month. Output is a
provisional five-column CSV with its original title row and MM/DD/YYYY dates.
Legacy XLS remains blocked pending an actual sample (xlrd is discovery-only).
Inventory depends on missing `dashboard.taxonomy` and is outside this milestone.

## Validation policy

- Reject missing required columns, ambiguous/unknown layouts, empty/no-output
  inputs, nonfinite numeric outputs, and repair results outside the confirmed
  month. Mismatches fail instead of silently adding repair filters.
- Service retains its scheduled-OR-completed month inclusion rule and warns about
  cross-period dates in accepted rows without excluding additional records.
- Invalid dates/malformed money produce category/count warnings. Existing date
  exclusions and money-to-zero behavior remain unchanged. Duration heuristics,
  defaults and rate are explicitly unverified. Unknown source columns and excluded
  counts are reported; business records are not deduplicated.
- Every candidate warns `production_accuracy_unverified`. Local success means
  wrapper/structural checks passed, not approval to publish. Source counts and single reported repair totals are now exposed for the exact
  observed layouts. Financial agreement, detailed rejected-row audit and business
  approval remain unverified.

## Duplicate protection and durability

One selected revision exists per `(report_type, confirmed period)` in SQLite.
Each revision records source/output SHA-256 hashes, cleaner version, counts and
warnings. Identical raw content + cleaner version skips after restart or rename.
An output must still exist and match its hash to skip/replace; missing/tampered
artifacts fail without silent repair or overwrite. Different content or a changed
cleaner version requires review. Filenames are not identities: equal basenames
in different months cannot overwrite, and renaming cannot bypass month review.

SQLite `BEGIN IMMEDIATE` serializes local check/select operations, including the
acknowledgement check. A new exclusive random revision directory holds the staged
CSV; it is flushed, fsynced and renamed within that directory. Only after the
artifact exists is metadata inserted and the active pointer committed. Success
returns after commit. Prior revisions and inputs are never modified.

A failed write/transaction leaves the previous selection intact. Interruption
after file rename and before database commit can leave an **orphan immutable
artifact**; file existence alone never selects it. This is not an atomic
filesystem-plus-database transaction or protection from power-loss corruption.
Readers must use manifest-selected results, never recursively combine `versions/`
CSVs, which include history/orphans. Retain the store for diagnosis after integrity
failure; recover from a trusted backup in a separate reviewed action. Automatic
orphan cleanup, backup/restore UI and flat Power BI export publishing are deferred.

The store assumes a trusted application-controlled local directory and one local
manifest. It does not provide a network-filesystem lease or multiuser SharePoint
commit protocol. Future adapters can consume candidate bytes/metadata after
approved validation and publication controls are implemented.

## Local CSV rejection context

CSV results and date/empty-output errors now carry optional `CleaningDiagnostics`.
The observer reuses original helpers in first-exclusion order and verifies retained
count parity with the original cleaner. It changes no parsing/filtering/calculation
rules. Diagnostics contain period/fingerprint/version, source data-record numbers,
reason counts and raw/parsed date observations; no identity/descriptive/money cells
are collected. Raw date cells are excluded from repr/default CLI summaries, visible
locally in the GUI or opt-in CLI trace, and never persisted in SQLite history.
Failures still expose category-only exception strings and create no selected output.
`process --preview` uses the existing read-only coordinator path. See
`january_rejection_investigation.md` for scope, privacy and the pending reproduction.

## Separate Power BI table exporter

`processing/powerbi.py` wraps an existing adapter, verifies its exact candidate
schema/count and uses CSV diagnostic source ordinals for supported raw-field
preservation. It serializes the schema-v1 header-first tables independently of the
original writers. It does not alter source filtering, dates or financial formulas.
TMA uses the known legacy date representation; excluded TMA rows do not get guessed
source ordinals. Optional raw metadata remains in private candidate artifacts.

`powerbi_coordinator(base_root)` uses the same ProcessingCoordinator and immutable
local store at base_root/powerbi_candidates with independent cleaner identities,
skips and correction tokens. `DesktopWorkflow(output_format='powerbi')` and CLI
`--output-format powerbi` call this factory; the desktop recommends/defaults to
Power BI candidates, while CLI/API defaults remain legacy. Original
legacy adapters/outputs/history remain available. Normalized metrics are labeled
Legacy where copied from the original candidate. Normalized missing financial
values are explicitly null with original calculated numbers retained separately.

There is no publisher or approved-current folder API. Every normalized candidate
carries CandidateUnverified and a publication-blocked warning. See
`powerbi_output_design.md` for schema/folder/approval design. Matching and maintenance
classification remain documentation only in `maintenance_classification_design.md`.

## Monthly local orchestration

`monthly.py` validates separate configurable roots and discovers only direct files
in raw/YYYY-MM/type. `DesktopWorkflow.preview_month` delegates each type group to
the existing write-free preview and conflict logic, then uses the same sequential
process API and source-bound correction tokens. Missing-report coverage is explicit;
no filenames override content validation or month rules. `export_review_packet`
reads all three selected normalized candidates in one read-only SQLite transaction,
verifies hashes/schema/count/month, and copies them to an exclusive staged packet
before local rename. It never writes approved outputs. Packets are monthly candidate
snapshots, not an approved-current pointer or a rolling multi-month publisher.
Power Query must use an explicit snapshot/report folder, never revision discovery.
See `monthly_workflow.md` and `powerquery_integration.md` for exact guarantees/limits.

## Financial schema-v2 wrapper

processing.repair_financial wraps the preserved v1 transform/trace. It copies original
hours/estimated labor/legacy results, preserves raw money, and assigns reported costs
only for the confirmed equal-cell summary layout. A separate monthly CSV uses each
source summary once and exposes incomplete/difference states without allocation.
FinancialOutputStore stages the companion before SQLite selection and verifies the
main-hash-bound summary on current reads; failed stages leave the old selection.
No SQLite schema migration, cleaner rule change or approved publisher is introduced.
See repair_financial_v2.md for exact contracts and unresolved grouping evidence.
