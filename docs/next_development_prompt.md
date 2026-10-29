# Recommended next development prompt

First run the real schema-v2 Power BI Desktop acceptance in
powerbi_real_data_readiness.md. Keep actual reports/amounts/model details private;
share a sanitized acceptance summary and authorized inventory examples as needed.
Then use this prompt for a focused Milestone B:

> Continue Milestone B — Equipment Inventory Foundation from the reviewed
> Milestone A branch. Read the roadmap, inventory_foundation_design.md, current
> contracts and my schema-v2 Power BI acceptance results first; inspect open PRs
> without merging. Inspect the authorized inventory raw/expected fixtures and two
> dated snapshots I supply. Implement only verified inventory layouts, literal text
> IDs, explicit current snapshot selection with immutable history, duplicate-ID
> review, online/offline preservation, reviewed location mappings and visible
> unresolved locations. Prepare the Building → Room → Equipment Name → Equipment ID
> matrix and a validated one-to-many repair/service relationship proposal; do not
> assume TMA work-order IDs are equipment IDs. Do not add inventory to the existing
> monthly three-report completeness rule. If source layout, status or Building_Dim
> keys are missing, document that dependency instead of inventing it. Preserve all
> existing cleaners, financial v2, GUI/settings/history/correction behavior and tests.
> Use synthetic fixtures in GitHub, a new feature branch and PR. No live Microsoft
> authentication, SharePoint access, production PBIX changes, invented approvals
> or automatic merges.

Milestone C auth/storage mocks should follow separately after inventory evidence
and the documented IT approvals. Milestone D handles approved publication,
deployment, recovery, employee training and successor-maintainer handoff.
