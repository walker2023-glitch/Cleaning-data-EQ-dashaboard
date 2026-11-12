Historical candidates previously needed monthly packet selection before a Power BI
pilot. Historical Data now previews current selected revisions across a range and
creates four deterministic local unapproved datasets, with a bound manifest and
backup-dashboard compatibility report. Missing/invalid slots block generation.

Based on merged main eea5d01 (PR #23), branch feature/historical-powerbi-dataset.

- Read-only selected-revision reader: no recursive CSV discovery or older fallback.
  Checks current identities, supported exact cleaner/schema versions, main and
  supplemental hashes, provenance, dates, counts and financial-summary consistency.
- Generation rereads reviewed evidence, retains the default SQLite read transaction
  through finalization, and exclusively owns a new compact staging/output container.
  Local/sync/path/link/Windows guards, fsync/readback, cancellation and owned cleanup
  preserve prior snapshots and candidate history. No selection or manifest mutation.
- Four canonical datasets preserve text IDs, ISO dates, nullable money, source fields,
  financial v2 and repeated events. Appended revision/month provenance and explicitly
  labeled estimated/legacy summary controls never allocate reported monthly costs.
- Responsive desktop tab: completeness, per-slot counts/warnings/revisions, explicit
  compatibility/local-test intent, confirmation, results and completed-folder access.
  Source/installed/packaged desktop smoke reaches phase 49 plus separate restart.
- Read-only PBIX metadata analysis informs mappings, actual DAX dependencies, March
  exclusions, date precision, Building differences and Requests/Work Order coverage.
  Complete model semantics/relationships and real M/Desktop execution remain manual.
  Private PBIXs, extracted metadata and reports are excluded from the repository.
- No cleaning calculation, financial schema, adapter, approval authority, Graph,
  production publishing, PBIX change or Power BI refresh.

Synthetic tests cover one/six months, year rollover, missing/orphan/current/corrected
revisions, corrupt hashes/summaries/schemas, null/zero costs, missing assignments,
repeated work-order IDs, determinism, collisions/concurrency, interrupted writes,
atomic finalization, cancellation, Windows path/link guards and real GUI integration.
All existing regression tests are preserved, with no skips/retries. Exact-head hosted
Windows/Linux/build/native executable checks must pass before recommending merge.

See docs/historical_powerbi_dataset.md (architecture, manifest, Windows acceptance,
backup-only M import), docs/historical_dataset_columns.md (ordered CSV contracts),
docs/historical_powerbi_compatibility.md (verified mappings and unresolved decisions)
and examples/create_historical_dataset_demo.py (invented six-month reproducibility).
The screenshot uses invented data only. Actual Jan–June snapshot/backup-PBIX acceptance
remains owner-pending; previous processing acceptance is not a snapshot/model sign-off.
Do not merge automatically.

Manual PR link if API access remains blocked:
https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard/compare/main...feature/historical-powerbi-dataset?expand=1

Packaging follow-up: initial hosted regression/build checks passed, but the packaged
Windows smoke wrapper reached its 120-second outer timeout. That wrapper did not
cover the existing 90-second desktop plus 35-second restart budgets and startup.
The outer watchdog now allows 180 seconds; both inner limits, all 49 phases and
all failure assertions remain unchanged. Allowlisted phase/job/busy/elapsed
heartbeats are uploaded and surfaced as CI annotations to diagnose any remaining
native stall. The initial timeout alone does not prove its underlying phase.
