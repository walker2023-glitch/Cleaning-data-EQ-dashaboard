# Add confirmed historical batch processing of local unapproved candidates

Historical reports previously had to be processed month by month. Historical Data
now lets employees select reports across months, review a refreshed processing plan,
explicitly confirm intent, and create local normalized candidates through the
existing coordinator. Results include counts, warning/financial evidence, revision
hashes, failures and safe cancellation. Unchanged candidates skip on repeat runs.

Based on merged main fe5df23 (PR #22), on feature/historical-batch-processing. No
historical prerequisite is replayed and no existing PR/main is merged by this work.

- Immutable session plan binds source identity/version/SHA, cleaner/proposed output,
  current candidate revision and selected configuration. The compatible guarded
  coordinator method checks expectations inside the normal SQLite transaction.
- Corrections are blocked in bulk and routed to existing individual confirmation.
  A blanket batch checkbox cannot authorize replacement or establish business approval.
- Sequential background work, per-report progress, stop between commits, scoped
  results and private diagnostic CSV/JSON exports. All Tk updates stay on its thread.
- Fresh plan/intent after restart; committed manifest history determines completion.
  Orphan filesystem writes are not selected, assumed successful or recursively ingested.
- Existing Windows export/link/junction and review-packet guards remain. Candidate
  destination checks reject internal redirects and projected long Windows paths.
- No cleaning/financial schema v2/exclusion/date changes, authoritative approval,
  review-request creation, publication, Graph writes, Power BI refresh or combined
  historical snapshot generation. Original private reports are not touched/committed.

Tests add both-layout one/six-month and year-boundary execution, subset selections,
skips/corrections, current-revision and proposal races, source/config changes,
financial gaps, service exclusions/cross-period dates, legacy/timestamped XLS,
concurrency, cancellation, storage failure, interruption/retry/orphan recovery,
exports and visible UI selection/intent/results/settings/correction routing.
Source/installed/packaged smoke extends to phase 45 (batch create plus safe retry),
including a separate-process restart. Synthetic screenshot and full isolated Windows
acceptance are in docs/historical_batch_processing.md.

Real January–June **processing** acceptance is owner-pending; prior all-18 preview
acceptance does not establish it. Hosted Windows/Linux and native packaging must
pass before merge recommendation. Do not merge automatically.

Manual PR link if the API is blocked:
https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard/compare/main...feature/historical-batch-processing?expand=1

Local validation: **884 tests passed, no failures/errors/skips**, with 67 GUI cases
isolated without retries. Wheel/sdist builds passed. Source and isolated
installed-wheel phase-45 desktop/restart checks passed. Screenshots demonstrate
real mapped/scrolled widgets using invented reports. Hosted Windows/Linux and
native package outcomes must be checked on the pushed head before merge.

Hosted Windows follow-up: the primary processing action was above other controls
and could scroll outside a small viewport. It now ends the panel; the unchanged
visibility assertion reproduces the original failure at 1100×700 on Linux and
passes after the layout fix. No processing/security rules changed.
