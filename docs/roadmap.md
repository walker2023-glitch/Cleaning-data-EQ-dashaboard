# Departmental workflow roadmap and project review

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
