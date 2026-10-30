# Microsoft 365 read-only connectivity pilot

## Evidence and scope — 2026-10-30

This feature starts from main **6b7e861**, the owner's merge of approval UX PR #16.
ff9cd36 and the earlier SharePoint/approval foundations are already ancestors: no
stack commits were replayed. The owner reports successful manual review/month/
duplicate/disabled-control testing and OneDrive-synced raw reads. Those are not
proof of direct Graph connectivity. Live PR metadata and Actions status remain
inaccessible through the environment's GitHub API proxy (HTTP 403).

**No approved tenant/client/test-resource configuration or written IT authorization
was supplied here. No real sign-in, browser flow, Microsoft discovery, Graph request,
upload or production access was attempted.** The official SDK was constructed only
with injected synthetic discovery responses; all graph/credential scenarios use
fakes. Ordinary desktop startup remains local/offline.

| Capability | Implemented | Actual live test |
|---|---|---|
| MSAL public client | Official msal 1.34.0, tenant-bound factory, system-browser/PKCE SDK flow, account/subject checks | No; SDK construction tested with mocked metadata |
| Session lifecycle | Silent renewal boundary, explicit interactive recovery, bounded claims challenges, local sign-out | No actual MFA, consent, CA or account sign-in |
| Protected cache | Dedicated tenant/client DPAPI cache, exclusive whole-session lease, encrypted empty-cache sign-out | Linux uses injected test protector/fail-closed default; native Windows coverage needs hosted results |
| HTTPS | requests 2.32.5, TLS verification, connect/read timeouts, streaming size bounds, exact hosts/no automatic redirects | Mock HTTP only |
| Test resources | One configured site/library, three direct raw folders, known synthetic item IDs/SHA-256 allowlist | No site/library permission verified |
| Downloads → engine | Same real M1/financial-v2 bytes API, preview/re-read/process, original-byte/provenance bundles | Synthetic CSV/XLSX through mock Graph |
| Desktop | Offline configuration check and Guided Mode; Graph/sign-in/Approve/Publish remain disabled | No connected account/site/file picker |
| Windows executable | Bundles SDK/HTTP/CA roots; separate offline component check plus existing GUI smoke | Must inspect exact-head hosted Windows result |

No cleaners/calculations, financial schema v2, review-request fingerprints/audit,
processing SQLite, Power Query, business approval state or production PBIX changes.
Reviewer identity/roles remain unavailable. This is an operator/API test-pilot
foundation; connected employee GUI activation follows separately after live evidence.

## Components and gates

The optional **microsoft** extra pins official MSAL and requests; uv.lock pins all
resolved artifacts. Default engine/GUI use does not import or construct an OAuth
client. New modules:

- m365_config.py: strict offline TOML validation and local-storage checks.
- auth/managed_msal.py: gated official SDK factory, session/cache/claims lifecycle.
- storage/https_transport.py: constrained Graph and Microsoft authority HTTP clients.
- storage/readonly_graph.py: read-only profile of the existing adapter. Every write/
  probe/output method is rejected before token acquisition; HTTPS also rejects writes.
- m365_pilot.py: scoped resource verification, synthetic listing/download bridge,
  preview/process operator commands and immutable local origin receipts.
- m365_components.py: installed/packaged imports and CA-root checks, never OAuth.

The real factory requires **all** of: complete valid configuration, enabled=true,
nonproduction environment, a nonempty IT authorization reference, and an explicit
operator-authorized call/CLI flag. No default file is loaded at startup. Inspecting
configuration or using Settings' Check Microsoft 365 test configuration does not
instantiate MSAL, create caches, sign in or contact Graph, even if enabled=true.

These are operator/configuration gates, **not cryptographic verification of IT
approval**. The application cannot independently classify an arbitrary SharePoint
site as production/nonproduction. IT must supply/protect the exact configuration,
restrict resource grants and authorize users. A typed reference/flag grants no
business approval and is not permission to ignore these prerequisites.

## Identity and credential handling

MSAL PublicClientApplication uses the configured tenant GUID authority at
https://login.microsoftonline.com, never common/consumers or a guessed tenant. No
client secret/credential, password collection or device-code fallback is implemented.
The native system-browser flow uses MSAL's PKCE/loopback handling with an explicit
account prompt and 120-second interaction timeout. MSAL supplies its reserved
openid/profile/offline_access scopes; Graph scopes are the configured selected-
resource scopes only. No broader Graph scope is requested on failure.

The result must match the tenant and contain a valid organizational object ID;
interactive account selection is bound to the matching SDK account. Token values
are repr-hidden. Expiry, denied consent, wrong tenant, malformed results and claims
challenges fail safely. Graph 401 invalidates in-memory access; a validated bounded
claims challenge is forwarded only on the next **explicit** interactive action,
not an automatic browser launch/retry. CP1 is advertised for claims handling.

A Graph-issued challenge stops the current CLI action safely; explicit recovery
using the retained session/API forwards its pending claims. The CLI does not loop
or automatically launch another browser, and a desktop recovery UI is not shipped.

MFA/conditional access remains controlled by Entra and the approved browser/device.
Broker integration is explicitly disabled in this profile. If tenant policy requires
an unsupported broker/device flow, stop and involve IT: never weaken policy, collect
passwords or broaden permissions. Actual policy/claims behavior is unverified.
Successful organizational sign-in is not verified reviewer role or business approval.

Cache path must end in **<tenant-guid>/<client-guid>/msal-cache.bin** on trusted local
fixed storage outside OneDrive, shared paths or redirected folders. The existing
Windows current-user DPAPI protector persists official SerializableTokenCache data;
there is no plaintext fallback or default Linux credential persistence. Runtime
Linux live bootstrap fails closed; Linux offline tests inject a fake protector.
IT must verify NTFS ACLs, user/device/backup/retention/sign-out policy on Windows.

An in-process reentrant lock serializes refresh, challenge, sign-in and sign-out
so a concurrent refresh cannot repopulate credentials after purge. Already-issued
tokens/in-flight reads are not revoked by local sign-out; a future connected UI
must drain its worker before logout.

An exclusive .session.lock is held for the whole connection to prevent stale
multi-process cache overwrites/resurrection. It is separate from the atomic per-
write cache lock. No stale lock is automatically deleted. Closing retains the
protected cache for a future authorized session; sign_out removes SDK accounts,
invalidates memory and writes an encrypted empty cache before releasing the lease.
This is **local app sign-out**, not browser SSO logout, account-wide token revocation
or logout on another device. A failed purge reports sign-out incomplete; do not
claim success. After a crash, IT must establish that no process owns the dedicated
cache and review recovery before removing a stale lease. Never upload cache blobs.

## HTTP, resource and byte integrity

Graph requests are GET-only, exact graph.microsoft.com/v1.0 routes and configured
exact SharePoint download hosts. No userinfo, fragments, explicit ports, wildcard
hosts or TLS bypass. Requests uses verified TLS, 10-second connect/30-second socket
read timeouts (not a guaranteed overall wall-clock deadline), and a 64 MiB decoded
body cap. Identity-encoded Content-Length mismatches and interrupted streams fail; decoded
file lengths/hashes are separately checked against metadata and the synthetic manifest. Automatic
redirects are disabled; the adapter permits one exact-allowlisted HTTPS content
redirect with **no bearer/application headers** sent to that host. .netrc auth is
suppressed; approved enterprise environment proxy/CA settings remain supported.

Authority GET/POST is restricted to login.microsoftonline.com, the configured tenant
path and validated authority endpoints, with bounded JSON bodies and no redirects.
OAuth POST is not a SharePoint upload. SDK/requests/urllib3 wire logs are suppressed;
application diagnostics expose category/status only, never signed URLs, headers,
claims, tokens, raw SDK error descriptions or file contents. Browser/proxy/OS logs
are separately governed by IT. Do not enable external wire tracing during the pilot.

The existing Graph adapter retains pagination validation, bounded GET retries and
Retry-After handling: long waits are deferred rather than shortened. No write retry
or permission fallback exists. Site identity, configured drive membership in that
site and each folder's drive/identity are verified before listing. Redirected folder
items are rejected. Only direct files with IT-allowlisted item IDs, matching report
types and CSV/XLSX suffixes are offered; historical folders are not traversed.
Unknown files are not offered. Legacy XLS is not enabled.

Downloads check captured drive/parent/item/name/size/ETag before and after content,
expected synthetic SHA-256 and any actual Graph SHA-256. QuickXor/SHA-1 is not treated
as SHA-256. The verified bytes are passed unchanged into DesktopWorkflow and the
same coordinator/cleaners. Processing re-downloads/rechecks; changed versions/hashes
fail rather than silently processing a new file after preview. Period validation,
exclusions, counts, date parsing, costs and correction mechanisms remain unchanged.

Preview creates no candidate history/output (explicit authentication may update its
protected cache). Successful/skipped processing preserves exact original bytes as
original.bin plus a private receipt under the local candidate root's m365_downloads/.
The receipt binds Graph identity/version, download/source hash, candidate revision/
output hash and an explicit not-granted approval state. Immutable deterministic
bundles deduplicate repeats and reject corruption; they are not ingestion folders.
No signed URL or Microsoft credential is included. Keep these private. A receipt
write failure can occur **after** the coordinator saved a candidate: inspect local
history, keep prior artifacts and resolve the diagnostic; do not claim full origin
capture or automatically roll back/edit SQLite. Filesystem/SQLite/remote reads are
not a multi-system atomic transaction.

## Required Entra / IT setup — STOP until authorized

1. Obtain written authorization naming the accountable data/IT owners, authorized
   tester/device, exact **nonproduction** tenant/client/site/library/folders, read-only
   operations, synthetic files, scopes/resource grants, dates and evidence policy.
   This document and a successful offline check are not that authorization.
2. IT registers/owns a single-tenant native/public client, approved redirect
   **http://localhost** and system-browser/loopback policy. No desktop client secret.
   Confirm broker/conditional-access compatibility; unsupported policy stops pilot.
3. This profile supports the public/global Microsoft cloud only; sovereign cloud
   authorities are unsupported and must not be substituted automatically.
   Approve least-privilege delegated selected-resource Graph consent **and READ grants
   on the test resource**, plus the user's own SharePoint rights. Sites.Selected is
   the initial profile; selected file/list alternatives may not authorize site/drive
   metadata verification. Test actual endpoint feasibility. Never fall back to
   Sites.Read.All, Files.Read.All or any ReadWrite permission to make it work.
4. IT prepares an isolated test library and three direct raw-report folders, using
   its approved tooling to place **synthetic files only**. The application uploads
   nothing. Record site/drive/folder/item IDs and independent original SHA-256s.
   Never substitute a production library if the test site is unavailable.
5. Approve exact signed-download hostnames, enterprise proxy/CA rules, local cache/
   candidate roots and ACLs, protected-cache/lease recovery and retention. Do not
   disable endpoint protection, TLS verification, MFA or conditional access.
6. Approve the pinned dependencies and executable/signing/distribution/device policy.
   Reviewer/approval roles, production publishing and Power BI refresh remain out
   of scope and unconfigured.

## Configuration and offline rehearsal

From the actual cloned repository (not an extracted Downloads ZIP), close old app
instances and use the new feature branch:

```powershell
git fetch origin
git switch feature/m365-readonly-connectivity
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv run --frozen --all-extras python -m equipment_data_manager.m365_components --output data/m365-components.json
python -m uv run --frozen python examples/create_powerbi_pilot.py --repair-financial-v2 --complete-financial-example --output data/m365-synthetic-fixtures
Copy-Item m365-test.example.toml m365-test.local.toml
```

Choose new output destinations outside all production ingestion/reserved-approved
folders. Never point --output-root at a production Power BI folder. The template is intentionally incomplete/disabled. The earlier graph.example.toml
was a design-only template and is not compatible with this runtime schema.
IT fills real configuration privately: tenant/client GUIDs, exact test IDs, raw folder
IDs in fixed repairs/service_orders/tma_work_orders order, exact download hosts and
one synthetic_files entry per known test item ID/report type/lowercase SHA-256.
PowerShell Get-FileHash returns uppercase; use .Hash.ToLowerInvariant() for the TOML.
Keep enabled=false until actual IT authorization. The cache path is an actual
absolute LOCAL path ending <tenant>/<client>/msal-cache.bin, not a literal environment
variable or an unexpanded placeholder. Use forward slashes or TOML literal strings
for Windows paths. Actual config/IDs/receipts remain private and ignored.

Offline configuration inspection (even a complete enabled config is not contacted):

```powershell
python -m uv run --frozen --all-extras python -m equipment_data_manager.m365_pilot inspect --config m365-test.local.toml
```

The JSON must say network_contacted=false and authorization_verified=false.
Settings → Check Microsoft 365 test configuration does only the same offline
validation. Graph and reviewer sign-in/Approve/Publish remain disabled in the desktop.
No account/site/library live picker or role verification is shipped here.

## Manual live pilot — only AFTER the above written authorization

IT enables the private config and an authorized operator explicitly supplies
--it-authorized-test-only. **The following commands can contact Microsoft and open
a browser; they were NOT run in this development environment.**

```powershell
python -m uv run --frozen --all-extras python -m equipment_data_manager.m365_pilot list --config m365-test.local.toml --it-authorized-test-only --output-root data/m365-test-candidates --report-type service_orders --sign-out-after
```

Verify the intended work account/tenant during the browser flow and obey MFA/device
policy. Only approved test metadata should appear. Choose an allowed synthetic item
ID from the listing, then use its confirmed source month (example January 2026):

```powershell
python -m uv run --frozen --all-extras python -m equipment_data_manager.m365_pilot preview --config m365-test.local.toml --it-authorized-test-only --output-root data/m365-test-candidates --report-type service_orders --item-id SYNTHETIC_ITEM_ID --month 2026-01 --sign-out-after
python -m uv run --frozen --all-extras python -m equipment_data_manager.m365_pilot process --config m365-test.local.toml --it-authorized-test-only --output-root data/m365-test-candidates --report-type service_orders --item-id SYNTHETIC_ITEM_ID --month 2026-01 --sign-out-after
```

Repeat with repairs and tma_work_orders using their authorized synthetic IDs and
months. These commands create **local CandidateUnverified outputs only**; no cloud
write/publication/approval/Power BI operation exists. Confirm source originals and
hashes remain unchanged. Repeating identical input should skip without new candidate
revisions or duplicate origin bundles. A changed item needs fresh capture and any
new synthetic hash approved in IT config. Existing month corrections stop for the
normal bound review token; do not auto-acknowledge a correction. The API preserves
the existing explicit correction mechanism; connected employee correction UI is
not part of this milestone. Microsoft token values are never printed.

CLI actions deliberately perform explicit interactive sign-in per run. Silent token
renewal is supported inside an authorized session; cache restart tests use the API.
Without --sign-out-after, close retains encrypted cache; test that lifecycle only
under IT's cache policy. With the flag, local purge success must be distinguished
from browser SSO/account-wide revocation. A connection/metadata success does not
prove download integrity until the expected synthetic hash and version checks pass.

### Authorized failure and acceptance matrix

Record actual tester/date, commit/executable hash, MSAL/requests/device versions,
approved resource IDs/scopes/grants and redacted outcomes **privately**:

- Explicit sign-in, MFA/CA success; denied consent, unauthorized user/wrong tenant,
  cancelled/timed-out browser, expired token and real claims challenge behavior.
- Allowed site/library/folders; rejected wrong drive/folder/remote reference and
  permission loss. No broader scope or production fallback.
- List pagination/direct-only behavior; unknown/non-synthetic items not offered.
- Synthetic download independent SHA, before/after ETag, byte count, UTF-8 BOM/text
  identifiers, unchanged XLSX bytes and same real-engine preview/process results.
- Source change during transfer/between preview/process; interrupted/oversize/partial
  reads; 429/503 Retry-After; redirect allowlist and absence of bearer on content host.
- Cache restart/expiry, local sign-out, failed purge, stale lease recovery, two local
  instances and appropriate NTFS/device protections. No secrets in logs or GitHub.
- Local candidate/revision/origin preservation, repeat skips, explicit corrections,
  errors without approved outputs or remote mutations.

Stop on any unexpected resource, permission, policy, integrity, cache or provenance
failure. Preserve category-only diagnostics and existing artifacts; never broaden
scopes, disable security, overwrite data or report the pilot successful to proceed.
Only actual authorized results can establish live-tested status. After that review,
propose a small connected desktop read-only UI milestone; business approval,
publication and production remain separately gated.

## Recorded local validation

589 tests passed with zero failures/errors/skips on Linux, preserving the 533 prior
cases plus 55 new backend cases and one real-widget case. Actual official MSAL
construction used only mocked discovery metadata. These are not live Microsoft
results. Read testing.md for installed/packaged evidence and hosted-CI limitations.
