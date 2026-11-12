# Historical backfill — PR 1: flexible discovery and read-only inventory


## Historical Power BI datasets — 2026-11-12

Based on merged main eea5d01 (PR #23). Historical Data → Power BI snapshot now
previews only current manifest-selected normalized candidates and creates four
deterministic local CandidateUnverified datasets with revision/source/output/summary
hashes, counts, warnings and a compatibility report. Missing/invalid slots block
generation; no older fallback, deduplication or dashboard filters are applied.
Corrections remain in the existing individually confirmed workflow.
See [snapshot workflow and Windows acceptance](historical_powerbi_dataset.md),
[ordered schemas](historical_dataset_columns.md) and
[PBIX metadata compatibility findings](historical_powerbi_compatibility.md).

No cleaning/schema-v2 changes, candidate selection mutation, authoritative approval,
Graph access, PBIX edit, production publishing or Power BI refresh. Actual owner
snapshot/import acceptance and model/finance decisions remain separate gates.
This section supersedes earlier statements that historical snapshot UI is deferred;
older sections retain their dated historical scope.


## Historical Batch Processing — current feature

Based on merged main fe5df23 (PR #22). Historical Data adds a reviewed, explicitly
confirmed plan and sequential creation of **local unapproved normalized candidates**.
Unchanged reports skip; corrections stay blocked with a route to existing individual
confirmation. Current revision/proposal/source guards prevent stale replacement.
Cancellation/restart recovery uses committed history and fresh intent, without
resuming old plans. Read-only preview remains unchanged. No approval, publishing,
Graph writes, Power BI refresh or historical snapshot assembly is enabled.
See [workflow, architecture and isolated Windows acceptance](historical_batch_processing.md).
Older sections below describe earlier scope and are superseded by this feature note.


## Historical batch preview — current milestone

`feature/historical-batch-preview` starts from merged main **f49b297** (PR #21).
Read-only range previews, per-month counts/date/exclusion/missing-value evidence,
schema-v2 financial warnings, cancellation with partial results and private local
diagnostic exports are implemented. Existing cleaners and write/approval/publication
semantics are unchanged. See [historical_batch_preview.md](historical_batch_preview.md)
for architecture limits, synthetic demonstration and exact Windows January–June
acceptance. Historical sections below retain the earlier branch history; their
then-current deferred preview status is superseded by this section.

Next: owner Windows range acceptance and independent financial baselines. Batch
processing, historical snapshot publication, authoritative reviewer roles, live
Graph authorization and production Power BI remain separate gates. No automatic
merge, business approval or production migration is part of this milestone.


## Timestamped HI-042b follow-up

feature/tma-timestamped-layout depends on legacy-tma-compatibility 32d36b6. The
existing strict filename matcher is unchanged. The owner-described numeric Excel
generation timestamp / exact title / blank separator / four headers / no footer
now has a separate adapter; only its generation timestamp's previous calendar
month may agree with the selected month. See tma_timestamped_layout.md. Historical
batch/snapshot UX remains outside this fix; source layout discovery never approves
workbook contents. No production or original raw files are changed.

## Legacy TMA follow-up (2026-11-04)

feature/legacy-tma-compatibility depends on this discovery branch at c425841;
main bd21499 still does not contain it at inspection. Its separate scoped fix
adds strict legacy filename discovery and genuine BIFF8 XLS candidate reading,
with optional Assigned To, existing period validation, source guards and unchanged
output schemas. See legacy_tma_compatibility.md for exact supported shape, null
semantics, dependency/cleaner-version implications and private May acceptance.
The actual May workbook was not attached or verified. Older PR-1 scope and test
counts below are historical; batch backfill and snapshot controls remain deferred.

This is the first scoped milestone from the historical-backfill request. It starts
from owner-merged main **bd21499** (PR #17, Microsoft 365 foundation). Approval UX
PR #16 and all previous foundations are already ancestors; no prerequisite changes
were duplicated. Git remote heads/merge history were inspected. GitHub API returned
HTTP 403 for open PR metadata; current open PR/reviewer/hosted-check status is unknown.
No PR is merged by this work.

## What this PR implements

- Explicit persistent raw-folder layout choice; no automatic detection or switching.
- Read-only historical range inventory in the desktop and CLI, using the existing
  local/synced provider. Up to 120 inclusive months; direct listings only, at most
  4096 entries per directory and 64 MiB per recognized source. No cleaner runs in
  historical discovery, no candidate database is opened or created.
- One row per requested month, including missing and unscanned months. Per-type
  status, problems, original paths, sizes, captured local identity/version and SHA-256.
- Employee problem explanations and an optional technical view. Exclusive private
  local JSON export outside the raw/synced folders; existing exports are not overwritten.
- For one month in the SharePoint layout, **Process Reports → Discover month**
  reuses the same inventory, passes only unambiguous available files to the existing
  preview/process APIs, and binds reads to the captured version/hash. Month
  confirmation, content validation, correction tokens and immutable candidates remain.
- Both layouts are exercised by real-window and installed executable smoke steps,
  including a fresh-process settings restore. Actual Windows results require CI
  or managed-PC execution; Linux success does not establish Windows packaging.

**Not implemented in this PR:** historical batch preview (row counts/exclusions,
missing-value and financial controls), selected multi-month processing, batch
correction review/stop/recovery UX, historical snapshot/reconciliation controls,
automatic snapshot assembly or migration of dashboard sources. A file marked
**Found** only passed filename/extension/local stable-read checks. Its schema and
reporting content have NOT been validated. Even a complete inventory is not approval.

Existing single-month cleaning/packets and explicit multi-month v2 snapshot and
reconciliation CLI remain available; this PR does not duplicate those tools or
claim the new historical inventory is a Power BI snapshot.

## Supported layouts and filenames

Settings → **Raw folder layout** offers:

1. **Standard month/report-type layout**: root / `YYYY-MM` / `repairs`,
   `service_orders`, `tma_work_orders`. Historical inventory accepts an arbitrary
   basename inside its type folder, preserving previous routing flexibility;
   CSV is required for CompuClean; supported XLSX/BIFF8 XLS are routed to TMA
   preview. Existing Standard Discover month routing remains compatible.
2. **SharePoint year/month layout**: root / `YYYY` / `YYYY-MM (Label)` / three
   directly stored reports. Choose `01_Raw_Data` itself as the raw root.
   Numeric year/month and English label must agree. Known case-insensitive labels:
   Jan/January, Feb/February, Mar/March, Apr/April, May, Jun/June, Jul/July,
   Aug/August, Sep/Sept/September, Oct/October, Nov/November, Dec/December.
   Parent year must agree. A numeric-only month folder is not accepted in this
   layout; use Standard for the supported numeric/type layout. Other historical
   conventions need examples and an explicitly tested matcher, not guessing.

Shared-folder matches are anchored, case-insensitive stems:

- `CompuClean Repair Report.csv`
- `CompuClean Service Orders List.csv`
- `Work Orders January 2026.xlsx` (or genuine `.xls`, documented month label matching folder period)
- `CU_Repair_WO_History_-_Previous_Month_(HI-042b)<1–30 digits>.xls` (period must be verified from workbook contents)

Spaces, underscores and hyphens between filename words are interchangeable.
Copy/revision suffixes, arbitrary `.csv`/`.xlsx` names and unknown month labels
are not guessed. Patterns are fixed in `historical.filename_match`; no user regex
or traversal expression is accepted. Source schema validation still occurs only
in the existing preview engine. The actual basename is preserved in provenance.

Two matching files, even byte-identical, are **Ambiguous**. Two agreeing folder
aliases (`2026-01 (Jan)` and `2026-01 (January)`) are also ambiguous; no choice is
made. A valid file alongside an unrecognized file produces a month-level issue.
The strict shared-folder monthly bridge blocks selection when month-level issues
remain. Resolve the intended current export with the data owner; the app will not
move, rename, merge or delete originals. Nested history/archive folders are never
recursed. Do not configure a broad dashboard/library root instead of the raw root.

Temporary/hidden/Office-lock and `.tmp`, `.part`, `.partial`, `.crdownload`,
`.download` files are not ingested and are visible as issues. Unsupported matched
formats block the report. Supported BIFF8 XLS now reaches the same strict TMA
preview checks; malformed, encrypted or renamed files remain invalid. Changing
an extension does not convert a workbook. Links/junctions encountered
in direct directory inventories fail closed. Malformed year/month entries are
reported for every inspected month in that year, so mislabeled history is visible;
this conservative behavior may require resolving an unrelated bad folder label.

## Settings compatibility

The existing strict settings v1/v2 and legacy three-folder imports still load.
An absent `preferences.folder_layout` defaults to `standard`. New writes keep
settings version 2 and add the validated optional enum (`standard` or
`sharepoint_year_month`); folders, month, guidance and output-format preferences
are preserved. Old application builds may reject this new optional field; retain
an earlier settings backup and use a separate `--settings-file` when evaluating
this feature. No SQLite or cleaning schema migration occurs.

Save Settings applies the layout and raw root and invalidates any historical
inventory. Editing the range also invalidates its export. Navigation alone retains
an inventory for inspection. Inventories/confirmation are not restored as authority
at restart. The reporting month remains the existing remembered preference; the
historical range is session-only and independent of that month selector.

## Windows / VS Code acceptance

Open the **cloned repository folder** in VS Code, not the downloaded executable
ZIP directory. From that folder's PowerShell terminal:

```powershell
git fetch origin
git switch --track origin/feature/historical-folder-discovery
python -m uv sync --frozen --all-extras
python -m uv run --frozen python examples/create_historical_inventory.py --output data/historical-preview
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app --settings-file data/historical-preview/settings.toml
```

Use `git switch feature/historical-folder-discovery` if it already exists, then
`git pull --ff-only`. Close running copies of the application before uv updates its
Windows launcher if Windows reports Access denied. Do not delete the old candidate
history. The generator refuses an existing destination; use a fresh name to repeat.

1. In Settings select `data/historical-preview/sharepoint` as raw root. Select
   SharePoint year/month layout, a separate trusted local candidate folder, and a
   separate reserved approved folder. Confirm local storage; Check and Save.
2. Open Historical Data. Enter Start `2025-12`, End `2026-03`. Discover. Only
   January 2026 should be Complete inventory; December, February and March missing.
   It must not create cleaned CSVs or SQLite as part of historical discovery.
3. Inspect Problems & files, hashes and Technical details. Export Discovery Report
   as a **new** `.json` file on trusted local storage outside raw and sync folders.
   Reusing an existing export must fail without modifying it.
4. In the synthetic tree only, copy a repair under the alternate recognized name
   `CompuClean_Repair_Report.csv`. Discover again: Repairs must be Ambiguous.
   Remove only the disposable synthetic duplicate to restore this test fixture.
   Try a mismatched folder label, invalid/renamed XLS, missing report or partial download
   in a disposable copy. Inspect reasons; no source should be changed by the app.
5. Return to Process Reports, select January 2026, Discover month, confirm the
   month and Preview. Supported bundled sample layouts should preview; no cleaned
   candidates yet. Process, repeat to confirm skips, and exercise an explicitly
   reviewed correction using disposable synthetic inputs. These older bundled
   samples do not establish full financial-summary reconciliation.
6. Change a selected source after discovery: preview must reject its changed
   version/hash. Rediscover after the export is stable. Content dates/unknown
   columns must still be rejected by the real engine, regardless of folder names.
7. Switch Settings to `data/historical-preview/standard` and Standard layout.
   Repeat inventory/monthly preview. Restart: layout, root and reporting month
   should restore; month confirmation must remain unchecked. Approval, Publish
   and desktop Graph sign-in must remain disabled.

For an inventory without the GUI (also works without the desktop extra):

```powershell
python -m uv run --frozen python -m equipment_data_manager.historical --root data/historical-preview/sharepoint --layout sharepoint_year_month --start 2025-12 --end 2026-03 --output data/historical-inventory.json
```

The JSON includes private paths/identities and must stay private. It is not a
source-of-truth manifest, an approved snapshot or an import format. Inventory is
point-in-time evidence; changed bytes require rediscovery and fresh preview.

## Availability and interruption

All recognized reads use `LocalFolderStorage` and its stable read guard. Known
Windows offline/recall attributes fail before opening bytes; folder placeholders
also fail before enumeration. Readability does not establish latest remote ETag,
server currency or OneDrive synchronization health. The app does not hydrate,
rename or finish incomplete downloads. Use the approved sync-client/IT procedure.
Files changed between discovery and preview or preview and processing are rejected.
Adversarial filesystem races and every third-party sync client cannot be proven
absent; use authorized roots and trusted local application storage.

Discovery can stop between file reads. The current read finishes; a partially
scanned month is flagged and all later months remain Not scanned. This creates
no candidate revisions and does not erase prior processing results. Discovery
report export is exclusive and fsynced; a hard process/power interruption can leave
an incomplete report file. Reports are never used as executable processing state;
choose a fresh export path and rediscover. Normal export failure removes its own
incomplete file, never a preexisting file.

## Dependent PR plan

**PR 2 — batch preview and controlled backfill**, after PR 1 review:
explicit month selection + confirmation, stable captured sources through existing
engine, per-month counts/exclusions/nulls/financial warnings, unsupported historical
schema evidence, correction acknowledgements bound to the exact source/revision,
stop after current file, independent failure results and safe repeat execution.
No new cleaning/business interpretation or unattended whole-history process.

**PR 3 — historical candidate snapshot/reconciliation**, after PR 2 review:
reuse complete monthly v2 packets and existing explicit `powerbi_pilot.assemble`
plus `powerbi_readiness` controls. Include four datasets, exact revisions and hashes,
multi-year selection and missing-month policy. Require complete months by default;
any incomplete-month inclusion needs an explicit documented policy, never silent
omission. Preserve nullable money/text IDs/monthly financial grain and estimated
versus reported versus legacy meanings. CandidateUnverified only.

Existing manual packet/snapshot tools already accept explicit nonoverlapping
months across years. Use `powerbi_real_data_readiness.md`,
`powerbi_backup_migration.md`, `powerbi_compatibility.md` and
`repair_financial_v2.md`; do not recursively ingest `versions/` or packet history.
No new inventory matrix, ID cross-system joining, building/room relationships,
DAX or dashboard migration is implemented here. Model inventory, keys,
classifications, capacity and independent historical baselines still need review.
Only test in a backup PBIX; production PBIX and SharePoint remain unchanged.

## Validation evidence and gates

See `testing.md` for exact local results. Windows/Linux matrix and actual Windows
PyInstaller build/component/GUI/restart smoke checks remain configured, now also
scheduled for this branch's pushes. Hosted results are not inferred from config.
Manual real historical-data acceptance must be initiated by the user on their
IT-authorized Windows PC; no private report or live authentication was used here.
