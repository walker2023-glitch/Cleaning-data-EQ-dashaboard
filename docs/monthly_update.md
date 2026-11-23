# Milestone 3a — Hybrid Monthly Update Workflow

Approved hybrid behavior, based on verified main
`00648ca434c59b6dd39334b272ca584c303388fa` (Milestone 2 PR #30 and automated acceptance
PR #29 present). Branch: `feature/hybrid-monthly-update`. This is implementation for
owner review, not a merge, departmental approval or production activation.

## Employee workflow

Before: process reports, manually inspect candidate coverage, generate independent
historical snapshots and compare their selections yourself.

Now: process eligible reports using **Process Multiple Months → Batch processing**.
Then open **Power BI snapshot**, whose primary panel is **Monthly Historical Update**:

1. Confirm the inclusive reporting range above and Raw Data/layout in Settings.
2. **Choose completed baseline**: explicitly select one previously completed folder
   ending in `snapshot`. The app never picks a folder by its name, age or position.
   For a genuinely independent first build, use **Initial build (no baseline)**.
3. **Choose new local output location**: select a trusted local parent outside raw,
   candidates, reserved-approved, synced and production locations. The plan displays
   the exact new `Monthly_Update_Test_<id>` destination before writing.
4. **Review monthly update**. Read the entire plan below: baseline/proposed coverage,
   all three report types, included/unchanged/excluded months, previous/proposed record
   counts, missing slots, selected revision replacements, missing values and warnings.
   **Technical details (show)** contains exact identities and evidence.
5. Review the recommendation and select another permitted operation if needed.
   Check the plan/compatibility/local-storage acknowledgement. Replacements or removals
   additionally require **I authorize the displayed replacements and removals for this
   new version.** Then **Generate confirmed monthly update** and confirm the final dialog.
6. Read the saved path and warnings. **Open completed snapshot** opens its four
   canonical CSVs, manifest and compatibility report. This is local/unapproved and does
   not affect an active Power BI input. Preserve earlier versions.
7. For the next update or retry, explicitly choose the new completed `snapshot` as
   baseline and choose a new local output location. No automatic baseline authority is
   persisted. Identical selections then report **No Update Needed**, with generation
   disabled. An already-used destination is blocked, never overwritten.

The older independent snapshot controls are inside **Development tools (show)** for
maintainers; the primary employee path is the hybrid monthly plan above. The existing
**Create simplified comparison export** continues to consume one completed snapshot.
There is no new permanent comparison format choice. Settings History, single-report
corrections and prior candidate revisions remain available.

## Recommendation and permission rules

| Evidence | Recommendation | Permitted generation |
|---|---|---|
| No baseline; all selected months complete and raw hashes match committed candidates | Rebuild History, labeled initial build | Rebuild |
| Additional complete months; all baseline months and revisions retained | Add New Months | Add or explicitly chosen Rebuild |
| Same range and selections as verified baseline | No Update Needed | None; no duplicate output |
| Changed historical selections committed through existing correction workflow; raw matches | Rebuild History | Rebuild, with separate historical-change confirmation |
| Proposed range removes baseline months, otherwise valid | Review Required | Rebuild only, with explicit removal confirmation; alternatively expand range |
| Missing/ambiguous/invalid/unsupported report or candidate, pending source change, invalid baseline or destination | Review Required | None; correct evidence first |

Missing reports never mean zero rows. No fallback to older revisions, automatic
correction approval, reprocessing or recleaning occurs. A correction's approval token
alone is insufficient: the existing workflow must commit the corrected candidate.
Existing warning/financial/classification policies remain unchanged.

## Architecture and safety

`monthly_update.py` is a small planner and wrapper over `historical_dataset.py`.
Both Add and Rebuild reconstruct a full new version using the existing canonical
generator. Add is a coverage rule, not a CSV append: all baseline selections must
remain identical. This avoids duplicate transactions and mixed versions while reusing
its existing ordering, null, path, integrity, staging, validation and cleanup safeguards.

The only new plan is an immutable **in-memory Python value**, discarded on restart.
It binds the existing DatasetPlan, explicit baseline path and six-file digest,
before/after coverage/counts/replacements, raw source identities/hashes, layout,
permitted operations and exact destination. There is no serialized planning record,
SQLite/settings migration, dependency, new canonical schema or active-output pointer.
The existing baseline validator is reused; plan/configuration identity is also checked.
The baseline must belong to this workspace; no cross-workspace candidate rebinding.

Generation requires a mode-bound confirmation and separate change consent. It holds
the existing DELETE-journal candidate read transaction while revalidating the plan and
calling the existing generator. Sources/baseline/selections are reread before generation;
a changed identity, hash, selection, configuration or destination invalidates confirmation.
Existing stable-file identities are also checked between staged writes and immediately
before finalization, so an in-flight source/baseline change stops and cleans this run.
No cleaner is called. Raw discovery reads bounded local bytes and cannot prove remote
sync completion. Concurrent hostile same-user file edits are outside the existing local
filesystem trust model; this is not a distributed lock or signed authority.

Output remains exactly the existing six-file `historical-powerbi-v1` snapshot inside
a new container. No extra metadata file is added to the canonical contract. Previous
outputs, raw reports and candidates are read-only. Caught failures/cancellation remove
only the newly owned container; an abrupt OS/process death may leave `.s`, never a
completed `snapshot`. Do not import/resume `.s`; retain for diagnosis and preview a
fresh destination. No cleanup of another run or rollback activation is implemented.

## Windows acceptance — synthetic data only

Use the Windows CI prototype artifact for the reviewed commit or build natively:

```powershell
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv build
.\packaging\build.ps1
$dir = Join-Path $PWD 'data/m3a-packaged-check'
$p = Start-Process '.\dist\EquipmentDataManager\EquipmentDataManager.exe' -ArgumentList @('--smoke-test','--smoke-dir',$dir) -PassThru
if (-not $p.WaitForExit(180000)) { $p.Kill(); throw 'Smoke timeout' }
if ($p.ExitCode -ne 0) { throw 'Smoke failed' }
Get-Content "$dir/desktop-smoke.json"
Get-Content "$dir/restore-smoke.json"
```

Require passed **phase 55** and passed separate-process restart. Earlier phase-51
comparison/lineage checks remain; the additional phases check monthly recommendation,
explicit cancelled/confirmed generation, preserved baseline and unchanged retry.
The acceptance CI tests the exact pushed/PR SHA (manual dispatch can select a ref).
The acceptance runner still requires phase 51 for a separately selected old M2 checkout;
it requires phase 55 and the extra check identities for this new implementation.

For hands-on checks, create invented reports with
`python -m uv run --frozen --all-extras python examples/create_historical_inventory.py --output data/m3a-invented`.
Use its local raw layout, a NEW private candidate store and reserved-approved folder.
Never use departmental stores for these scenarios:

1. Process January reports; build initial January history without a baseline.
2. Process February, select the January baseline and January–February range: Add New
   Months. Verify January revisions/counts unchanged and February appears once.
3. Select the new output as baseline with the same range: No Update Needed; no output.
4. Change an older invented report: Review Required. Use the existing single-report
   correction approval AND **Process Reports & Save Candidate**, then preview again.
5. Confirm Rebuild with its displayed revision replacement. Verify no extra appended
   copy of January and both prior snapshots remain byte-identical.
6. Remove one raw report or select a month with a missing candidate: Review Required,
   identifying the month/type. Restore/complete it and review again.
7. Select an invalid/missing baseline or modify evidence after preview: blocked/stale;
   no new completed output. Correct evidence and preview again.
8. Preview January only against January–February: Review Required. Rebuild requires
   separate explicit removal consent; Add is unavailable. Prior coverage is preserved
   in previous outputs. Expand range instead to retain February.
9. Cancel the confirmation dialog, then stop a longer generation. No completed partial
   output; previous snapshots/candidates remain. Resolve any failed operation before retry.
10. Restart the app: Settings/candidates survive. Explicitly reselect the completed
    baseline/destination and make a fresh plan; no old confirmation survives restart.

Check keyboard/F1 help, scaling, wrapping, screen-reader/accessibility expectations and
actual employee comprehension on the managed Windows machine. Automated Windows runs
are not departmental financial approval or Power BI M/DAX execution.

## Limits and next gate

No Milestone 3b, stable production activation, rollback activation, SharePoint write,
automatic Power BI refresh, cleaner/financial/classification fix, new Building alias or
new dependency. V1/V2/V3 comparisons and the canonical four-table contract are unchanged.
The previously documented V3 manifest scalar-type defect remains owner-gated and is not
fixed here. Independent acceptance reviews and missing business authorities remain.
After owner review of 3a, propose **Milestone 3b — stable local activation and recovery**
separately; do not start it under this approval.
