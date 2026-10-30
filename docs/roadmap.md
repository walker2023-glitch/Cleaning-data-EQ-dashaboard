# Departmental workflow roadmap and project review

## Microsoft 365 read-only foundation — 2026-10-30

Main 6b7e861 contains owner-merged PR #16. The feature starts there without replaying
approval UX or SharePoint foundation commits. Owner-reported UX/OneDrive raw-read
success is preserved; direct Microsoft connectivity remains unverified.

Implemented for an authorized TEST-only operator pilot: pinned official MSAL and
requests optional dependencies; tenant-bound gated public-client/session/cache/
claims handling; TLS/read-only HTTP; exact site/library/folder and synthetic file
hash allowlists; verified remote bytes into existing preview/process; local original/
provenance bundles; offline configuration UI/help and executable dependency checks.
Mock/SDK-with-mock-metadata tests establish offline behavior only. No real Microsoft
request/browser/sign-in has run. Desktop connected picker/sign-in, reviewer roles,
approval, publication and production remain unavailable.

Next: actual written IT authorization and private config/grants/device/cache policy,
then the manual nonproduction synthetic pilot in m365_readonly_pilot.md. Review real
MFA/CA/permission/cache/redirect results before a small connected desktop UI PR.
Require exact-head Windows/Linux/build and managed-PC checks; API HTTP 403 still
prevents independently reading hosted results. Prior checkpoints are historical.

## Approval UX / identity readiness — 2026-10-29

Owner merged PR #15 into main a01ebb5; c32d820 is already included. New branch:
feature/approval-ux-identity-readiness. No stack commits were duplicated. Open PR
metadata/hosted checks remain unavailable through the API (HTTP 403); Git merge
history is not proof of CI/reviewer approval.

Implemented: shared visible month/year selection, strict settings-v2 remembered
period with v1 compatibility, startup/close preference ordering, read-only employee
review tabs and exact technical evidence, clear local-versus-authoritative status
cards, contextual help, and an unavailable-by-default reviewer identity interface.
Local request persistence, duplicates/stale detection, cleaners/financial v2 and
business states are unchanged. No production or live authentication operation.

Next: exact-head Windows/Linux/packaged and managed-PC acceptance, then an explicitly
authorized identity/role-service design and nonproduction pilot. Receipt/decision/
publishing connectors are separate gates. See approval_ux_identity_readiness.md.
Earlier milestones below retain their dated implementation/test evidence.

## Approval / publishing foundation — 2026-10-29

Owner merged PR #14 into main at 36f8f20. New work starts from main on
feature/approval-publishing-foundation. Owner now reports successful local Windows
raw reads from a OneDrive-synchronized SharePoint folder; this is not direct Graph
connectivity, a synchronization guarantee or approval to publish.

Implemented: monthly evidence view, exact selections/source/output/summary hashes,
counts/nulls/warnings/financial summaries, durable local unsent requests, stale
selection/source detection, disabled final approval/Publish and new Guided Mode.
Model-only: mock-authorized in-memory staging, read-back equality, immutable sets,
conditional selection, duplicate/concurrent/interrupted recovery and rollback.

Next: authoritative reviewer role/identity/evidence/retention policy, final approved
artifact contract, then independently reviewed durable coordination and authorized
nonproduction Graph pilot. Publishing/production refresh remains disabled. See
approval_publishing_foundation.md. Older pending integration/feature statuses below
are dated records, not current branch state or proof of hosted CI outcomes.

## Integration checkpoint — 2026-10-29

All remote feature tips are now included in **integration/stable-baseline** via a
single non-fast-forward merge from current main. The owner already merged #13 into
#12's branch at ae9a865; no independent feature branch was omitted or cherry-picked.
See [exact branch/PR evidence](integration_branch_audit.md) and
[baseline/rollback/validation gates](integration_baseline.md).

473 local tests pass; source GUI/restart, installed-wheel synthetic four-table
readiness, mock Graph and all 15 M syntax checks pass. Windows executable and hosted
CI are unverified because API requests remain proxy-blocked. Do not merge until
those checks, managed-PC acceptance and explicit owner review are complete.

After approval, use main as the single starting baseline. Next: authorized read-only
MSAL/Graph test-site pilot after IT decisions, or local employee/recovery testing
while access is pending. Inventory still requires verified fixtures/keys.
Candidate publication, business approvals and production refresh remain separate.
Older checkpoints below are historical, not current PR/feature status.

## Current checkpoint — 2026-10-28, Milestone C foundation

This branch builds on the locally reviewed Milestone A head 454c7a0. Git remote
branch refs confirm that parent head; GitHub API/PR status access is currently
blocked by the environment proxy. Last confirmed PR review (2026-10-27): #1 merged,
#2–#12 open in their dependency stack. Do not assume additional merges or retarget
anything automatically; recheck live PR states when access is available.

Owner now reports successful January/February structural/source-integrity/financial
checks and Desktop imports/visual testing, plus an inventory matrix prototyped
separately in Power BI. These are owner-reported results, not production approval
or evidence that an inventory adapter/Graph connection exists in the application.

Implemented C foundation: read-only local/synced provider and availability/stability
checks; existing engine bridge; injected Graph site/library/list/download/retry/
version/hash behavior; MSAL-compatible session logic; DPAPI/cache persistence
component; fixed nonproduction probe-only write verification/recovery; truthful
Settings/Guided Mode with Graph disabled. No raw/candidate/approved publication state
changes, calculation/schema changes or live Microsoft/SharePoint/PBIX operations.

Next focused C PR, only after IT/test authorization: real MSAL/cache/HTTP bootstrap,
account/site/library selection and connected read-only test UI. Actual SDK/tenant/
redirect/device/permission/cache behavior needs an approved test-site pilot. Optional
probe server conflict semantics must be verified before any write feature is enabled.
Business approval/publisher, approved snapshot selection, shared concurrency,
production refresh and D deployment/recovery/handoff remain separate later gates.
Inventory parsing still needs verified input fixtures/keys; the separate matrix
prototype does not resolve that contract. See sharepoint_foundation.md and
sharepoint_live_pilot.md for the status matrix, safe folder layout and IT checklist.


## Current checkpoint — 2026-10-27

Reviewed local/remote branches, all PR states, documentation, cleaners/export schemas,
monthly packets/snapshots, M queries, storage boundaries and tests. Only #1 is merged;
#2–#11 remain open in the existing dependency chain. PR #11 at bffd53f is the base
of feature/powerbi-real-data-readiness. Its Windows/Linux checks passed. No automatic
merge/retarget is performed. Prior dated reviews below remain historical records.

| Milestone | Current work / completion boundary | Next gate |
|---|---|---|
| A — Real-data Power BI readiness | Explicit v2-only packet selection, four-table snapshots, hash/provenance checks, recomputed financial controls, private monthly/combined expectations and raw-file verification, shared-period M comparison and migration instructions | Owner runs real v2 Desktop/model trial and records page/DAX/relationship/ID/null/hour/capacity results |
| B — Inventory foundation | Design and original-module dependency review only; inventory not in monthly completeness | Actual sanitized inventory/raw-expected snapshots, status/grain/duplicate policy and Building_Dim/location map |
| C — SharePoint foundation | Existing disabled Graph boundary and delegated/local/synced/approval/IT design only | Separate auth/test-resource authorization, IT registration/scopes/cache/device policy, offline mocks then approved test site |
| D — Production readiness | Checklist/design only; no approval/publisher/deployment | Data/finance/model/IT sign-off, authenticated approvals, recovery/rollback/shared locking, employee training and managed-PC handoff |

Owner-reported evidence now includes January/February v2 arithmetic reconciliation
and a successful synthetic **previous repair schema** Desktop pilot. Do not relabel
that pilot as v2 or production-approved. Real v2 Desktop testing remains manual.
No exact existing model/DAX inventory or actual inventory export is supplied here.
All new repository fixtures/dollar values are invented; private expectations remain local.
See powerbi_real_data_readiness.md, powerbi_backup_migration.md,
inventory_foundation_design.md, management_decisions.md and sharepoint_integration_plan.md.


Review date: 2026-10-22. Remote branch heads, all seven existing PRs, current tests,
architecture and documentation were inspected. This branch starts from PR #7's
74cb7d3. Prior docs referring to PR #1 as an unmerged draft were historical and
have been corrected. No PR was merged as part of this work.

| PR / branch | State at review | Scope |
|---|---|---|
| #1 feature/m0-project-setup | Merged into main | Scaffold/discovery; business fixture gate still open |
| #2 feature/m1-cleaning-engine | Open, targets M0 | Offline engine/local manifest |
| #3 feature/m2-desktop-gui | Open, targets M1 | Offline GUI and packaging |
| #4 feature/service-orders-february-layout | Open, targets M2 | Exact no-price CSV adapter |
| #5 feature/multi-month-compatibility | Open, targets February fix | Summary metadata and provisional TMA XLSX |
| #6 feature/january-rejection-diagnostics | Open, targets multi-month | Date/exclusion reasons and Windows checks |
| #7 feature/powerbi-candidate-exports | Open, targets diagnostics | Schema-v1 candidate tables and classifier design |
| feature/monthly-department-workflow | New, targets PR #7 branch | Local monthly discovery/checklist/review packets and integration plans |

There are no other remote branch heads at review beyond these seven and main.
Current PRs #2–#7 have successful Windows/Linux checks at their reviewed heads;
PR #1's historical Windows setup checks failed, with runtime setup corrected in
later branches. PR checks are not business approval. There were no recorded
review approvals on the open PRs at this review. The user's successful Windows
processing is useful compatibility evidence; the older January rejection symptoms
were not reproduced with the same raw inputs on the then-current adapter branch.
Do not close/retarget/merge the dependency chain automatically. Maintainer review
must decide the eventual merge/retarget order.

## Implemented versus experimental versus blocked

| Area | Available now | Validation / dependency still open |
|---|---|---|
| Cleaning | Supported repair/service CSV and observed TMA XLSX; strict layouts/dates/exclusions; source preservation | Trusted expected outputs, new layouts/encodings, XLS sample and business contracts |
| Safety | Write-free preview, SHA-256 identity, local current revision/type/month, explicit correction tokens, retained revisions, per-record CSV rejection diagnostics | Shared multi-PC locking, operational restore/retention drill and authenticated approval |
| Desktop | Responsive native GUI, file selection, results/history/help; all three report types; user-tested Windows processing | Nontechnical managed-PC accessibility/usability and release/distribution approval |
| Standardized exports | Header-first schema-v1 candidates, ISO dates/text IDs/provenance, nullable money plus separate Legacy comparison values | Finance/schema/baseline approval; production accuracy unverified |
| Monthly workflow | Configurable raw/candidate/reserved-approved folders, direct discovery, missing checklist, mixed-type preview/process and explicit immutable review packets | Zero-activity/optional report policy; no approved publication; local single operator only |
| Power Query | M example plus offline Python contract tests for synthetic current-month sets | Actual M/PBIX pilot, decimal precision, relationship/DAX regression, approved snapshot publisher |
| Microsoft / sync | Disabled Graph repository and future delegated integration design; readable local sync files can be selected | IT registration/consent/cache/device policy, explicit implementation/live test approval; no sync verification |
| Maintenance matching/classification | Evidence-preserving raw fields and design only | Labeled examples, keys, taxonomy, review policy and evaluation gates; no classifier code |

## Next gates in order

1. **Business validation** — data owner supplies trusted raw/cleaned pairs and
   source/baseline counts for all three types; finance resolves repair cost-field,
   hours/default/rate meanings; model owner approves schema/nulls/precision.
   Continue local candidate review; do not alter calculations without explicit approval.
2. **Local departmental pilot** — use the monthly SOP with nontechnical employees;
   agree zero-activity/month completeness policy, retention/backup/support owner,
   accessibility and corrected-month procedures. Test failures and restore on a
   second managed Windows PC without Python. IT approves signed distribution.
3. **Approved publication design/implementation** — authenticated review evidence,
   immutable complete multi-month snapshots, current pointer and concurrency/
   recovery tests. This is separate from candidate export and needs authorization.
4. **Power BI comparison pilot** — actual Power Query evaluation in a PBIX copy,
   preserve table identities/relationships/DAX; compare totals and all visuals.
   Production model migration and publication require separate explicit approval.
5. **Connected test pilot** — only after separate approval and IT prerequisites,
   implement delegated MSAL/Graph on approved test resources, least-privilege
   permissions and shared concurrency controls; no production fallback.
6. **Production release** — business/finance/model/IT sign-off, recovery and security
   checks, named refresh/support owners, separately authorized destinations and
   deployment. No current milestone grants these approvals.

See `monthly_workflow.md`, `validation_checklist.md`,
`sharepoint_integration_plan.md` and `powerquery_integration.md` for concrete paths.

## Settings and Guided Mode follow-up (2026-10-22)

PR #8 remains open at 456440d; it is the parent of
feature/settings-guided-mode. PR #1 alone is merged; PRs #2–#8 keep their existing
dependency relationships. No automatic merges/retargets are performed.

Implemented: visual first-run/settings form, Browse/recommended local candidate
location, folder indicators/confirmed creation, strict private atomic preferences,
restart restore/reset/legacy import/sanitized template, default Detailed Guided
Mode, persisted Brief/Detailed choices, hover/focus/F1/disabled-control help,
centralized dashboard-aware registry, bundled offline guide and adaptive short/
scaled-display layout. All existing cleaning and monthly safeguards remain.

Next: nontechnical employee pilot on a second managed Windows PC, keyboard/screen
reader and 125/150/200% multi-monitor checks, IT confirmation of any custom local
candidate directory and recovery/support policy. Candidate path checks cannot prove
absence of every sync client. Business/finance/schema baselines, repair cost-field/
hours/rate reconciliation, zero-activity policy and real Power Query/model validation
remain open. Microsoft auth/Graph, approved publication and production Power BI
still require separate authorization; this usability milestone does not grant it.

## Power BI pilot follow-up (2026-10-23)

PR #9 (feature/settings-guided-mode, 25d7a28) remains open and is the base of
feature/powerbi-integration-pilot. PR #1 alone is merged; #2–#9 remain in their
existing dependency chain. No merges or retargets occur here.

The next user-authorized priority is local model comparison before more interface
work: assemble explicit monthly candidate selections, check complete schemas/months,
import into a separate PBIX and record source/cleaned/existing-measure differences.
Synthetic assembly and arithmetic checks are implemented; real M/DAX/visual checks
and exact model contracts still require the model owner's evidence. Business/finance
validation and an independently approved publisher remain production gates. This
candidate-only pilot does not depend on implementing that publisher and does not
authorize production ingestion, authentication or SharePoint access.

## Financial correction follow-up (2026-10-26)

feature/repair-financial-mapping starts from PR #10's 6857953. Existing PRs remain
open and unmerged. Repair v2 corrects source-total meaning without altering original
calculations, adds monthly summary integrity/reconciliation and migration examples.
The prior PR #10 Windows PR job lost hosted-runner communication; its same-head
branch Windows/Linux checks passed. No speculative GUI/runner fix is included.

Next evidence: formatted repair XLSX and nonzero grouped totals, actual February,
trusted expected pairs and finance/model contracts. Continue local candidate review;
reconcile source totals and separately review estimate assumptions before migration.
No production dashboard, approved output, SharePoint or authentication changes.
