# Delegated Microsoft Graph integration requirements — design only

No live authentication, HTTP client, token cache or Graph operation is implemented.
`storage/interface.py` defines list/download/create-only output contracts;
`GraphSharePointRepository` still rejects every operation before network access.
`FileSource.read(SourceFile)` supplies bytes to the GUI workflow, and the cleaning
coordinator remains independent of storage and Microsoft. Do not turn the disabled
stub into a connector by populating configuration. Separate user approval and IT
approval/test registration are required before implementation or live access.

## IT decisions and configuration

- Name an application owner, departmental data owner, finance reviewer and support
  owner. Approve an initial nonproduction site/library and test users first.
- Register a single-tenant organizational **public/native client** in Entra ID.
  IT must approve MSAL's supported system-browser redirect/loopback behavior and
  public-client settings. Package no client secret or certificate private key.
- Agree on delegated Graph permissions and consent. Evaluate selected-site/file
  permissions and explicit resource grants against the actual tenant/Graph API
  support. Do not assume Sites.Selected alone grants access or that every selected
  permission works with every delegated endpoint. The signed-in employee also
  needs independent access. Do not default to Files.ReadWrite.All or
  Sites.ReadWrite.All merely to make a test pass. IT must document the minimal
  scope/resource-grant combination actually tested for listing, reads and writes.
- Configure tenant/client ID, allowed authority/cloud, approved scopes, site/drive
  IDs and per-type raw/candidate/approved/log folder IDs. Resolve IDs through a
  separately approved discovery process; never hardcode a tenant/user path.
  IDs are nonsecret but may still be organization-sensitive: local settings only.
- Approve executable signing/distribution, proxy/network policy, MFA/conditional
  access, secure token cache, retention, diagnostics and one-operator/shared-lease
  policy. Test denied access, revoked consent, sign-out and account switching.

## Proposed adapters and operation contracts

| Boundary | Required behavior before connected implementation can ship |
|---|---|
| OrganizationalIdentity | MSAL public-client interactive system browser, PKCE through supported library flow; tenant/account display and confirmation; silent acquisition only as allowed by policy |
| TokenCache | Approved Windows DPAPI-backed cache with restricted ACLs, no plaintext refresh tokens; sign-out/cache purge and reauthentication; no credentials in logs/config/SharePoint |
| GraphFileSource | Store stable drive/item ID + ETag in the source reference; download the expected version into bytes/temp workspace; verify unchanged ETag/content identity before processing; no Graph URLs inside cleaners |
| ReportRepository.list_files | Approved folder only, all pagination, safe Graph-host/nextLink allowlist, explicit supported-extension filtering; no recursive archive discovery |
| ReportRepository.download | Bounded size/timeouts, safe authorized content redirects without leaking authorization to arbitrary hosts, expected ETag/version checks before/after download; surface changed/unavailable sources rather than guessing |
| ReportRepository.create_output | Create-only semantics, no automatic replace; verify returned identity/hash where supported, distinguish authorization/throttle/conflict errors |
| Future snapshot publisher | Separate business approval service/record; stage complete immutable approved set, verify every artifact, then conditionally select one pointer with expected ETag; keep old approved snapshots accessible |

The current `RemoteFile` includes item ID/name/size/ETag. A future immutable remote
source reference must also include drive ID and expected ETag/version rather than
reusing a filename as identity. Extend the interface with conditional pointer
selection/lease only when connected publishing is authorized; create_output alone
is insufficient to publish a multi-file month safely. Do not overload a local
correction token as an authenticated reviewer approval.

Use bounded retry/backoff for 429/503 respecting Retry-After, per-operation timeouts,
and cancellation between operations. Verify Graph response download URLs and expiry;
do not log preauthenticated URLs. Check permissions before write and after account
changes. Audit safe categories, stable IDs/hashes, row counts and review references;
never tokens, names, work-order descriptions or raw date cells by default.

## Concurrency and failure safety

A local SQLite lock protects one local store only. First connected pilot needs a
documented single operator or tested shared lease with expiration/recovery. Source
identity is drive/item/version/ETag plus SHA-256; output identity includes report
kind/month, cleaner/export/schema version and hash. Recheck expected state after
review and before pointer selection. Stale tokens/ETags stop the operation.

Do not claim Graph multi-file atomicity. Failed/partial uploads remain unselected;
conditional pointer selection happens only after all artifacts and approved audit
records exist. Retain immutable old snapshots outside the selected ingestion root.
Consumers read the approved pointer once per refresh and use that exact snapshot.
Follow `powerbi_output_design.md` for the proposed publication contract.

## Approval and acceptance gates

1. Explicit authorization to implement/test auth, with IT-owned registration and
   approved nonproduction locations; no production fallback when test access fails.
2. Synthetic mocked transport tests: pagination, wrong tenant/account, denied
   consent, expired tokens, ETag changes, 409/412 conflicts, 429/503/timeouts,
   upload interruption, stale lease and crash recovery; no network in unit tests.
3. Approved live **test-site** pilot: MFA/device policy, restricted users, secure
   cache/sign-out, readonly raw access, create-only candidate uploads, concurrency,
   recovery and independent cloud verification. A local sync observation is not
   evidence that Graph authentication or uploads work.
4. Business/financial/schema validation and signed publication policy; then separate
   approval for production destinations. No existing PR or prototype grants it.

## Milestone C/D follow-up — design only (2026-10-27)

Milestone A remains the implemented priority. Existing storage protocols/disabled
Graph stub were reviewed; no SDK, auth/cache, library-listing or upload implementation
is added here. Proposed next boundaries:

- LocalFolderSource reads explicitly selected local bytes; SyncedFolderSource reads
  only locally available/downloaded bytes and surfaces unavailable/permission errors.
  Neither claims cloud synchronization. Cleaning/history and SQLite remain on an
  independently confirmed trusted local disk, never the synced raw/candidate path.
- OrganizationalSession supports delegated organizational sign-in, tenant/account
  confirmation and expiry/sign-out. Its credentials/tokens belong only in an
  IT-approved protected cache. A future library-listing API returns opaque authorized
  drive/library IDs; it must not assume administrator visibility or access.
- GraphSource lists authorized direct month/type children with safe pagination,
  downloads the expected ETag/version, and verifies the source content hash. Separate
  proposed error categories include access denied, session expired, unavailable
  network, throttled, version conflict and integrity mismatch. They are not current
  implemented exception classes or evidence of connectivity.
- ApprovedSnapshotPublisher accepts an authenticated approval record bound to exact
  selected hashes/versions, stages create-only immutable output, verifies uploads,
  then conditionally selects one pointer under an approved shared lease. Do not
  assume Graph exposes SHA-256 for every drive; use an approved download-and-compare
  verification strategy where necessary. Interrupted uploads stay unselected.

### Proposed approval states and record

Raw source → cleaned candidate → financially reconciled candidate → business-approved
revision → published approved snapshot are distinct events, not edits to a CSV cell.
Reconciliation changes no ValidationStatus today. Future approval evidence must record
reviewer organizational identity/authority, UTC timestamp, selected revision/type/month,
source/output/summary hashes, cleaner/schema/map versions, counts, financial/business
comparison evidence, decision and scope. A correction requires fresh approval bound
to its exact hashes; a local replacement token is not reviewer authentication.
Publication also records destination identity/version, integrity verification and
selected-pointer ETag. Failed publication does not revoke or overwrite prior data.
No approval or publication service is implemented by this document.

### IT and release approval checklist

Every row is pending; record the accountable owner and approved evidence privately.

| Required decision/evidence | Gate |
|---|---|
| IT-owned native/public Entra app, supported redirect and organizational tenant scope | Before auth implementation/test |
| Tested least-privilege delegated Graph scopes plus explicit site/library resource grants | Before approved test access; no broad-scope fallback |
| Employee read/create permissions, consent/admin-consent requirements and conditional access/MFA behavior | Before authorized nonproduction pilot |
| Protected Windows token cache/ACLs, sign-out/revocation, retention and redacted diagnostics | Before distributing connected code |
| Exact authorized test site/drive/folder IDs and library-discovery policy | Local nonsecret config; never guessed production paths |
| Windows signing/distribution/endpoint policy, dependency ownership and named support backup | Before employee release |
| Power BI model/refresh owner, gateway/Service identity and test-workspace permissions | Before separately authorized publish/refresh |
| Shared concurrency, immutable snapshot retention, backup/restore and orphan/stale-pointer recovery drills | Before multi-operator publication |
| Business/finance/schema/model approval and production-specific authorization | Before any production destination/Power BI change |

Future offline mocks must exercise denied permission, expired sessions, pagination,
ETag conflicts, retries/timeouts/cancellation, interrupted transfers and uploaded-byte
verification. Real test-site, MFA, token-protection and Service refresh behavior need
separately authorized live tests; mocks or a readable OneDrive file cannot prove them.
Milestone D additionally needs a signed release/checksum, employee SOP/training,
second managed-PC acceptance, rollback drill and successor-maintainer handoff.
