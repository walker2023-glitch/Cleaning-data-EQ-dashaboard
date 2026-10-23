# Power Query folder ingestion — review example, production blocked

`powerquery/fnReadMonthlyFolder.pq` is a complete M function example for schema v1.
`powerquery_contract.py` is an independently callable offline Python reference
validator. Automated tests feed real-engine **synthetic** outputs into that
validator and check the M file's ordered column/type specifications against the
exporter. They test distinct-month combination, duplicate-month rejection, text
identifiers, nullable prices, incompatible schemas, bad dates/numbers/status and
nonrecursive history exclusion. They do **not** execute a Power BI mashup engine
or establish Power BI refresh/financial accuracy. A real M/PBIX pilot is still a gate.

## Multi-month pilot

See [powerbi_pilot.md](powerbi_pilot.md) for a runnable two-month synthetic
trial, explicit packet assembly/hash checks, complete-month M examples,
reconciliation CSVs and exact backup-PBIX instructions. The optional fourth
`ExpectedMonths` argument adds missing/unexpected-month detection; the prior
three-argument API retains its behavior. Actual M/model execution is still pending.
`fnMonthlyControlTotals.pq` and `PilotControlTotals.pq` expose comparison sums and
missing counts without replacing existing DAX or cleaning calculations.

## Try only in a separate review model

1. Process a synthetic month and **Export review packet** using the monthly guide.
   Use that exact immutable packet/report subfolder, not review_packets as a whole,
   powerbi_candidates/versions, raw folders or any production ingestion path.
2. Run the offline check from VS Code, replacing PATH with that report subfolder:

   ```powershell
   python -m uv run --frozen python -m equipment_data_manager.powerquery_contract "PATH" service_orders --candidate-review
   ```

   Without --candidate-review the current candidate files are rejected. The flag
   permits private review only, not approval. Validate packet.json's hashes/revision
   selection against the intended current candidates as part of the private review.
3. Open a new review PBIX or a backup **copy**. Create a blank query in Advanced
   Editor, paste the M file, and name it `fnReadMonthlyFolder`. Disable its load.
4. Create separate staging queries for the three contracts:

   ```powerquery
   // Candidate-only sandbox. Substitute the exact packet's report subfolder.
   = fnReadMonthlyFolder(ReviewRepairFolder, "repairs", true)
   = fnReadMonthlyFolder(ReviewServiceFolder, "service_orders", true)
   = fnReadMonthlyFolder(ReviewTmaFolder, "tma_work_orders", true)
   ```

   Set the three folder parameters explicitly to authorized **candidate review**
   paths in this model. Do not repoint a production query or reuse production
   credentials to try this example. Omit/remove automatic Changed Type steps;
   the function already applies explicit types. Check UTF-8 text and IDs in
   Power Query itself, not Excel's automatic numeric inference.
5. For a synthetic multi-month folder trial, assemble a separate direct report
   folder containing exactly one deliberately selected current candidate per month
   of that type from the reviewed packets. Do not scan/copy every packet revision.
   A second CSV with an existing month fails even if it is identical. Corrections
   require replacing the selected snapshot **in a new review folder**, not adding
   another copy of the month. The app's packet exporter is monthly, not a rolling
   multi-month production snapshot publisher.
6. Review schema, counts, warnings, totals, nulls/zeros, relationships and DAX with
   `validation_checklist.md`. A successful import does not approve costs or source
   contracts. Do not publish or refresh the existing production model from candidates.

## Enforced contract and limits

Folder.Contents reads direct children only. Direct CSVs must have the exact ordered
schema (no added/unnamed columns), nonempty rows, one ReportMonth per CSV, matching
ReportType/ExportVersion/SchemaVersion, finite numbers, integer counts and ISO
dates. Metadata/identifiers remain text; blank money/date/count cells become null.
Rows retain source identifiers and legitimate repeat transactions; RecordId is
unique per retained occurrence/source revision, not a shared business join key.
Duplicate months or RecordIds across files reject the combine. Default M mode
requires ValidationStatus=Approved; explicit review mode requires
CandidateUnverified and never treats it as approved. A mixture fails.

The current application NEVER emits Approved. Editing this column is not an
approval mechanism. The M example checks structure/status, not reviewer identity,
signatures or packet hashes. Future production use requires an independently
approved snapshot publisher and restricted approved-only folder access; see
`powerbi_output_design.md`. Default rejection alone does not implement that system.
Do not connect production Power BI to the reserved approved folder yet.

Numeric types use nullable number (floating decimal) and Int64 counts, not an
unapproved currency rounding conversion. Python reference tests use Decimal;
M/Power BI number precision differs. Model/finance owners must approve precision,
rounding, locale and null behavior with trusted amounts. Fix decimal choice only
through reviewed contract/model changes. No cleaning calculation changes here.
The example is local-folder ingestion, not a SharePoint connector or gateway setup.
It does not verify OneDrive synchronization or protect against files changing
mid-refresh; use completed immutable snapshots in a trusted folder.

## Future production migration, after separate approval

Implement authenticated approval/audit and complete immutable approved snapshots
first. A future publisher must choose only one current approved CSV per type/month
and stage a complete multi-month set plus approval/hash manifest. Conditionally
select one snapshot pointer; failed uploads remain unselected. Read that pointer
once, then pass each exact snapshot/report folder to the function with review mode
false. Archive snapshots remain outside that folder. Do not refresh across two
pointer versions or recursively ingest history. The reserved approved path and
this example do not implement the publisher or its pointer resolver.

Back up the PBIX and work in a copy. Preserve existing table identities/names
(`Compuclean list`, `Service_Orders`, existing work-order tables); initially load
new tables only as comparison staging queries. Map approved schema columns to the
existing model contract deliberately. After comparison, change existing tables'
source/query steps rather than deleting/recreating tables. Preserve relationship
keys and text types, Building_Dim/calendar joins, cardinality/filter direction,
DAX references, date tables, sort columns and row-level security. Do not use the
source-revision RecordId to replace established business relationships.

Compare monthly/grand counts, repair hours/costs, blank-vs-zero measures, existing
DAX results, filters/slicers/maps and every page. Keep rollback copy and prior
snapshot. Model owner signs off before a separately authorized test-workspace
publish; IT/model owner establish approved refresh credentials/gateway/ownership.
No PBIX, DAX, relationship, workspace or refresh is changed by this repository work.
