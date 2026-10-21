# Equipment Data Manager: local prototype

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
skipped even if renamed. Use separate runs for different months or report types.
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

The **Output format** selector offers Legacy candidate (the existing reports) and
Power BI CSV candidate (one header, standardized columns and dates). Changing it
requires another month confirmation and preview. Use Legacy mode to save a
comparison/rollback CSV; the Power BI mode does not replace those artifacts.
Both modes retain the original cleaning/exclusion rules and process only local
supported reports. Power BI candidates have their own history under the base
folder's powerbi_candidates directory.

These exports are **unapproved candidates**. The financial discrepancy and trusted
cleaned-output comparisons are unresolved, so the application does not publish
approved monthly exports. Do not point a production Power BI query at either
candidate/history directory. SourceMaintenanceTag is a preserved description tag,
not an approved maintenance classification. No classifier is implemented.
