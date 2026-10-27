# Departmental workflow roadmap and project review

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
