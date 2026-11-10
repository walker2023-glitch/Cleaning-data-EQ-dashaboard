# January batch preview: ignored temporary file poisoned the month

## Cause and focused fix

Discovery's `_reports` correctly excludes filenames starting with `.` or `~`, or
ending in `.tmp`, `.part`, `.partial`, `.crdownload` or `.download`. It records an
`historical_temporary_file_ignored` month issue without selecting or reading the
extra file. January's three legitimate `ReportInventory` objects can all be Found.

The defect was in `preview_history`: `if month.issues or ...` rejected every report
before its verified read, then assigned `issues[0]` as that report's failure code.
Thus one unrelated Office lock file could produce three identical failures with
null counts, `integrity=not_read`, and `candidate_status=not_assessed`. Synthetic
January–June trees reproduce this exact condition in both layouts on baseline
58fe29a. This confirms the mapping defect; the actual private January folder and
its extra filename have not been inspected here. The code also covers incomplete
download and hidden temporary names, not just Excel `~$` names.

Only the existing ignored-temporary-extra notice is now nonblocking for batch
preview. All other month issues (including unknown future codes), ambiguous/missing
reports and selected-source problems retain their blocking behavior. Selected
report issues take precedence over other discovery issues in the failure code.
The original filename exclusion predicate is unchanged, shared with an additional
selected-source check: a temporary filename cannot become a preview source even
if an incorrect Found inventory is supplied. Source identity/version/SHA and stable
read validation still run for every real selected file. No temporary file is read,
renamed, deleted or accepted as a report.

No cleaner, financial schema v2, calculation, month/date rule, candidate selection,
approval state, SharePoint or Power BI behavior changes. This is a follow-up on
`feature/historical-batch-preview`, not a new milestone or a merge to main.

## Diagnostic distinction

- JSON `inventory_notices` contains month, fixed code, observed count and scope
  `ignored_extra_files`. It omits extra filenames and file contents.
- Report `code` and `warnings` no longer inherit the ignored-extra notice. Actual
  report failures retain their own reason. `failure_scope` distinguishes discovery
  month/report blockers, selected-source failures and report validation failures.
- CSV preserves its existing columns and appends `FailureScope` and
  `IgnoredExtraFilesInMonth`. The latter repeats the **monthly observed count**
  for each report slot; do not sum it across the three rows for a month.
- Desktop summary and selected-month details explain ignored extras separately
  from source/report failures. Technical details keeps both categories available.
- Discovery itself remains conservative: a month with extras may still have an
  inventory Needs attention status. Its eligible real reports can now be previewed.
  This fix does not broaden the separate single-month discovery workflow.

For the actual private extra filename, use Discover and inspect Problems & files
before preview, or export the existing private discovery JSON locally. Do not send
that private inventory or source reports to GitHub. A successful batch preview is
not independent business validation or an approval.

## Windows January–June acceptance

Close the running application before syncing dependencies. Use the source Git
clone, not the old Downloads prototype directory. Preserve any uncommitted local
work before switching/pulling.

```powershell
cd "$env:USERPROFILE\Cleaning-data-EQ-dashaboard"
git status --short
git fetch origin
git switch feature/historical-batch-preview
git pull --ff-only
git rev-parse HEAD
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python -c "import equipment_data_manager.historical_preview as p; print(p.__file__)"
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app
```

1. Confirm the new commit and loaded module path belong to this checkout.
2. Keep the existing authorized local raw root and explicit layout in Settings.
   Keep candidates local and the approved location unchanged. Do not reorganize
   or edit departmental originals and do not delete any lock file automatically.
3. Open Historical Data, set `2026-01` through `2026-06`, and **Discover again**.
   Old failed preview evidence does not update itself.
4. Click Preview Selected Months. Expect all **18 slots assessed**. January's
   three real reports should pass into their own source/schema/date validation,
   without receiving `historical_temporary_file_ignored` as their report failure.
   Existing real-data validation can still reject a genuinely invalid source.
5. Select January and open Problems & files. If a temporary extra remains, its
   ignored count is shown separately. Real reports should have actual counts and
   stable-read integrity if their existing validation succeeds. February–June
   should retain their prior behavior. Review financial warnings independently.
6. Export a new local diagnostic CSV/JSON outside all workspace/synced folders.
   Check the separate inventory notice and any actual report failure scopes.
   Confirm no new candidates/database/review requests/approvals were created and
   all original bytes, including temporary files, remain untouched.
7. Owner must rerun and accept the actual January results. Synthetic success does
   not establish that the real reports are verified, approved or production-ready.

For a disposable synthetic check, generate a **new** destination with
`examples/create_historical_batch_demo.py --output data/january-lock-demo`, then add
an invented `~$Work Orders January 2026.xlsx` to its January folder (use literal
single quotes in PowerShell so `$` is not interpolated). Do not do this to the real
folder. The extra must remain ignored while the 18 synthetic reports preview.

Full test/build/native packaging commands remain in historical_batch_preview.md.
Native Windows package and packaged/restart smoke must be run on Windows; Linux
success cannot establish those results. Check the feature branch's Actions run
before merging. No automatic merge is authorized by this fix.

## Verification recorded 2026-11-10

- Before fix: synthetic January lock-file reproduction failed in both layouts,
  matching the reported null-count/not-read failure pattern.
- After fix: complete Linux regression **820 passed, zero failures/errors/skips**;
  all 62 desktop-widget cases isolated in fresh processes, with no retries.
- Both-layout January–June tests compare all 18 report results with a no-extra-file
  baseline, verify only the real sources are read, and verify unchanged raw bytes
  and no candidate store. Additional cases cover strict selected temporary rejection,
  remaining discovery blockers, stale sources, failure precedence, exports and GUI.
- Wheel/sdist builds passed. Source and isolated installed-wheel desktop smoke
  passed phase 39 with the synthetic January lock file; both separate-process
  settings/restart checks passed.
- Native Windows executable/packaged smoke and hosted Windows/Linux outcomes are
  not verified here. This executor is Linux, with no Windows runtime. The existing
  feature push workflow includes native Windows build/component/desktop/restart
  checks using the updated smoke. GitHub API access is blocked by network policy,
  so inspect its actual Actions results separately before merge.
- No actual January source file or departmental extra file was inspected. Owner
  rerun/manual acceptance of all 18 real slots remains required. No merge occurs.
