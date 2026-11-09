# Add read-only historical batch preview and local diagnostics

Base: `main` at f49b297. Head: `feature/historical-batch-preview`.

Employees previously had to preview historical months individually. Historical Data
now discovers a range and previews all three report types sequentially from one
screen, with per-month counts, exclusion/date/missing-value evidence, financial-v2
summaries, stale-source rejection and readable failure states. Safe cancellation
keeps completed results and marks remaining slots Not previewed. Optional CSV/JSON
exports are nonproduction diagnostic reports outside workspace and synced folders.

The coordinator gains an opt-in detailed read-only preview for unchanged candidates;
normal duplicate and correction behavior is preserved. Existing adapters and all
financial calculations remain unchanged. No candidate write, revision selection,
approval request, authentication, publication or Power BI refresh is introduced.

A six-month synthetic generator, screenshot, updated employee/bundled guides and
exact Windows acceptance steps are included in `docs/historical_batch_preview.md`.
The Windows build includes this guide. Range state is session-only and independent
of the persisted single reporting month/root/layout.

Validation on Linux/Python 3.12.14:

- Full regression suite: 808 passed, zero failures/errors/skips; all 61 GUI cases
  isolated in fresh processes, no retries (765 baseline + 43 new cases).
- Wheel/sdist builds passed.
- Source and isolated installed-wheel desktop smoke passed phase 39; both
  separate-process settings/restart checks passed.
- Real XLSX, classic BIFF8, timestamped BIFF8 and formatting-only edge fixtures;
  stale/corrected/duplicate/missing/unsupported inputs; zero/missing money;
  cancellation, partial failure, export cleanup and Windows UTF-16 limits tested.

Native Windows packaging/packaged smoke and hosted Windows/Linux outcomes remain
unverified from this Linux environment. The push workflow is configured for them;
check Actions and manually preview January–June on the owner's authorized local
raw copy before merge. Prior owner real-data May/June acceptance is not blanket
financial approval. GitHub PR/check APIs currently return Forbidden/403.

No automatic merge. Batch processing and historical snapshot publication remain
separate milestones.

Manual PR creation:
https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard/compare/main...feature/historical-batch-preview?expand=1

Use this document as the PR body and the first line as the title; target `main`.
