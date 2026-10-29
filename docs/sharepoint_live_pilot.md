# Future authorized SharePoint pilot and approval boundary

## Integration status — 2026-10-29

The foundation is preserved in integration/stable-baseline. All mock/storage/session
regressions passed in the 473-test Linux suite. Hosted native Windows DPAPI and
packaged results remain unverified; no live tenant, sync, SDK or server write
behavior is established. The integration task grants no live SharePoint approval.
The IT checklist below still gates a separately authorized read-only pilot.
See integration_baseline.md for the current consolidation evidence.

This is a checklist, **not authorization to connect now**. Default Graph sign-in/
transport and all business publication remain disabled. The current milestone uses
mocks/synthetic data only. Complete these gates in a later focused PR and approved
nonproduction environment; never substitute production when test access fails.

## IT decisions before SDK/transport wiring

- Name departmental/data, finance, model, IT application and successor support owners.
- Approve a native/public single-tenant Entra registration, supported system-browser
  redirect/loopback, organizational account selection, MFA/conditional access and
  broker/proxy/device requirements. No desktop client secret or password collection.
- Evaluate least-privilege delegated scopes and explicit selected-resource grants
  (selected-site/file options where the tenant/endpoints support them). Do not assume
  Sites.Selected alone grants access or automatically request broad scopes. The
  employee also needs independent SharePoint permissions; no admin role is assumed.
- Record exact approved TEST site/library/drive/raw/probe folder IDs and permitted
  download hosts in private config, with separate read/write capabilities. Prove
  selected library membership in the chosen site. graph.example.toml is an inert
  template, not a loader or activation mechanism. Keep actual IDs private as needed.
- Approve the pinned MSAL/HTTP dependencies in the next PR, tenant-bound authority,
  real PublicClientApplication construction and cache serialization lifecycle;
  explicitly disable PII/authorization/signed-URL logging. Handle claims challenges,
  revoked consent, expired tokens, account changes and sign-out/purge.
- Validate current-user DPAPI, NTFS cache ACLs, local cache/SQLite paths, encryption,
  retention, shared-cache locking, interrupted-write recovery and endpoint security.
  Never disable tenant security/antivirus to run the prototype.
- Approve executable signing/distribution/updates, a second managed-PC acceptance,
  support ownership, raw/candidate backup and recovery drills. Windows native DPAPI
  tests are not proof of the department's credential/device policy.
- Separately agree Power BI refresh identity/ownership, gateway/Service permissions,
  test workspace and model/data/finance approval. No PBIX or production refresh is
  modified by this milestone.

## Minimal live acceptance, after separate explicit approval

1. Wire the real MSAL public client, protected cache and a constrained HTTP transport
   only against configured test resources. Real construction/authority discovery
   can access the network; do not call it during offline tests. Confirm displayed
   organizational tenant/account and selected site/library with the operator.
2. List only permitted libraries/direct folders. Test restricted users, no-access
   folders, wrong tenant/account, pagination, missing folders and expired sessions.
   Access denied must stop without broader scopes or a production fallback.
3. Download a synthetic test report using captured item/drive/parent/version. Test
   source change before/during download, interruption/timeout, size/hash mismatch,
   redirect allowlists and no bearer forwarding to content hosts. Preserve raw
   bytes. Pass the verified bytes into a local preview and keep SQLite/candidates local.
4. If optional probe writes are explicitly authorized, configure a separate test
   probe folder and upload only the fixed synthetic .txt probe. Verify downloaded
   bytes, then test existing-name conflict and lost response after creation. Confirm
   server create-only behavior; the current query/header request alone is not proof.
   Recover by explicit list/verify, not blind upload retry. Do not upload candidates.
5. Test cache persistence/restart, consent revocation, sign-out, token expiry/claims
   challenges, interrupted writes, permission loss and cache recovery on an approved
   Windows user/device. No credentials/tokens/private reports go in logs or GitHub.
6. Record actual SDK/transport/server/device versions, permissions/grants, tester,
   date, scope, expected/observed results, hashes and redacted evidence privately.
   Only real tests justify a connected/sync/upload status; mocks do not.

## Business approval and future publication — design only

Keep distinct states: raw source, cleaned CandidateUnverified, financially reconciled
candidate, business-approved exact revision, published approved snapshot. Reconciliation
is evidence, never approval. No current method changes these states. A future
approval service must authenticate reviewer identity/authority and bind UTC timestamp,
report type/month, selected revision, source/main/summary hashes, cleaner/schema
versions, independent comparisons, financial/business decision and evidence to the
exact bytes. A local correction token or user-editable Approved cell is insufficient.
Corrections invalidate old approval for new bytes and require fresh evidence/review.

A future publisher must validate approval, stage a complete immutable approved set,
verify uploaded bytes, acquire/recheck shared concurrency state and conditionally
select one snapshot pointer. Failed/partial uploads stay unselected; old revisions
remain readable. No default create_output method may publish CandidateUnverified.
Create-only probe tests do not implement authenticated approval or atomic publication.

## Proposed approved SharePoint/Power BI layout

Names are examples, not existing tenant paths; resolve actual IDs through IT:

```text
Raw/YYYY-MM/{repairs,service_orders,tma_work_orders}/
Candidates/                         optional restricted future review exchange, NOT production ingestion
ApprovedSnapshots/<snapshot-id>/
  tables/repairs/                   one approved CSV per selected month, financial v2
  tables/repair_financial_summary/  one approved summary row/month, financial v2
  tables/service_orders/            current versioned service schema
  tables/tma_work_orders/           current versioned TMA schema
ApprovedSelection/current.json     future conditional pointer, NOT implemented
Archive/                           previous/unselected snapshots, never recursive ingestion
Logs/                              approved redacted audit evidence
```

Keep SQLite/caches local, not in any of these synced/shared folders. Power BI should
resolve one selected approved snapshot once per refresh and use the exact four
report subfolders and explicit month set. Exclude archives/history/staging. Keep
text equipment IDs, dates, nullable financial values, repair/source/legacy/estimate
meanings and monthly-summary grain; never expand monthly costs onto transactions.
Preserve existing table identities, DAX, Building_Dim/calendar/filters and capacity
visuals through the backup-model procedure. The current local candidate M examples
are for review, not a SharePoint connector or approved publisher. Actual SharePoint
M connector/pointer resolution, authenticated approvals, rollback and production
refresh need their own reviewed implementation/authorization.

## Recommended next PR

After IT/test authorization, implement only real MSAL/cache/transport bootstrap and
connected **read-only** test-site UI selection. Preserve the disabled business
publisher. Test live tenant/account/permission/redirect/claims/cache behavior with
synthetic files, then decide separately whether probe writes can be enabled. Do
not combine sign-in, authenticated business approval and production publication
into one unreviewable change.
