# Power BI CSV candidate exports — schema v1

## Microsoft 365 read-only foundation (not live verified)

Adds an optional pinned official MSAL/requests integration, tenant-bound authorized-
test bootstrap, protected-cache lifecycle, constrained read-only HTTPS/Graph and
synthetic-hash allowlists. Verified bytes feed existing cleaners; processing keeps
local original/provenance bundles. Settings can check test config offline. The
packaged component check verifies SDK/HTTP/CA availability without OAuth/network.

Local suite: 589 passed. No real Microsoft authentication, Graph request or live
conditional-access/permissions test was performed. Desktop live controls and all
reviewer approval/publication remain unavailable. Written IT test authorization and
configuration, actual nonproduction pilot and exact-head Windows build are required.
No production data, calculations, financial v2/schema or review-state changes.
See m365_readonly_pilot.md. Version remains prototype 0.2.0; identify by commit/hash.

## Approval UX and identity readiness (review prototype)

Reporting month is now visible/shared across processing and review and remembered
after setup via backward-readable settings v2. Restart restores the month but never
confirmation or old previews. Review defaults to labeled overview/issues/revisions/
history tabs; structured evidence remains in Technical details. Status cards never
infer remote pending/approved/published outcomes from local requests. The default
Entra reviewer interface refuses sign-in and verification; Approve/Publish stay
disabled. No cleaning, financial, request-record or business-state changes.

Local suite: 533 passed; source/installed-wheel phase-26 GUI and fresh-process
January restore passed. Hosted Windows/Linux and executable outcomes remain
unverified. Identify prototype 0.2.0 builds by exact commit and ZIP hash; old ZIPs do
not update with a Git checkout. See approval_ux_identity_readiness.md.

## Approval / publishing foundation (review prototype)

Adds monthly review evidence and exact revision/hash binding, local unsent request
history with stale detection, and Review & Approval Guided Mode. Final approval
and Publish stay disabled without authoritative reviewer verification. A separate
in-memory specification model exercises future staging/integrity/concurrency/recovery/
rollback with synthetic grants only. No cleaning/schema/processing-store changes
or production writes. Local full suite: 508 passed; source/installed-wheel phase-26
smoke and restart passed. Hosted Windows/Linux and Windows executable status remains
unverified due API access; require exact-commit checks before employee distribution.
See approval_publishing_foundation.md. Version remains 0.2.0 prototype; identify
review builds by branch/commit and ZIP checksum, not the reused artifact name.

Adds an opt-in GUI/CLI export layer after the existing cleaners: header-first
Repair History/Service Orders/TMA tables, ISO dates, numeric contracts, text IDs,
ReportMonth, provenance and raw description/status/tag fields. It creates separate
unapproved normalized candidate revisions; legacy mode/bytes remain available.
Missing/invalid parts and related totals are blank in normalized business fields,
while explicit Legacy columns retain the unchanged calculated values. No formula,
date, exclusion, source script or financial meaning is silently changed.

Original preambles are omitted only by the separate exporter. Unknown candidate
schemas fail; extra raw fields outside the normalized contract produce a warning.
Unicode is UTF-8; consumers must apply explicit encoding and identifier types.
Repeated report totals remain metrics, never per-transaction numeric columns.
Production publication is blocked and no approved-current folder is created.
Maintenance matching/classification is a future design only. No Graph, Microsoft
authentication, production SharePoint or Power BI modifications are included.

# Multi-month compatibility follow-up

Adds strict 14-column repair summary/count checks and financial-review warnings,
service status-fallback diagnostics, and a specific local TMA XLSX adapter using
the original requests transform/writer. TMA candidates retain its five columns,
title and MM/DD/YYYY dates. openpyxl is now a required pinned dependency; legacy
XLS remains blocked pending an actual sample. GUI, wheel and Windows packaging
include the adapter; no Microsoft/SharePoint/Power BI operations are added.

All original sources and business calculations/exclusions remain unchanged.
CompuClean cleaner versions advance so previously selected months require normal
review after updating. No automatic overwrite/migration is performed. Synthetic
monthly cases are not production approval; see `edge_case_validation.md` and the
repair discrepancy in `format_compatibility.md`.

The sections below describe earlier milestones as implemented at that time.

# Release notes

## 0.2.0 — M2 local desktop prototype

- Added a CustomTkinter interface with supported report cards, native local file
  selection, explicit month confirmation, previews, results, warnings, history/help
  and bundled synthetic samples. TMA is visibly unavailable.
- Added background processing, main-thread event delivery and between-file stop/
  deferred close. Source changes invalidate previews; corrections require an
  explicit checkbox and M1's existing bound approval token.
- Added shared read-only M1 preview/history APIs without changing cleaners,
  calculations or exclusions. No outputs are created by preview.
- Added workflow/widget tests and a visible-window smoke workflow, plus Windows
  PyInstaller onedir build configuration and packaged-executable CI checks.

This user-directed M2 is offline. Microsoft/Graph work is deferred, not implemented.
Production accuracy remains unverified; managed-PC testing and IT distribution
approval are still required. Windows build evidence is reported in the PR checks.

## 0.1.0 — M1 offline cleaning foundation

- Added type/period-specific CSV wrappers around original repair and flat-service
  transformations/writers, with no calculation/date/exclusion changes.
- Added bytes/path requests, sequential coordination, structured results,
  conservative layout guards, counts/warnings and local candidate artifacts.
- Added a persistent local SQLite manifest, hash-verified rerun skips, immutable
  revision history and replacement acknowledgement bound to current/proposed data.
- Added synthetic workflow, source equivalence, invalid-input and failure-injection
  tests, plus an installed-wheel engine smoke check and architecture/test guidance.

TMA remains blocked pending compatible verified fixtures; inventory's taxonomy
helper remains missing. No production accuracy or source-total reconciliation is
claimed. Microsoft integration, GUI, Power BI publishing and executable packaging
are deferred. M0's approved-sample gate remains open.

## 0.0.1 — M0 setup and discovery

- Added a Python 3.12 src-layout package, pinned dependency resolution, offline
  CLI/config check, testing framework, and Windows/Linux CI configuration.
- Preserved all six uploaded cleaning sources unchanged with SHA-256 provenance.
- Added cleaner/result and version-aware storage contracts; Graph operations fail
  explicitly while integration is disabled.
- Documented code-derived schema observations, compatibility risks and the exact
  sanitized fixtures, missing source and IT configuration still needed.

No GUI, production adapter, report publisher, live sign-in, SharePoint operation,
packaged Windows executable or Power BI change is delivered. M0's verified-sample
acceptance remains open until approved raw/expected pairs and baselines arrive.

## Monthly departmental workflow follow-up

- Desktop now recommends/defaults to standardized Power BI CSV candidates; legacy
  mode and CLI/API defaults remain available for compatibility.
- Configurable separate local roots, direct month/type discovery, missing-report
  checklist and mixed-type real-engine preview/process are available.
- Explicit complete-month review packets copy current verified candidates into new
  immutable snapshots with counts/hashes/warnings. No approved output is written;
  synchronization and production accuracy remain unverified.
- Added an M folder-ingestion example/offline reference contract tests, employee
  SOP, validation/finance gates, branch/PR roadmap and delegated Graph requirements.
  M runtime evaluation, authenticated publication and live Microsoft remain deferred.
- Original cleaning calculations, exclusions and production Power BI/SharePoint
  are unchanged. The January repair-cost discrepancy remains a production blocker.

## Settings and Guided Mode follow-up

Visual Settings replaces mandatory manual TOML editing. Added first-run setup,
Browse/recommended local storage, validation/confirmed creation, atomic private
preferences, automatic restore, confirmed reset and advanced import/sanitized
export. Known sync/network candidate stores are blocked; custom locations still
need trusted local/IT confirmation. Existing reports/history are never migrated.
Guided Mode defaults to Detailed and remembers Brief/off choices. Hover/focus,
F1/topic help and a bundled Employee guide explain sources, workflow states,
disabled actions, errors, corrections and financial/production limits. Short/scaled
displays use adaptive sizes/scrolling; a managed-PC accessibility pilot remains.
Cleaning/calculations/exclusions/schemas, revision safeguards and packet contracts
are unchanged. No Graph/auth, production publishing, Power BI or sync-completion
claim is added. The repair-cost discrepancy remains unresolved.

## Power BI integration pilot (candidate review only)

Adds an explicit multi-month snapshot/reconciliation CLI and synthetic two-month
trial, required-month Power Query examples and monthly controls, model mapping
proposals and unresolved repair-cost decision checklist. Existing cleaners/financial
calculations, GUI and legacy outputs remain unchanged. Real M/PBIX/model accuracy
and business approval are pending. No production dashboard, SharePoint, authenticated
approval or publisher is implemented.

## Repair financial mapping — schema v2

Recommended Power BI repair output now distinguishes reported total cost, estimated
labor and explicit legacy arithmetic. Source raw values stay available; ambiguous
unequal grouped fields stay unassigned. A separate monthly summary is hash-bound to
each revision and included in packets/snapshots. v2 M examples and migration guidance
preserve v1/legacy compatibility; service/TMA/calculations/exclusions are unchanged.
Actual January arithmetic reconciles; February/formatted grouped evidence and full
business/model approval remain pending. No candidate approval or production writes.

## Milestone A — schema-v2 Power BI real-data readiness

Adds v2-only packet selection, one-read snapshot verification, recomputed four-table
readiness/independent expectations/original-source audit reports, a complete fictional
walkthrough, shared v2 month queries and monthly reconciliation query. Documents
backup-model preservation, management decisions and B/C/D dependencies. Original
cleaners, financial schema/estimates and desktop behavior are unchanged. Owner-reported
January/February source reconciliation does not approve production or establish real
v2 M/DAX execution; that trial remains manual. No inventory or live Graph added.

## Milestone C — SharePoint connectivity foundation

Adds local/synced read-provider contracts, stable/placeholder-aware GUI reads,
nonrecursive provider discovery, injected offline Graph operations/error/retry/
verification and fixed synthetic probe recovery, MSAL-compatible session behavior
and Windows user-DPAPI encrypted-cache component. Settings/Guided Mode make unavailable
Graph and unverified sync explicit. No SDK/HTTP bootstrap, real sign-in, arbitrary
upload, approval-state change, production SharePoint/PBIX access or cleaner/schema/
calculation change. See sharepoint_foundation.md for the tested versus deferred matrix.
