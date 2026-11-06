# Next checkpoint after Microsoft 365 read-only components

## Timestamped HI-042b dependency follow-up

Review feature/tma-timestamped-layout targeting legacy-tma-compatibility 32d36b6,
which itself depends on discovery c425841. Neither base feature was merged into
main bd21499 at inspection. Do not replay or merge automatically. The owner has
supplied verified May structural/timestamp facts; the new no-footer adapter uses
them strictly, without text date parsing. Actual May/June output acceptance and
native Windows/hosted checks remain separate. See tma_timestamped_layout.md, then
resume the historical batch/snapshot plan only from the appropriate reviewed base.

## Legacy TMA dependency before historical backfill

Review feature/legacy-tma-compatibility targeting historical-folder-discovery
c425841; main was bd21499. Do not duplicate either branch or merge automatically.
The XLS/four-column candidate contract is synthetic-tested, not proof of the actual
May workbook. Follow legacy_tma_compatibility.md for owner-local acceptance and
native Windows/CI gates. No unknown title/header/footer or financial meaning may
be guessed to make a real file pass. Then resume the dependent historical
batch-preview/controlled-processing and snapshot plan below.

## Historical backfill handoff — supersedes older next-step priorities

First review/merge (owner action only) feature/historical-folder-discovery targeting
main bd21499. This PR implements flexible raw-folder layouts, persistent layout,
read-only historical inventory/export and captured-source single-month handoff.
Do not replay the already merged #16/#17 foundations. Recheck main/open PRs and
Windows/Linux/native executable results; API access was blocked here.

Then implement the explicitly dependent batch-preview/controlled-processing PR,
followed by historical candidate snapshot/reconciliation controls using existing
v2 packet/powerbi_pilot/powerbi_readiness APIs. See historical_backfill.md for scope
and missing-policy/independent-baseline gates. Do not claim those later phases are
implemented by the inventory. Preserve every cleaner, v2 financial meaning,
revision/correction mechanism, review request, disabled authority/publication and
production boundary. Actual historical tests are user-initiated on the authorized PC.

Review feature/m365-readonly-connectivity from owner-merged main 6b7e861 without
automatic merge. Require exact-head Windows/Linux and packaged SDK/GUI checks;
local Linux success is not Windows or live Microsoft evidence.

Next obtain actual IT authorization, private single-tenant registration/config,
selected-resource READ grants and approved synthetic files/device/cache policy.
Run only the separately authorized nonproduction procedure in m365_readonly_pilot.md,
record actual MFA/CA/account/permissions/redirect/hash/cache/failure outcomes privately,
and stop on any scope/policy/integrity issue. No production fallback or uploads.

Only after reviewing live evidence, propose a small connected read-only desktop
picker/status/sign-out/worker UI PR. Preserve byte/version/hash checks, local SQLite/
cache/origin receipts, corrections, month persistence, financial v2 and business-state
boundaries. Successful sign-in does not grant reviewer roles. Approval, publishing
and Power BI production changes remain separate, explicitly authorized milestones.
Do not request credentials/tokens/private reports in chat or commit them to GitHub.
