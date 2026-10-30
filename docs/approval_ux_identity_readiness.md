# Approval UX and identity readiness

## Branch and evidence

feature/approval-ux-identity-readiness starts from main a01ebb5, the owner's merge
of PR #15. The approval-publishing-foundation head c32d820 is already an ancestor;
no feature commits were replayed or merged again. Git fetch/ref history confirms
this. GitHub PR-list and Actions API access still return proxy HTTP 403, so current
open PR metadata, review status and hosted checks cannot be inferred from Git.
No PR is automatically merged or retargeted.

This milestone changes presentation, reporting-period preferences and a disabled
identity interface. It does not change cleaning, financial v2, candidate CSVs,
review-request format/fingerprints, publication model, processing SQLite or business
approval states. No production SharePoint, Graph authentication or Power BI is used.

## Why January could become October

The application created month/year variables from today's calendar date at each
launch. Settings version 1 stored folder/help/output preferences but no reporting
period. The review page read the shared variables while hiding their controls on
Process Reports. In October a new process therefore reviewed October unless January
was selected again. Source inspection found no month reset in ordinary page
navigation; tests now prove navigation preserves the shared month.

Both pages now expose the **same month/year selection**. Review shows an explicit
YYYY-MM caption and invalidates old evidence when the month changes. Changing it
never infers a month from filenames and never bypasses engine period validation.

## Month persistence policy

- A new profile without a remembered period starts at the current calendar month,
  visibly displayed. No candidate month, filename or last-success guess is used.
- Once Settings exists, valid month/year changes are saved through the existing
  serialized background preferences worker. Saving folder Settings also captures
  the current valid period. First-run selection alone creates no directory/file:
  explicitly save setup before expecting persistence.
- Settings version **2** adds preferences.reporting_period as blank or YYYY-MM.
  Version-1 settings and legacy three-folder workspace imports still load without
  losing choices. They gain a period only when valid preferences are next saved.
  Unknown keys/versions and invalid periods still fail strictly.
- Navigation, folder checks and help changes do not substitute the calendar month.
  An explicit user choice made during asynchronous startup wins over a saved month.
- Incomplete/invalid year edits never replace the last valid saved period. Failed
  preference writes keep the old file, show a session-only message, and preserve
  the current session choice. Unreadable settings are retained instead of overwritten.
- Close waits for the latest pending preference write without prompting solely for
  that save. This is not a durability guarantee against power loss or force-kill.
- Processing confirmation and previews are **not** persisted. Confirm the source
  month and preview again before processing after restart.
- Load synthetic sample deliberately selects its documented sample month. Reset
  Settings clears the remembered period along with the other preferences; the
  current session selection remains until changed, and a later fresh profile falls
  back to calendar month. Imports are drafts, not automatic month changes.

The v2 preference file is not understood by older builds that only support v1.
Keep a private backup of settings before using an older executable; restore the
matching backup in a reviewed rollback. Do not edit candidate databases/outputs to
resolve a preference-version mismatch. No data-store migration is performed.

## Employee review layout

Select **Review & Approval** and check its month/year caption, then **Review candidate**.
The default tab is Overview; JSON is confined to the optional Technical details tab.

| Section | What it shows |
|---|---|
| Overview | Required report counts and missing types; labeled monthly source-reported costs/counts and financial arithmetic status |
| Issues | Plain-language engine warnings and per-column missing-value counts |
| Revisions | Exact selected revision IDs, source/output/summary hashes, schema/cleaner versions and original-byte checks |
| Review history | Every local request for this month, request ID, local-clock UTC time, unverified note and current/stale status |
| Technical details | Original structured evidence, exact warning codes, source hashes and local statuses for maintainers |

Display currency formatting does not alter stored values or calculations. Not supplied
is not $0.00. Known individual totals may be partial; monthly summary grain is not
expanded onto individual repairs. Original descriptions/IDs/dates and CSV schemas
remain untouched. Source/financial validation stays in the existing review service.

Add a concise evidence reference and click **Request approval (local)**. Requests
are still local and unsent; repeat identical requests reuse one durable record.
History now remains complete after recording another note rather than showing only
the newest request. Corrections/source changes retain the existing stale detection;
refresh before requesting review. No local user statement becomes approval.

## Status terminology and truthfulness

| Label | Evidence required to achieve it | Current presentation |
|---|---|---|
| Review Requested Locally | Matching durable local request for current evidence | Recorded here — not sent, or not recorded for current evidence |
| Approval Pending | Verified submission/receipt from an authorized approval service | Not submitted to an approval service |
| Approved | Authoritative reviewer decision bound to exact revisions/final hashes | No authoritative approval evidence |
| Published | Verified immutable snapshot and authoritative selected-pointer evidence | Unavailable — publishing disabled |

Stale requests cannot make the first stage current. Forged/local status strings
such as Approved, Published or ApprovalPending cannot advance the later cards.
No receipt ingestion or business-state transition is implemented. The application
cannot assert whether independently managed remote publications exist. Publication
history remains unavailable until an authorized service exists.

The Entra sign-in, Approve and Publish buttons remain disabled, including after
busy/error recovery. ReviewService.approve/publish still fail closed. There is no
checkbox, typed identity or preference that can activate them. Guided Mode/F1 now
explains month restoration, evidence sections, local/remote status distinctions,
identity versus authorization, and why controls remain unavailable.

## Future reviewer identity architecture

New auth/reviewer_identity.py defines ReviewerIdentityProvider, IdentityReadiness
and ReviewerVerification contracts. UnavailableReviewerIdentity is the only provider
wired into the desktop. It returns not_configured/not_verified and refuses sign-in
and reviewer verification. It creates no SDK client, browser, HTTP request, token or
cache. Merely constructing a verification object cannot authorize an approval.
The prior injected MSAL/storage foundation remains unchanged.

A future Entra adapter and independent authorization service need a separately
reviewed implementation and IT-approved nonproduction pilot:

1. Authenticate the immutable organizational tenant/subject through the approved
   public-client SDK flow. Validate trusted issuer/audience/tenant/session claims;
   honor MFA, device/conditional access and organizational account selection. A
   display name, email string or client-editable claim object is insufficient.
2. Independently verify authorized reviewer role/resource scope under a versioned
   departmental policy, including separation of duties, revocation and expiry.
   Signing in successfully does not grant approval authority or SharePoint write.
3. Bind trusted service evidence to the exact month, action and candidate selection
   fingerprint, policy version and authority evidence reference. Check current
   selection, permissions and trusted expiry at decision and publication time.
4. Keep identity evidence distinct from a business decision. Approval Pending needs
   a real submission receipt; Approved needs a validated authoritative decision;
   Published needs an independently verified immutable output/selection record.
   A dataclass, mock grant or local hash is never sufficient proof.
5. Use approved protected cache/sign-out/ACL/retention and redacted diagnostics.
   No tokens, roles, secrets or identity assertions belong in ordinary Settings.
   Any future authoritative assertion must be independently validated, including
   signature/issuer/audience, rather than trusting client-side fields.

No live provider, role lookup, receipt/status connector, approval, publisher or
production Power BI refresh is added here. Required decisions: Entra registration/
redirect/scopes, reviewer/policy owner, authoritative role service, test resources,
claims/revocation/evidence handling, permission lifecycle and managed-PC acceptance.
See sharepoint_live_pilot.md and approval_publishing_foundation.md.

## VS Code preview

Close older app instances and use the actual Git clone rather than a downloaded ZIP:

```powershell
git fetch origin
git switch feature/approval-ux-identity-readiness
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv run --frozen python examples/create_powerbi_pilot.py --repair-financial-v2 --complete-financial-example --output data/approval-ux-demo
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app --settings-file data/approval-ux-preview/settings.toml
```

Use a new demo destination. In Settings choose that demo's raw/candidates folders
and a separate reserved approved folder; confirm trusted local candidate storage,
then Save Settings. Keep candidate history/requests outside sync services. Select
January 2026, open Review & Approval and refresh. Review all five tabs. Record a
synthetic local request twice and confirm one record, no remote-pending/approved/
published achievement, and disabled sign-in/Approve/Publish. Choose February directly
on this screen; old evidence is cleared. Refresh to load February, then return to
January and navigate Help/Settings/History; January must remain selected.

Close normally and relaunch using the **same settings-file**: January returns but
month confirmation is unchecked. A different settings file is a different profile.
An extracted old executable ZIP does not update when a Git branch changes. Use only
an exact-commit successful Windows build for employee review; no Python/Git/VS Code
is needed for the extracted packaged app. Preserve private settings/candidates when
switching builds and do not commit actual reports, notes or identities.

## Validation scope

Tests cover fixed-October January navigation/restart, shared selectors, pending
startup/save/close races, incomplete years, version-1 compatibility and strict v2
validation, readable sections, nullable/zero money, full technical hashes, duplicate
requests, missing reports, stale records and permanently disabled controls. Identity
contracts are tested offline and cannot authorize business approval. The actual-
window/executable smoke checks the overview, disabled identity controls and fresh-
process January restoration without restoring confirmation.

Full-suite and distribution results are recorded in testing.md. Windows/Linux CI
and Windows packaging/smoke are configured on this feature branch's pushes, PRs and
manual dispatch. Hosted results must be observed separately; API HTTP 403 remains
a blocker to reading checks or creating a PR from this environment. Workflow YAML
or a passing Linux source test is not Windows executable evidence.
