# Power BI CSV candidate exports — schema v1

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
