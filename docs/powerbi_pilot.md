# Power BI integration pilot — local candidates only

> **Superseded for current repair finances:** recommended output now uses repair
> schema v2. See [repair_financial_v2.md](repair_financial_v2.md) for confirmed
> total-cost mapping, separate monthly summaries, evidence limits and migration.
> Schema-v1 details below remain compatibility/history documentation; source-reported
> totals must not be interpreted as parts or have estimated labor added to them.


This pilot assembles an explicit multi-month selection from monthly review packets.
It never selects files by recursively scanning candidate history, marks data
approved, connects to Power BI, or changes cleaning calculations. Work on a trusted
local disk with one operator. Folder access/OneDrive synchronization is not verified.
Known network/synced destinations and linked paths are rejected using existing
local-folder checks; those checks cannot prove absence of every sync client. Obtain
IT confirmation for custom locations. The Python checks are offline reference checks; actual M execution, DAX and visuals
must be evaluated in Power BI Desktop by the model owner.

## Current v2 real-data procedure

Follow [powerbi_real_data_readiness.md](powerbi_real_data_readiness.md) for current
January/February assembly, independent expectations, original-file checks, all four
tables and backup-PBIX acceptance. The complete-example flag generates a successful
fictional v2 assessment; the older examples below retain comparison/missing-data behavior.

## 1. Generate a reproducible synthetic trial

Close the desktop before updating dependencies. In VS Code open the **cloned Git
repository**, not the extracted Windows executable ZIP. In its PowerShell terminal:

```powershell
cd C:\path\to\Cleaning-data-EQ-dashaboard
git fetch origin
git switch feature/powerbi-integration-pilot
python -m uv sync --frozen --all-extras
python -m uv run --frozen python examples/create_powerbi_pilot.py --output data/powerbi-pilot
python -m uv run --frozen python -m equipment_data_manager.powerbi_pilot check data/powerbi-pilot/pilot/snapshot
```

If the branch already exists, update with `git pull --ff-only`. The generator
refuses an existing output directory; use a new name for another trial. It creates
two raw synthetic records per report type in January and February 2026, processes
all six inputs through the real normalized engine, and exports monthly packets.
The approved destination is not created. Everything under data/ is ignored by Git.

```text
powerbi-pilot/
  raw/YYYY-MM/type/synthetic.csv or .xlsx     original synthetic inputs
  candidates/powerbi_candidates/versions/    history — NEVER ingest
  candidates/review_packets/                 monthly candidates — NEVER ingest root
  pilot/snapshot/
    snapshot.json                           selected month/type, revision, hash, rows, warnings
    tables/repairs/*.csv                     exactly January and February
    tables/service_orders/*.csv              exactly January and February
    tables/tma_work_orders/*.csv              exactly January and February
  synthetic-baselines.csv                    INVENTED source/dashboard observations
  reconciliation.csv                         comparison, not approval
```

Each imported table should have **4 rows**, each month **2**. IDs include `000438`,
`000439`, and TMA `000128`/`000129`. Both months' repair hours sum to 4 each. January
repair parts/labor/estimated totals are 20/50/70; synthetic source totals are
30/40/70. February has a missing parts value: known PartsCost sum 10 with one null,
EstimatedTotalCost known sum 35 with one null; legacy parts/estimated totals remain
10/60. All service prices are null. These values deliberately expose disagreement,
partial sums and null handling; they are not actual departmental totals or evidence
of the production discrepancy's cause. Repeated report summaries count once.

## 2. Assemble approved-to-handle local examples instead

“Approved example” means authorized for private testing, not production-approved
output. Process each selected month in Power BI candidate mode and export its
complete monthly review packet using the application. Choose one packet per month
explicitly; review its correction selection, warnings and source fingerprints.
Then, substituting the actual local packet paths and desired months:

```powershell
python -m uv run --frozen python -m equipment_data_manager.powerbi_pilot assemble --packet "C:\local-review\packet-january" --packet "C:\local-review\packet-february" --month 2026-01 --month 2026-02 --output data/private-pilot-01
python -m uv run --frozen python -m equipment_data_manager.powerbi_pilot check data/private-pilot-01/snapshot
python -m uv run --frozen python -m equipment_data_manager.powerbi_pilot baseline-template data/private-pilot-01/snapshot --output data/private-baselines.csv
```

Requires one nonempty supported file per type/month; genuine zero-activity months
need a separately agreed completeness contract. A packet's exact paths, status,
period, hash, schema and row counts are checked before staging. Missing/duplicate
months, missing types, changed bytes, links, schema mismatches and failed staging
reject the snapshot. A fresh destination is required; prior snapshots remain.
Packet hashes demonstrate consistency, not authenticated approval. Explicit packet
selection does not prove it is still the manifest's latest current revision: verify
that at selection time. A packet remains pinned even if a later correction exists.

For corrections, use the desktop's existing review/token mechanism, export the
corrected packet, then assemble a **new** pilot destination using one chosen packet
per month. Point all three pilot queries at that new snapshot. Never add a second
CSV for an existing month or copy the versions tree. Keep old snapshots outside
the selected ingestion root. Do not edit either snapshot after selection. The
checker detects extra files/subfolders as well as missing or changed files.

## 3. Import into a separate PBIX

1. Preserve the original PBIX and any local source backups. Create an explicitly
   named local review copy with **Save As** (or begin with a blank PBIX for synthetic
   data). Keep production closed. Do not publish, schedule refresh or overwrite it.
   Inspect existing queries: Refresh All in a copy may still contact production
   sources. For a fully offline synthetic trial, start a blank PBIX. For comparisons,
   use authorized local baseline exports or explicitly isolate existing live queries;
   do not infer that Save As changes their connections.
2. Record existing table names/columns/types, DAX expressions, relationships,
   calendar and Building_Dim joins, sort-by columns, RLS and model properties before
   considering any source replacement. See powerbi_compatibility.md. No replacement
   of existing queries is needed for this pilot.
3. In Power Query create a **Text** parameter `PilotSnapshot` containing the full
   local path to the exact `pilot/snapshot` directory. Never use the parent pilot,
   candidates, versions or review_packets directory.
4. Create a blank query, paste powerquery/fnReadMonthlyFolder.pq into Advanced Editor,
   and name it `fnReadMonthlyFolder`. It is a function, not a loaded table. Create
   three queries using the full contents of PilotRepairs.pq, PilotServiceOrders.pq,
   PilotTmaWorkOrders.pq with those exact names. They explicitly permit candidates
   in this review model and require both selected months. For other periods, edit
   the expected-month lists **in all three** queries to exactly match snapshot.json.
5. Add fnMonthlyControlTotals.pq as `fnMonthlyControlTotals`, then
   PilotControlTotals.pq as `PilotControlTotals`. This comparison table keeps missing
   counts beside known sums. Do not add automatic Changed Type steps to imported
   transaction queries. The function already types IDs as text, dates explicitly
   as ISO dates, hours as nullable numbers and counts as whole numbers. Never
   replace missing money with zero or add Legacy fields to their normalized copies.
6. Initially keep pilot tables disconnected from existing tables/relationships.
   Inspect Power Query results and load only the pilot tables. Verify leading zeros,
   UTF-8, dates, counts, hours, nulls and report months. Match the synthetic controls
   above and reconciliation.csv. Test missing files, duplicate months and schema
   errors on a **disposable copy** of the snapshot; expect refresh failure, then
   restore the intact snapshot. Never test by damaging the original candidate store.
7. In the backup model, create a separate comparison page. Review pilot controls
   against authorized source totals and exported existing measures for **the same
   month/filter scope**. Existing measures are not automatically redirected by adding
   pilot tables; do not change their DAX to make the comparison match. Use the
   mapping review and reconciliation instructions below. Preserve filter context,
   blank behavior, rounding and date-basis differences as explicit findings.
8. Save only the local pilot PBIX. Record Desktop version, snapshot file hashes,
   query errors, monthly/grand totals, refresh duration and visuals checked. Model,
   data and finance owners must resolve differences before a separately authorized
   migration/test workspace. No production upload or Service refresh is part of this.

The M function reads direct CSVs only, rejects duplicate months/record identities,
requires exact ordered schemas and metadata/status, and applies explicit nullable
numeric/date types. The fourth argument checks missing/unexpected months. Its
backward-compatible three-argument form cannot detect an absent expected month;
use the provided four-argument pilot examples. Power Query does not authenticate
snapshot.json or verify SHA-256 during refresh; run `check` immediately before
refresh and keep the trusted snapshot unchanged throughout. A successful M parse
or offline test does not prove actual mashup-engine behavior or model compatibility.

## 4. Reconcile real observations without inventing results

Fill the generated private-baselines.csv locally. Preserve its exact header:

```text
report_type,period,metric,source_total,powerbi_total,powerbi_measure,tolerance,comparable,evidence
```

One row per type/month/metric. Blank totals mean **unknown**, not zero. Use plain
finite decimal numbers; tolerances must be explicit and nonnegative (template 0).
`powerbi_measure` records the actual existing measure/table and filter scope, not a
guessed name. `evidence` identifies the authorized source report/summary and baseline
export/date/filter context. The tool cannot verify a manually entered observation's
provenance. Record source hours only if the report actually supplies comparable
person-hours; do not derive an “independent baseline” using the cleaner's formula.

Set `comparable=true` only after a reviewer confirms row grain, exclusions,
reporting-date basis, units, scope, financial meaning and precision. This setting
permits arithmetic comparison; it is not approval and never modifies output status.
Use false for unresolved cost semantics even if the numbers happen to agree.

```powershell
python -m uv run --frozen python -m equipment_data_manager.powerbi_pilot reconcile data/private-pilot-01/snapshot --baseline data/private-baselines.csv --output data/private-reconciliation-01.csv
```

The command refuses an existing report or a report inside the tables tree. It emits
all expected metric rows even if a baseline observation is absent. Metrics cover
transaction counts, repair counts, hours, parts/labor/estimated costs, legacy
comparison costs, service price and TMA count. Each row shows known cleaned sum,
missing count, source/Power BI observations, cleaned-minus-baseline deltas, tolerance,
evidence and separate comparison statuses. Deltas for incomplete totals stay blank.
Statuses include `not_supplied`, `incomplete_cleaned_values`,
`business_mapping_unconfirmed`, `difference`, and `arithmetic_match`. No status is
approval. Malformed/duplicate/unknown observations fail instead of being ignored.

Source raw counts can exceed retained rows because of intentional exclusions.
A count difference is a finding to trace through the existing diagnostics, not a
reason to remove rules. Record accepted/excluded counts and first-match reasons
from Preview beside the comparison report. Compare each month, then matched-period
grand totals; do not compare a two-month pilot with a full-history dashboard total.
For duplicate/corrected-file review retain the selected revision/hash and previous
reconciliation privately; no business-event matching across revisions is invented.

## Remaining gates

Actual PBIX/M evaluation and existing measures have not been supplied/run here.
Trusted raw/cleaned pairs and baselines, financial semantics, date/null/precision
approval, zero-activity policy, relationships/DAX/visual regression and managed-PC
review remain open. See repair_cost_reconciliation.md and inputs_needed.md. No
production publisher, authenticated approvals, SharePoint access, sync verification
or dashboard change is implemented by this pilot.
