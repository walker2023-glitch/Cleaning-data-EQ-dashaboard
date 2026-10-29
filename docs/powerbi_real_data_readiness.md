# Milestone A — schema-v2 real-data Power BI review

## Integration update — 2026-10-29

The owner now reports successful real January/February **schema-v2** reconciliation,
Desktop imports and monthly visuals. That supersedes the older pending/previous-
schema descriptions below, but does not establish production approval or independent
agent-run Desktop testing. Repeat acceptance privately at the integration commit
using **integration/stable-baseline** in section 1. Preserve the supplied monthly
and combined targets in your local expectations grid, not in repository fixtures.
The four datasets, v2 contract, legacy compatibility and calculation rules are
unchanged. See integration_baseline.md for current branch and remaining checks.
Below is the original Milestone A procedure/evidence record; its older PR-state
and pending-test statements are historical.

The application can assemble explicit monthly packets into a separate, candidate-only
snapshot with four report folders. This milestone adds an assessment of monthly and
combined controls, independent private expectations, optional original-file hash
verification, shared Power Query periods, and a month-level comparison query.
It does not change cleaners, financial schema, the GUI, approvals or production.

## Evidence and current status

| Evidence | Who performed it | Meaning / remaining limit |
|---|---|---|
| Prior January CSV read-only reconciliation | Development environment, PR #11 | Observed input reconciled; original bytes unchanged |
| January and February financial-v2 reconciliation | Owner reported, 2026-10-27 | Observed files' arithmetic agrees with their summaries; not business/production approval |
| Synthetic multi-month Power BI Desktop import and visuals | Owner reported, 2026-10-27 | Successful **previous repair schema** pilot; does not prove v2 Desktop/model behavior |
| Current snapshot/assessment/M contract regressions | Automated synthetic tests | Offline structure, integrity and arithmetic only; not execution of the Power BI mashup engine |
| Real schema-v2 Power BI Desktop/dashboard trial | Still required locally | Follow this procedure and retain the completed acceptance record privately |

The environment does not contain all six real January/February inputs or both
exported packets. The new tooling is tested with invented records/amounts. No
private reports, financial expectations or actual source fingerprints are in Git.
No need to resend already-tested files for this milestone: use your local packets.
Nonzero unequal repair field/subtotal meanings remain a future-format question;
existing conservative v2 behavior is unchanged.

## 1. Start from the right project

Close Equipment Data Manager before syncing. Open the cloned Git repository in
VS Code, **not the extracted executable ZIP**. In PowerShell:

```powershell
cd C:\path\to\Cleaning-data-EQ-dashaboard
git fetch origin
git switch feature/powerbi-real-data-readiness
python -m uv sync --frozen --all-extras
```

If the branch already exists, update with `git pull --ff-only`. Only PR #1 is merged
at review; #2–#11 remain open in their dependency chain. This branch is based on
PR #11's bffd53f. Do not check out main expecting these features or merge the stack
automatically. SQLite and candidate history must stay on a trusted local disk.

## 2. Try the complete synthetic walkthrough first

```powershell
python -m uv run --frozen python examples/create_powerbi_pilot.py --repair-financial-v2 --complete-financial-example --output data/milestone-a-demo
```

The destination must be new. This creates six raw invented reports, immutable
candidates, two monthly review packets, a snapshot, independent invented expectations,
an explicit raw source index and readiness-report/. Every report has two records
per month; each imported transaction table has four rows. Monthly synthetic repair
totals are 20, reported parts 5 and labor 15; combined totals 40/10/30. These are
fictional demonstration amounts, not the departmental expectations in your request.
Leading-zero IDs and null service prices remain present. Do not copy these baselines
into the real-data trial. Without the complete-example flag the older v2 example
intentionally contains a missing February repair amount and needs review.

To repeat the assessment, writing another new private report folder:

```powershell
python -m uv run --frozen python -m equipment_data_manager.powerbi_readiness assess data/milestone-a-demo/pilot/snapshot --month 2026-01 --month 2026-02 --expectations data/milestone-a-demo/readiness-expectations.csv --sources data/milestone-a-demo/source-index.csv --output data/milestone-a-demo/recheck
```

## 3. Export the real selected monthly packets

In the desktop choose recommended **Power BI CSV candidate**, discover/select the
three reports for January, confirm the month, preview, process and review warnings.
An existing v1/current correction requires normal explicit confirmation. Export
January's review packet. Repeat for February. Keep the exact packet paths returned
by the application. Confirm they select the intended revisions and source hashes;
a packet remains pinned if a later correction is processed.

Each packet needs v2 repairs + the hash-bound repair financial summary, and service/
TMA candidates (their schemas remain v1). All four CSVs must be present, consistent
and unapproved. Do not add inventory to this three-report completeness requirement.
Do not fabricate a missing/zero-activity report or modify a packet to pass a check.

## 4. Assemble one explicit two-month snapshot

Substitute your actual two packet directories. Paths below are placeholders, not
organizational settings:

```powershell
python -m uv run --frozen python -m equipment_data_manager.powerbi_pilot assemble --require-repair-v2 --packet "C:\local-review\january-packet" --packet "C:\local-review\february-packet" --month 2026-01 --month 2026-02 --output data/private-real-pilot-01
python -m uv run --frozen python -m equipment_data_manager.powerbi_pilot check data/private-real-pilot-01/snapshot
```

`--require-repair-v2` rejects legacy repair packets before writing. The general
assembler retains v1 compatibility when the flag is omitted; the readiness tool
always requires repair v2. Expected tree:

```text
private-real-pilot-01/snapshot/
  snapshot.json
  tables/
    repairs/                   exactly two selected v2 monthly CSVs
    repair_financial_summary/  exactly two one-row v2 summaries
    service_orders/            exactly two selected v1 monthly CSVs
    tma_work_orders/           exactly two selected v1 monthly CSVs
```

Hashes, exact file sets, distinct/required months, schemas, record identities and
main-to-summary references are checked. The same bytes that pass hash checks are
parsed, once per artifact; a second unverified file read is not used to assemble
controls. Historical versions, all review packets, and raw reports are outside
the ingestion root. A changed/missing file or mixed repair schema rejects the set.
Nothing is copied into the reserved approved location.

For a correction, use existing engine confirmation, export a new packet, choose
one packet per month and assemble a **new destination**. Preserve the old snapshot
and assessment. Never add a second CSV for the same month or edit files/manifests.
The snapshot's hashes show local consistency, not authenticated approval. Keep a
single operator and freeze the selected snapshot before/during Desktop refresh.

## 5. Supply independent expectations and original files privately

Generate the complete monthly + ALL comparison grid outside the snapshot:

```powershell
python -m uv run --frozen python -m equipment_data_manager.powerbi_readiness template data/private-real-pilot-01/snapshot --month 2026-01 --month 2026-02 --output data/private-real-expectations.csv
```

The exact columns are `period,report_type,metric,expected,tolerance,evidence`.
Fill the blank expected values using your original source reports/confirmed
January/February checklist. Required controls cover repair counts, reported repair
totals, missing repair costs, single monthly summary counts/parts/labor/totals,
service counts and TMA counts. ALL means exactly the selected periods, not all
history. Keep your supplied departmental amounts in this private CSV, not GitHub.

Use independently checked accepted counts and documented exclusions/date basis.
Service/TMA counts were not supplied as new verified baselines in this request;
read them from the appropriate original reports and retained-record diagnostics.
Do not use synthetic report_samples counts or copy observed cleaned sums as an
independent source baseline. Monthly reported parts/labor belong to the single
monthly summary, not each transaction. Fill zero only for a confirmed zero, never
as a substitute for unknown. Use finite plain decimals, nonnegative explicit
tolerances (default 0), and evidence references naming the source/reviewer/date/
filter scope. A tolerance/evidence entry is not an approval record.

Create data/private-real-sources.csv with this exact header and six explicitly
selected paths, using the actual names on your computer:

```csv
report_type,period,path
repairs,2026-01,raw/2026-01/repairs.csv
service_orders,2026-01,raw/2026-01/services.csv
tma_work_orders,2026-01,raw/2026-01/work-orders.xlsx
repairs,2026-02,raw/2026-02/repairs.csv
service_orders,2026-02,raw/2026-02/services.csv
tma_work_orders,2026-02,raw/2026-02/work-orders.xlsx
```

Relative paths resolve against the index CSV's folder; absolute Windows paths also
work. This index is private configuration, not a rename/move instruction. Point
to the exact original bytes for the chosen revisions. No source file is modified.
Readable synced files can be indexed, but a successful read/hash check verifies
**local bytes only**, not OneDrive/SharePoint synchronization or remote currency.

## 6. Assess before Power BI refresh

```powershell
python -m uv run --frozen python -m equipment_data_manager.powerbi_readiness assess data/private-real-pilot-01/snapshot --month 2026-01 --month 2026-02 --expectations data/private-real-expectations.csv --sources data/private-real-sources.csv --output data/private-real-assessment-01
```

New report folder contents:

| File | Purpose |
|---|---|
| assessment.json | UTC timestamp, manifest hash, structural checks, financial/expectation/source-byte results; always unapproved and manual-test-required |
| controls.csv | Monthly and combined counts/known sums/null coverage, hours/estimates, missing and leading-zero identifier counts |
| comparisons.csv | Independent expected values, observed controls, missing counts, signed differences, tolerance/evidence and match/difference/not-supplied states |
| selected_files.csv | Eight selected artifacts with revisions, hashes, source provenance, versions and recomputed financial status |
| source_integrity.csv | All six source hashes and whether exact original local bytes were actually checked |

The assessment recomputes summary counts, known individual sums, missing amounts,
component/individual differences and status. A summary claiming a match incorrectly
is rejected even if its edited file hashes are mutually consistent. Real recorded
differences/incomplete costs remain valid review data and are flagged, not altered.
Partial sums never become complete totals in combined comparisons. Source provenance
must be constant per file; summary and repair selected revision/provenance must agree.

Exit 0: structure/financial arithmetic/all supplied expectations agree. Exit 2:
report saved, but missing expectations/financial values or differences need review.
Exit 1: invalid/unavailable inputs, structural/integrity inconsistency or write failure;
no successful assessment is claimed. Reports/templates refuse overwrite and cannot
be written inside the snapshot. Failed report writes remove only the newly created
report directory. Source and prior snapshot/report bytes remain untouched.

If --sources is omitted, original bytes are **not verified** even if the command
exits 0. The real-data checkpoint requires `source_bytes_verified`,
`reported_financials_reconcile`, and `expected_totals_match` all true, plus review of
identifier/date coverage and all remaining warnings. None is production approval.
Existing legacy-calculation warnings can coexist with matched **reported** totals:
legacy arithmetic and estimate policies remain separate comparisons.

## 7. Import the v2 queries into a separate Power BI file

For an offline first run use a **new blank local PBIX**. A backup of the production
PBIX retains its live connections; Save As does not make Refresh All offline.
Do not refresh production connections, publish, schedule Service refresh or overwrite
the existing file. Keep the snapshot unchanged and rerun assessment immediately
before testing. Disable automatic relationship detection for new pilot tables
(Current File → Data Load → Relationships) and inspect any already-created links.

In Transform Data → New Source → Blank Query → Advanced Editor, create the following
queries using the full matching .pq file. Use these exact query names. Functions/list
queries are helpers, not loaded fact tables:

| Query name | Repository file | Role |
|---|---|---|
| PilotSnapshot | Text parameter, your exact .../snapshot path | Local review root only |
| PilotMonths | powerquery/PilotMonths.pq | Shared explicit month list; January/February default |
| fnReadMonthlyFolderV2 | powerquery/fnReadMonthlyFolderV2.pq | Strict folder/schema/type/status/month function |
| PilotRepairsV2 | powerquery/PilotRepairsV2.pq | v2 repair transactions |
| PilotRepairFinancialSummary | powerquery/PilotRepairFinancialSummary.pq | One v2 row/month, separate grain |
| PilotServiceOrders | powerquery/PilotServiceOrdersV2.pq | Unchanged service v1 schema, shared periods |
| PilotTmaWorkOrders | powerquery/PilotTmaWorkOrdersV2.pq | Unchanged TMA v1 schema, shared periods |
| fnMonthlyControlTotalsV2 | powerquery/fnMonthlyControlTotalsV2.pq | Known sums and null controls |
| PilotControlTotalsV2 | powerquery/PilotControlTotalsV2.pq | Transaction control metrics |
| PilotReconciliationV2 | powerquery/PilotReconciliationV2.pq | Four-table comparison aggregated to month before joins |

Existing v1 service/TMA query/function files remain available for compatibility.
The V2-suffixed entry files above preserve their schemas but use the common period
list. Edit PilotMonths once, not four hardcoded lists. Do not add automatic Changed
Type steps; explicit UTF-8, ISO dates, text IDs, nullable numbers and Int64 counts are
already set. Inspect `000439`-style equipment IDs and missing values in Power Query,
not by opening CSVs with Excel inference. TMA WorkOrderId is not an equipment ID.

Load the four tables and two controls/comparison tables into the **test file**.
Keep them disconnected from the existing model initially. PilotReconciliationV2
shows monthly counts, source parts/labor/total, known individual repair totals,
missing costs, repair hours and the separate labor estimate. It joins monthly
aggregates, never expands monthly costs onto each repair. ReviewStatus must be
interpreted with null/coverage fields; an arithmetic match is candidate review only.
The function reads direct CSVs, never versions/ or archive trees. Power Query does
not verify snapshot SHA-256 or authenticate approvals; Python assessment plus an
unchanged trusted snapshot is required. M numeric comparisons are exact floating
number comparisons; small precision differences require recorded finance/model
review, not unapproved rounding or zero filling. Actual Desktop execution is still
a manual acceptance step; parser success does not prove it.

## 8. Backup-dashboard compatibility and acceptance record

See powerbi_backup_migration.md for preserving visuals/table identities/DAX,
building/calendar relationships and monthly hours/capacity measures. No production
query source or measure is automatically replaced. Actual measure names/expressions
are not available in this repository; dependency identification must use your
private model inventory, not guessed DAX names.

Keep a private acceptance record with tester/date, Power BI Desktop version,
commit/build, exact snapshot/manifest hash, eight selected file hashes, local raw
verification, expected-vs-observed monthly and combined metrics, null/ID/date checks,
query errors and screenshots. Confirm your provided January/February expected
financial figures and combined values using comparisons.csv. Check all four tables,
controls, existing visuals and unchanged hour/capacity behavior under the same
filters. Record v2 success only after actually running it. Keep failures/questions
visible; do not change exclusions, rate/default rules or costs to force a match.
