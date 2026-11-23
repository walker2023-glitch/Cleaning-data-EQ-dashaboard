# Owner-directed Milestone 2 — employee interface simplification

Baseline: verified remote main `dc73a80a4ecbbe038f687c7735887bb1a210f644`,
including owner-merged comparison V3 (Milestones 1a/1b/1c).
Branch: `feature/employee-interface-simplification`. This milestone changes the
existing CustomTkinter presentation, not processing rules or output contracts.

## Navigation before and after

| Before | After |
|---|---|
| Process Reports | Process Reports |
| Results | Results |
| History | Settings → Processing History |
| Review & Approval | Hidden from employee navigation; foundation/records/tests retained |
| Historical Data | Process Multiple Months |
| Settings | Settings |
| Help | Help |

Settings has a **Processing History** button in its header. It opens the original
read-only view, refreshes saved current/previous revisions, and retains Refresh
history and Open selected revision folder. Back to Settings returns to the form.
Existing output-format/store selection still determines the history shown. No
history deletion, database/schema migration or candidate-storage change occurs.

Internal `Historical Data`/`History` route keys and page/module attributes remain
compatible with existing automation. `Process Multiple Months` is accepted as an
alias. ReviewPage still has its explicit developer API route for regression tests;
no ordinary navigation control opens it. This is a usability boundary, not a new
security/authentication layer. Approve, Publish and sign-in stay disabled; local
review requests remain intact and no requests are sent by this milestone.

## Important workflow changes

**Correction review:** the dialog says approval saves nothing, retains current and
proposed counts/totals and the existing checkbox/token check. Its button is
**Approve Correction for Processing**. The separate primary action is
**Process Reports & Save Candidate**. Only successful processing writes/selects
the correction; the earlier revision remains. Selection changes clear preview and
approval state. Source hash/current revision guards run unchanged. The dialog's
long summary scrolls while the checkbox and confirmation action remain available.

**Results:** each row retains report type and month and distinguishes Saved
successfully, Already processed / unchanged, Needs review, Failed and Stopped /
not processed. Totals include warnings. Completion wording is derived from actual
outcomes, so a completed run with failures does not imply every report succeeded.
Cancellation is counted separately from failure. The Results page gives its space
to the outcome table/details, with a Process more reports return action rather
than repeating the input form. Preview success without a saved
artifact is never presented as a successful save. Each result gives a next step.
Multi-month processing retains its original more specific status codes in technical
evidence while showing the same business distinctions and retry instructions.

**Technical information:** normal report details retain counts, exclusions, missing
data, warnings, financial metrics and next steps. Optional Technical details holds
hashes, versions, paths, revisions and source-date traces. Snapshot details likewise
keep business issues visible and move revision/hash identities into an optional
pane and optional revision column. Multi-month technical JSON/diagnostic exports
remain available. Storage connection/test-configuration controls move into existing
Advanced Settings. Nothing is removed from stored data, logs or diagnostic exports.

**Power BI stages:** processing creates local candidate revisions; snapshot creation
separately combines selected candidates into the existing four-table canonical test
snapshot; collapsed Development tools separately creates the five-table V3 backup
comparison. None activates, publishes or refreshes production Power BI. There is
no placeholder Update Power BI Data button or new permanent format workflow.

**Help:** existing Guided Mode, Brief/Detailed, hover/focus/F1 and the offline guide
explain selections, writes, recovery and next steps. Explain this step recognizes
Settings, History, Results and Process Multiple Months. New controls use the same
keyboard activation registration. No new framework, service or dependency is added.

## Windows acceptance

Use this feature commit/review build and an isolated synthetic local workspace.
Keep real originals, production PBIX and SharePoint untouched. Do not run GUI
suites and smoke checks concurrently on one display.

```powershell
uv sync --frozen --all-extras
uv run --frozen --all-extras python .github/run_tests.py
uv build
.\packaging\build.ps1
.\dist\EquipmentDataManager\EquipmentDataManager.exe --smoke-test --smoke-dir data/m2-windows-smoke
```

The smoke must exit successfully with desktop-smoke.json status passed at phase
51 and restore-smoke.json passed true. It covers the existing cleaning, correction,
history, snapshot/V3 export and fresh-process settings restore, plus new navigation,
truthful save wording and optional diagnostic access. CI packages the Windows
executable on feature pushes even if API permissions prevent PR creation.

Manual acceptance (about 20–30 minutes plus build time):

1. Launch the executable with a fresh test settings profile. Check the five primary
   choices above. Confirm no History or Review & Approval navigation buttons and no
   Update Power BI Data button. Use Tab/Enter/Space and F1 on the new controls.
2. Save synthetic Raw Data, local Candidate Output and reserved Approved folders.
   Run Check Locations/Save Settings. Confirm startup and help preferences survive
   a full close/relaunch. Existing earlier settings must still load.
3. Use the bundled synthetic sample: confirm month, Preview Processing (no saved
   report), then Process Reports & Save Candidate. Expect Saved successfully with
   readable warnings, counts and next steps. Repeat unchanged: expect unchanged,
   not another revision. History in Settings should refresh with one current row.
4. On a disposable COPY of that synthetic source, change a cost. Preview/review
   correction, check the box and approve for processing. Verify no new revision
   exists yet. Change the selection once: the approval must be invalidated. Preview
   and approve again, then process. Verify the earlier file survives and History
   shows current/previous revisions. A failed correction must retain the old one.
5. Preview two distinct filenames containing identical synthetic data. Make one
   source unavailable before processing. Expect one saved/unchanged outcome and one
   failed row with a partial-failure summary, not a generic all-success message.
   Restore availability and preview again. Stop a multi-report run; completed
   files remain and remaining rows are stopped/not processed.
6. Open Technical details on results and snapshots: hashes/versions/paths must be
   available there, while normal details still show warnings, missing values,
   incorrect totals and exclusions. Advanced Settings still has the offline
   connection/configuration diagnostics. No authentication should be attempted.
7. Process Multiple Months must open the existing range discovery/preview/plan/
   processing pages. Verify month/type selection and correction routing still
   work. Review counts/warnings, generate an unchanged four-table snapshot, then
   use Development tools for a five-table V3 comparison. Check V1/V2 CLI verification
   and V3 integrity using their existing guides; no schema changes are expected.
8. Confirm snapshot/comparison wording says local/unapproved/development/backup test,
   with no claims of production activation, refresh or publication. Close/relaunch
   the packaged app and repeat navigation/help/history access at 125/150/200% DPI
   on the intended employee computer. Business acceptance is not established by CI.

## Validation and limits

Exact local counts, failures/skips, builds and smoke outcomes are recorded in
[testing.md](testing.md). Linux and synthetic checks must be distinguished from
native Windows, managed-PC accessibility and actual departmental acceptance.

No cleaner, financial calculation, canonical or comparison V1/V2/V3 schema,
Settings schema, candidate store, append/rebuild, activation/rollback, production
Power BI/SharePoint, approval/authentication service or dependency change is in
scope. Older maintainer documents retain historical feature descriptions; the
employee guide and these instructions describe the current navigation.

Next gate: owner review and Windows employee acceptance of Milestone 2. Do not
begin Milestone 3a without separate approval. No automatic merge is authorized.
