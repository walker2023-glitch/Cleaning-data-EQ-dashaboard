# Equipment Data Manager: local prototype

## Review & Approval — local foundation

After processing the month in Power BI CSV candidate mode, open **Review & Approval**
and select **Review candidate**. Inspect report counts, monthly reported costs,
missing values, warnings and exact revisions/hashes. Add a concise evidence note
or private reference, then choose **Request approval (local)**. The request is
recorded on this computer only: **it is not sent and is not business approval**.
All three current reports and repair schema v2 are required. Corrections or changed
original files require fresh review; refresh the view to see stale requests.

**Approve** and **Publish** stay disabled until independent reviewer authority and
a separately authorized publishing service exist. Publication history is unavailable;
use History for local candidate revisions. Guided Mode/F1 explains the controls.
Do not put credentials or unnecessary personal information in notes. Keep local
requests/history outside OneDrive/shared folders. Reading downloaded synced raw
files does not verify synchronization. See approval_publishing_foundation.md for
synthetic preview instructions; existing Power BI files and production folders are
unchanged.

## Consolidated prototype review

Obtain the build for **integration/stable-baseline** from a successful exact-commit
Windows check; older Downloads ZIPs do not update with source code. This integration
build still requires Windows/managed-PC acceptance. Extract the complete application
folder and double-click EquipmentDataManager.exe; employees do not need Python,
Git or VS Code. Developers use the Git clone instructions in development.md.

Use Settings for downloaded local/synced raw folders and trusted local candidate
history, then choose month → Discover → confirm month → Preview → Process → review
results → Export review packet. Corrected months require explicit review. Keep
historical revisions outside Power BI snapshots; never treat an arithmetic match
as business approval. Cloud synchronization is unverified and Graph is unavailable.
For January/February reconciliation use the private real-data SOP with a separate
PBIX; do not publish or refresh production. See integration_baseline.md.

This prototype processes supported local CompuClean CSVs and TMA XLSX candidates. It does not connect to Microsoft
or SharePoint. Cleaning accuracy against departmental data is **unverified**;
outputs are candidates for review, not production-validated reports.

## Launch without Python or a terminal

After the Windows prototype has been built and its automated checks pass, an
authorized maintainer can supply `EquipmentDataManager_v0.2.0_win64.zip` from the
PR's Windows build artifact. This is a review build, not an approved employee release.

1. Download the ZIP and extract **the entire folder** to an approved local location.
2. Open the extracted `EquipmentDataManager` folder and double-click
   `EquipmentDataManager.exe`. Keep the `_internal` folder beside the executable.
3. If organizational security policy blocks it, contact IT. Do not bypass device
   controls. Never run the executable from a SharePoint browser preview.

## Try the bundled synthetic sample first

1. Select **Repair Reports**, **Service Orders List** or **TMA Work Orders**.
2. Click **Load synthetic sample**. It contains invented values, not departmental data.
3. CompuClean samples use **September 2026**; TMA uses **January 2026**. Check **I confirmed this reporting month**.
4. Click **Preview Processing**. It creates no outputs or history entries. Inspect
   the filename, report type, month, proposed row counts and warnings. Select a
   table row to read its details; scroll the detail panel to read every warning.
5. Click **Process Reports**. The Results screen shows saved candidates, skipped
   files, corrections needing review and errors. Warnings do not mean production
   validation passed. The CompuClean samples deliberately include an excluded row.
6. Select a saved result and click **Open output folder** to find its CSV. For an
   earlier run use **History**, select the revision, then **Open selected revision folder**.

## Process a local report

Use **Select local raw files** for supported UTF-8 CompuClean CSV or TMA XLSX exports. Explicitly choose
the correct report type and month, confirm the month, then preview. Filenames do
not establish the reporting month. For TMA choose the reviewed title/header/footer
XLSX layout; its output is provisional. Legacy XLS and unverified layouts remain
unsupported. A repair financial-disagreement warning requires review of the source
and candidate totals; it does not authorize changing calculations or using the output.

Select one version per report type/month. If different files are proposed for the
same month, the application asks you to select one. Identical content is safely
skipped even if renamed. Use separate runs for different months. Individual file selection handles one type;
folder discovery can preview/process all three types together.
Changing the selection, month, type or output folder requires another preview.

Use **Choose output folder** to choose an approved local folder if the default
does not suit your workflow. The default Windows location is under your user
profile's Local AppData, `EquipmentDataManager/Candidates`. Each output folder
has its own processing history; use the same one for repeat runs.

## Correct a report safely

If the month already has different data, preview marks it **Potential correction**.
Select that row and click **Review correction**. Review current/proposed row counts
and proposed totals. Open the current revision folder to compare its CSV if needed.
Check the explicit approval box and click **Confirm correction**, then process.

Approval applies only to that preview. A changed input file or current revision
requires another preview/review. The original raw file and previous output remain
unchanged. History distinguishes current and previous **candidates**; it does not
claim that either was approved against a production baseline.

## Progress, errors and history

Processing runs in the background. Controls that would change the operation are
disabled until it finishes. **Stop after current file** lets the active file finish
safely, then stops remaining files. Closing while busy offers the same behavior.
Files already saved stay saved; stopping does not roll back the completed batch.

For errors, read the selected row's next step, fix the selection/export, then
preview again. A missing/changed previous output stops processing to protect the
recorded history; keep the folder intact and ask your maintainer for help.

History lists completed candidate revisions, including CLI-created M1 revisions.
Failed attempts remain in the current Results screen, not a permanent audit log.
Do not delete the manifest or recursively combine all version CSVs into Power BI:
the folder contains superseded revisions and may contain unselected artifacts
after interruption. No Power BI refresh or report modification occurs here.

## Before departmental use

Approved raw/cleaned example pairs, baseline totals, Windows managed-PC testing,
retention decisions and IT distribution approval remain required. SharePoint,
Microsoft sign-in and production publishing are deferred.

## Power BI CSV candidates

The **Output format** selector defaults to the recommended Power BI CSV candidate
(one header, standardized columns and dates). Legacy candidate remains available
for compatibility and comparison. Changing it
requires another month confirmation and preview. Use Legacy mode to save a
comparison/rollback CSV; the Power BI mode does not replace those artifacts.
Both modes retain the original cleaning/exclusion rules and process only local
supported reports. Power BI candidates have their own history under the base
folder's powerbi_candidates directory.

These exports are **unapproved candidates**. Financial field ambiguities, estimate
policies and trusted cleaned-output comparisons remain unresolved, so the application does not publish
approved monthly exports. Do not point a production Power BI query at either
candidate/history directory. SourceMaintenanceTag is a preserved description tag,
not an approved maintenance classification. No classifier is implemented.

Repair Power BI output now separates **ReportedTotalCost** from **EstimatedLaborCost**.
Never add estimated labor to the reported total. Original calculations remain in
Legacy columns for comparison. A separate monthly financial-summary CSV is saved
beside the repair CSV and included in review packets. Review its reconciliation
status and missing-cost count. Unequal or unconfirmed source fields stay blank;
a matching monthly total is not production approval. Previously processed months
need the normal correction review to select the new format. See
[the financial guide](repair_financial_v2.md) before changing a review Power BI query.

## Monthly folder checklist and review packets

Use **Settings** to select and save separate raw, local candidate and reserved
approved folders. Valid choices restore automatically. Select the month, then
**Discover month**. Read the missing-report checklist, confirm the
month and preview all discovered files. Resolve errors and review corrections,
then process and check every result. Click **Export review packet** only after the
intended current candidates for all three types have been saved. It exports current
manifest selections, so a failed newer attempt does not replace the last success.

Each new packet contains three report folders and packet.json with hashes/counts/
warnings. It is unapproved and does not belong in production Power BI. Exporting
never writes reports to the reserved approved folder. Files in nested history folders are
not discovered. Synchronization is unverified: unreadable or cloud-only files need
local availability checks through the approved sync client/IT procedure. Keep
candidate history on a local disk, single operator. Full steps and recovery limits:
[monthly workflow](monthly_workflow.md). Approval checks: [validation checklist](validation_checklist.md).

## First launch: Settings

Open **Settings** (shown automatically on a normal first launch). Use **Browse**
for Raw Data, Candidate Output and the reserved Approved Output folders. For
candidate storage you can choose **Use recommended local folder**. Keep candidate
history on this computer outside OneDrive, SharePoint and network sync; confirm
the local-storage checkbox. **Check Locations**, resolve the indicators, then
**Save Settings**. Missing folders require a separate creation confirmation. The
reserved approved folder may be created empty after confirmation; no report is
published there. Settings and preferred output format restore automatically next
launch. You do not need to edit TOML, run Python or open a terminal.

Raw reports belong in year-month/report-type subfolders. After setup: choose the
month, Discover Month, review missing reports, confirm, Preview Processing, resolve
errors/corrections, Process Reports, review Results and Export Review Packet when
eligible. Follow the separate departmental approval procedure. Saving folders does
not move originals/history; use the former base candidate folder to reuse history.
See the Settings guide supplied with the review build for detailed setup/recovery.

## Guided Mode and keyboard help

The left navigation has **Guided Mode** and **Brief / Detailed** (default Detailed).
Hover or focus a control for help, including disabled buttons. Press **F1** to read
its explanation in the Help page, or click **Explain this step**. The Help topic
selector and **Employee guide** work offline even if automatic tips are off.
Space/Enter activate supported focused buttons/options; disabled actions remain
inactive. Esc dismisses a tip. Your help choices are remembered without changing
cleaning results, dates, correction approvals or financial calculations.

Errors need resolution before the affected operation can proceed. Warnings need
review; repair source and calculated financial totals still require reconciliation.
Neither a saved candidate nor a review packet is a production-approved release.
Maintenance classification and direct Microsoft/SharePoint integration remain future
work. Do not rename an unsupported TMA XLS file to CSV/XLSX to force processing.

If saved folders become unavailable, Settings keeps the choices and shows what
needs attention. **Reset to Defaults** asks first and only resets preferences;
it never deletes reports/history. Advanced import accepts earlier workspace TOML
as a draft; validate/reconfirm local storage and save. Export Sanitized Template
omits real paths/credentials. No OneDrive synchronization is verified by this app.

## Local and SharePoint-synced raw folders

Raw Data Browse can select local folders or reports already downloaded through the
organization's OneDrive sync client. Preview stops known offline/recall placeholders,
missing files and files that change or read only partly. Make required files available
on this device, wait for export/download completion, then preview again. Existence,
a green folder indicator or a successful local read does not verify cloud sync.

Candidate history, review packets, SQLite and authentication caches must remain on
trusted local disk outside sync services. The Settings storage card keeps Microsoft
Graph unavailable: organizational sign-in and site/library selection are not enabled
in this prototype. No candidate is uploaded or published. Finance reconciliation is
not business approval. See sharepoint_foundation.md for developer tests and the
separate IT-authorized live-pilot requirements.
