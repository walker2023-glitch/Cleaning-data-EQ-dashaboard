# Milestone C — storage and offline Graph connectivity foundation

This branch implements the bounded foundation requested for Milestone C. No
credentials, live sign-in, SharePoint HTTP calls, candidate uploads, publication,
approval changes or production PBIX/refresh are performed. Default application
startup still uses local file reads; Graph remains unavailable in Settings and
the original GraphSharePointRepository fails closed.

## What actually works

| Area | Implemented/testable now | Still requires separate work or evidence |
|---|---|---|
| Local / SharePoint-synced raw files | Read-only provider, stable before/after identity/length checks, known Windows offline/recall detection, SHA-256, explicit folder discovery; GUI file reads use the same stable reader | Export-complete/operator handoff and actual OneDrive/device testing; local checks cannot prove cloud currency/completion |
| Provider boundary | StorageFile identities include provider/container/parent/item/version, FileRead bytes/hash/integrity; ProviderFileSource bridges to the existing engine | Live Graph browser/selection UI and actual remote source references persisted across sessions |
| Graph operations | Scoped site/library metadata, paged direct-folder listing, version/size/hash checked downloads through an injected transport | **Only fake transport responses tested**; no HTTP implementation or live endpoint verification ships |
| Organizational authentication | MSAL PublicClientApplication-compatible injected session, tenant/account checks, explicit interactive gate, expiry/permission handling | **Fake MSAL client tested**; MSAL package/client construction, protected-cache lifecycle/sign-out, redirects/claims challenges and interactive UI are not wired |
| Protected cache | Windows current-user DPAPI implementation, atomic ciphertext writes, exclusive writer lock, no plaintext staging, dirty-state recovery | Native DPAPI roundtrip is exercised by Windows tests; actual MSAL cache/ACL/retention/enterprise-device validation remains a live-pilot gate |
| Optional upload | Fixed **synthetic .txt probe only**, create-only request, no automatic PUT retry, read-back integrity verification and explicit unknown-outcome recovery | Probe request conflict semantics/redirect hosts and server behavior require an approved nonproduction pilot; no general candidate/approved-output uploader exists |
| Settings / Guided Mode | Existing Browse supports local/downloaded synced raw paths; truthful status and disabled Graph control with contextual help | A full three-mode selector, site/library chooser and Microsoft account controls remain proposed, not functional |
| Approval / Power BI | Existing repair schema v2, four separate datasets, explicit months, packets and snapshot integrity unchanged | Authenticated business approval, approved snapshot publisher/pointer and production refresh remain unimplemented |

The source adapter does not clean. It returns bytes plus provenance to the unchanged
coordinator; preview hashes and correction tokens still guard processing. Downloads
are verified in memory, so an interrupted transfer never becomes a selected local
candidate. No basename-only identity or business-record deduplication is introduced.

## Mode A: local or OneDrive-synchronized raw folders

1. In Settings choose the **Raw Data Folder** with Browse. It may be a local folder
   or an authorized locally available SharePoint library synced through OneDrive.
   Use the existing year-month/report-type layout; direct files only, no recursive
   historical revision ingestion. Inventory is not a fourth monthly requirement.
2. Keep **Candidate Output Folder**, review packets/snapshots and SQLite on trusted
   local disk outside OneDrive/SharePoint/shared folders. The existing local-storage
   confirmation/policy remains mandatory. The approved location stays reserved;
   selecting it does not approve or publish anything.
3. Finish the source export/copy. In OneDrive make required reports available on
   this device and wait for downloads to finish using your organization's normal
   procedure. The app does not request hydration or query the sync service.
4. Preview. Known Windows OFFLINE, RECALL_ON_OPEN and RECALL_ON_DATA_ACCESS files
   are stopped **before open**. Missing/denied files produce safe errors. A short
   read or changed identity/size/timestamps stops processing. A stable read proves
   only the bytes read locally: the file may still be an unfinished producer export
   or differ from the cloud. Report layout/count/period validation still runs.
5. Review results, process and export packets locally. Original reports are never
   moved or changed. If a file changes between preview and processing, preview again.
   Compare original-source hashes in the existing readiness assessment as needed;
   neither a hash match nor a local Ready indicator verifies OneDrive synchronization.

No new settings-file version/migration is introduced. Both local/synced raw folders
use the same read semantics, so Browse selects their location without a misleading
connected-mode switch. Graph and publication remain disabled even after Save/Reset.

## Offline developer preview (no credentials/network)

Use the cloned repository, not an extracted executable ZIP:

```powershell
cd C:\path\to\Cleaning-data-EQ-dashaboard
git switch feature/sharepoint-connectivity-foundation
python -m uv sync --frozen --all-extras
python -m uv run --frozen pytest tests/test_storage_providers.py tests/test_graph_adapter.py tests/test_msal_foundation.py
python -m uv run --frozen python examples/sharepoint_foundation_demo.py
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app
```

The demo uses an in-memory transport, a synthetic MSAL-compatible client and the
bundled synthetic Service Orders CSV. It previews through the real engine, prints
mock_graph/live_authentication=false/publication_enabled=false and writes no outputs.
It is not proof of an MSAL sign-in, Graph connectivity, synchronization or Windows
enterprise policy. An actual SDK is not installed/initialized by this milestone.

## Adapter/module map and recovery

- storage/contracts.py: read-provider/file/result contracts and category-only errors.
- storage/local.py: root-confined local/synced provider and stable local byte reader.
- storage/discovery.py: explicit three-type folder mapping, no recursive traversal.
- storage/source.py: captured provider identities through the existing FileSource API.
- storage/graph_adapter.py: OfflineGraphAdapter, GraphScope, injected transport response
  contract. No HTTP client is supplied; constructing this with a fake cannot go online.
- auth/msal_session.py: injected public-client session behavior, no authority discovery,
  real credentials, username/password collection or client secret.
- auth/token_cache.py: ciphertext-only protected serialization. Load into a real
  MSAL SerializableTokenCache before client construction, persist after SDK changes
  and wire sign-out/cache purge **in the later authorized bootstrap**.

GET requests have bounded attempts/timeouts and respect Retry-After. If the server
requests a wait beyond the configured budget, the adapter defers instead of retrying
early. 401/403/404/conflicts stop with safe categories. Pagination must stay on the
same Graph endpoint/host and cannot loop or repeat item identities. Folder IDs are
explicit scope, not guessed tenant paths; child folders/history are not recursed.
Metadata must retain the selected drive/parent/name/size/ETag before and after download.
If no expected/server SHA-256 exists, the result says hash computed/version checked,
not an independently matched source hash. Graph may expose only quickXorHash; it is
not treated as SHA-256.

HTTP transport MUST enforce TLS verification, bounded response sizes/timeouts,
redacted diagnostics and **no automatic redirects**. Content redirects need exact
IT-approved hosts, HTTPS and a separate request without the bearer token. Signed
content URLs must never be logged. An expired content link is distinct from an
expired organizational session. These rules are mock-tested; the transport itself
is still absent.

The probe upload method accepts a safe .txt name and the constant synthetic body;
it accepts no arbitrary CSV content. Its configured probe folder must be a separate
nonproduction folder, never a raw folder or approved production destination. Requests
ask for conflictBehavior=fail and If-None-Match=*. Real server enforcement is a
mandatory live-pilot check, not proven by a mock. A conflict stops without rename
or overwrite. An interrupted PUT has unknown outcome and is never retried blindly.
List the probe folder explicitly and verify the identified probe's version/hash;
if contents differ, stop for investigation. The adapter never deletes an uncertain
remote file or marks an upload published. create_output always rejects publication.

Protected cache defaults to Windows user DPAPI; non-Windows default protection
fails closed, with no plaintext fallback. Test protectors are test-only. No cache
is created at app startup. Choose a trusted per-user local cache directory with
IT-validated NTFS ACLs, backup/retention and sign-out policy; never sync it. Writes
recheck local path policy, encrypt in memory, stage ciphertext then replace atomically.
Serialization/write failure leaves the prior blob and dirty state for retry. A lock
left by a crashed writer requires reviewed recovery after confirming no process owns
it; there is no automatic stale-lock deletion. No PII/raw SDK errors/tokens are logged.

## Settings proposal for the next connected PR

Keep the current implemented card until authorized integration is ready. The next
proposed selector has Local files / Synced raw folder / Microsoft Graph (disabled
until configured/tested). Local and synced modes share the existing private folder
settings. Graph should show organizational account/tenant, exact selected test site/
library, raw mappings, separate nonproduction probe destination, and token/session
state only after actual verification. Never label Connected from saved IDs alone.
Candidate/SQLite stays local in every mode; approved publication stays separately
disabled. Endpoint/tenant/proxy/device errors need contextual help and explicit
reauthentication, not broader permission fallback or embedded credentials.

See sharepoint_live_pilot.md for the IT checklist, proposed approved folder layout,
approval evidence, test steps and next-PR boundary.
