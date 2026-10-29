# Next development checkpoint

First finish integration/stable-baseline review: inspect exact-head hosted
Windows/Linux checks, build and run the packaged Windows smoke, complete a second
managed-PC employee/recovery trial, then obtain explicit owner approval before
merging into main. The current Linux-only evidence does not close that gate.
See integration_baseline.md for dependencies, blockers, final merge commands and
rollback. Do not merge/retarget the historical PR stack automatically.

After the integration is approved and merged, create future feature branches from
updated main. The recommended next implementation is a narrowly scoped **read-only
SharePoint test-site pilot**, only with explicit test authorization and the completed
sharepoint_live_pilot.md IT checklist:

> Preserve the stable baseline's cleaners, financial v2, Power BI four datasets,
> local candidates/history, Settings and Guided Mode. Wire real MSAL public-client
> authentication, the protected cache lifecycle and a constrained HTTP transport
> against approved nonproduction resources only. Validate tenant/account/site/library
> selection, least-privilege grants, cache ACL/sign-out/claims handling, safe downloads,
> transfer identity and permission failures. Keep publication and production refresh
> disabled. Use synthetic fixtures, offline mocks and authorized live test evidence
> separately. No real secrets/reports in Git, broadened permissions, production
> fallback, candidate approval or automatic merge. Use a small feature branch and PR.

Until IT/test authorization arrives, continue local managed-PC usability/recovery
acceptance. Inventory work is an alternative only after verified raw/expected
snapshots, status/grain/duplicate policies and Building_Dim keys are supplied; the
owner's separate Power BI matrix is not an application adapter contract. Do not
add inventory to existing monthly completeness or invent equipment keys for TMA.
Authenticated approval, shared concurrency, publication and production deployment
remain separately reviewed later milestones.
