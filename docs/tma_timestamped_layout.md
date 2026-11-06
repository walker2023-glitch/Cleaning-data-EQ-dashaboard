# Timestamped TMA HI-042b layout — May and June local acceptance

## Evidence and dependency

Branch feature/tma-timestamped-layout starts from legacy-tma-compatibility
**32d36b6**, which depends on historical-folder-discovery **c425841**. Main is
**bd21499** at inspection; neither feature is merged. The PR targets the legacy
branch without replaying its changes. GitHub PR/check API remains HTTP-403 blocked;
no open-review/hosted-check result is inferred. Do not merge automatically.

The owner has independently inspected the actual May workbook: genuine BIFF8,
one sheet CU_Repair_WO_History_-_Previous, 85 physical rows, 4 columns; 81 records,
all request dates parseable and in May. The reported numeric generation value
46174.31306712963 converts with the workbook date system to June 1, 2026 about
07:30 (07:30:49 for that exact serial). This is owner-provided structural evidence,
not an application run against the private workbook in this environment.

The prior adapter correctly rejected this different layout: it expected an explicit
month title in row 1, headers in row 2, and a final count footer. Its ID reader also
stopped before the last row because that layout has a footer. The new adapter
recognizes a separate tightly specified structure and includes the last body row
in identifier normalization and cleaning. It does not relax the old footer gate.

## Exact additional contract

The existing anchored legacy filename matcher is unchanged. The numeric filename
suffix and the words Previous_Month never determine a reporting period.

Acceptance requires all of these:

- Genuine OLE BIFF8 XLS, exactly one sheet named `CU_Repair_WO_History_-_Previous`.
- Exactly four physical columns; no hidden/unlabeled extra-data column is ignored.
- Row 1, column 1: a positive finite **numeric Excel date/time serial**, with cell
  type XL_CELL_NUMBER or XL_CELL_DATE; other cells in that row blank. Conversion
  uses `xlrd.xldate_as_datetime(cell.value, book.datemode)` with date system 0 or 1.
  Text (including ISO text), booleans, missing/negative/zero/nonfinite/out-of-range
  values and the fictional 1900-02-29 serial are rejected. No text date parser,
  locale/month-day guess, filename tick conversion or timezone conversion is used.
- Row 2: exactly `CU Repair WO History - Previous Month (HI-042b)` in the first
  cell, other cells blank. The hyphen and report code are significant.
- Row 3 entirely blank.
- Row 4: exactly `Work Order #`, `Request Date`, `Requestor`, `Request` in that order.
- Rows 5 onward: work-order records, **no footer**. Known Total/Grand Total footer
  markers reject the layout instead of being silently sliced off. No minimum or
  expected body count of 81 is built into the engine. At least one body row is needed.
- The calendar month immediately before the generation timestamp must equal the
  operator-selected YYYY-MM. December/January rollover is handled by calendar
  arithmetic, not by subtracting 30 days from the generation day.
- Every retained request date must still belong to the selected month.

A recognized sheet/title is a routing hint, never approval. A wrong sheet, title,
timestamp, separator, header, period or footer produces a specific safe message.
The existing standard XLSX and classic XLS four/five-column layouts keep their
own month-title/header/footer validation, including arbitrary sheet names. An old
standard workbook named with this sheet title still uses its original layout.
The new timestamped structure is not enabled for XLSX without separate verification.

## Preserved cleaning, counts and provenance

The original requests cleaner, date parser, CSV writer, missing-ID/total-ID/invalid-
date exclusions and legitimate repeated transactions are unchanged. Unparseable
request-date records follow the existing exclusion rule with warnings and counts;
they are never assigned a date. If all records are excluded, processing fails.
Retained out-of-month records reject the report; excluded source records outside
the period remain counted warnings. This is not a new whole-file exclusion policy.

Only source Assigned To is absent. The preserved cleaner fills blank fields;
CSV has no typed null, so `AssignedTo` is an empty field, not a fake employee or
the literal text null. Source/retained affected counts and a missing-column warning
remain. Existing Power Query text-blank semantics and the optional separate nullable
assignment view are documented in legacy_tma_compatibility.md.

Preview additionally reports physical worksheet rows, source body-record count,
parseable source request dates, retained count and source dates outside the selected
month. Physical count includes four heading rows. There is no source footer total
for this layout: body count is an observed count, not independent reconciliation or
business approval. A synthetic 85-row example demonstrates 81 source/retained rows;
other fixtures use three records to ensure the engine does not hardcode 81.

Leading-zero/text IDs and supported numeric zero-only display formats are retained,
including the final record. The original bytes remain untouched. Existing source
version/hash checks, SourceFileName, SHA-256, correction acknowledgements, immutable
revision history and CandidateUnverified status remain. No private workbook is in
GitHub. Generated body names/requests/IDs are invented, not sanitized copies of
actual employees or transactions.

Cleaner identity is now `tma-workbook-v3:...`. Previously selected TMA candidates
remain readable and immutable; reprocessing with the new cleaner can require
explicit correction review even when source bytes match. No silent replacement,
financial schema v2 change, CompuClean calculation change, business approval or
publication is introduced. Direct Graph and production Power BI are untouched.

## Manual May 2026 acceptance in VS Code / Windows

Use the cloned repository folder, not a downloaded executable ZIP. Close running
application copies before uv updates their Windows launchers. Use a separate
private profile and **new trusted-local candidate folder** outside OneDrive,
SharePoint, approved outputs and production ingestion.

```powershell
git fetch origin
git switch --track origin/feature/tma-timestamped-layout
git branch --show-current
git rev-parse --short HEAD
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app --settings-file data/may-layout-test/settings.toml
```

If the branch exists, use git switch feature/tma-timestamped-layout and git pull
--ff-only. Settings: choose SharePoint year/month layout and the authorized locally
available 01_Raw_Data root; choose separate local candidates/reserved approved
locations. Confirm local candidate storage, Check Locations and Save Settings.

1. Retain the original May workbook unchanged. Independently record its SHA-256
   locally using `Get-FileHash -Algorithm SHA256 -LiteralPath <private-path>`.
   Do not put private paths, reports or output descriptions in GitHub.
2. Select May 2026 → Discover month. Confirm the original legacy basename is TMA.
   Resolve ambiguous XLS/XLSX matches with the owner; the app never prefers one.
3. Confirm the reporting month → Preview Processing. No candidate files should
   be created. Inspect counts and warnings. Expected based on owner evidence:
   **85 physical rows, 81 source records, 81 parseable May dates, 0 source dates
   outside May**, and missing Assigned To. Retained count should be 81 if no
   existing ID/date exclusion applies; inspect any difference rather than forcing it.
4. Compare against the original: earliest May 1 at 05:01 and latest May 29 at 16:25,
   all original legitimate records, leading-zero/text IDs, repeated transactions and
   blank assignments. Normalized RequestDate intentionally remains date-only ISO;
   the original workbook preserves request times, as before.
5. Review any generation/period error. A June generation timestamp means May,
   regardless of folder/filename. Do not change dates or select a different month
   merely to make a wrong file pass. Text timestamp cells are unsupported for this
   contract; stop and provide a sanitized structural example instead of rewriting
   the original. The owner-confirmed cell is numeric and should pass this gate.
6. Process only after reviewing the preview, into the separate local test candidate
   directory. Verify 81 records where exclusions allow, SourceFileName and raw SHA,
   ReportMonth 2026-05, ISO dates, missing assignments and CandidateUnverified.
   Compare the original hash again. Approval/Publish must remain disabled.
7. Re-preview to confirm skips. A correction or cleaner-version change requires
   the existing explicit acknowledgement. Preserve prior revisions. If the source
   changes after discovery/preview, stop and rediscover, then preview again.

Do not modify or save over the original, publish/approve a candidate, change a PBIX,
or copy unverified output into a production ingestion folder. Record private owner
acceptance findings and resolve any unsupported structure before further processing.

## June test

Inspect the actual June workbook locally; do not assume its body count. Require the
same exact sheet/title/separator/four headers/no-footer structure. Its numeric
Excel generation timestamp must be in **July 2026**, and retained request dates in
**June 2026**. Select June 2026, discover, confirm, preview and compare independent
source/retained counts, date range, affected assignments and hash before candidate
processing. A May workbook placed in June must fail generation-period validation.
A synthetic June fixture with three records exercises this path in packaged smoke;
it is not evidence of actual June counts or accuracy.

For a disposable synthetic preview from the repository:

```powershell
python -m uv run --frozen python -m equipment_data_manager process tests/fixtures/synthetic/tma_timestamped/may_81.xls --report-type tma_work_orders --period 2026-05 --output-format powerbi --output-dir data/timestamped-may-test --preview
python -m uv run --frozen python -m equipment_data_manager process tests/fixtures/synthetic/tma_timestamped/june.xls --report-type tma_work_orders --period 2026-06 --output-format powerbi --output-dir data/timestamped-june-test --preview
```

Remove --preview only after review to create local synthetic candidates. These
invented examples do not reproduce actual request descriptions, IDs or date ranges.

## Verification and remaining gates

Final Linux regression: **731 passed, 0 failures, 0 errors, 0 skips**, retaining
all 684 previous cases. Wheel/sdist build, default installed-wheel May (81-record)
and June (3-record) processing, source/installed-wheel phase-36 desktop and
fresh-process restart checks passed. These are synthetic/offline Linux results. Automated coverage includes numeric
serial validation, both date systems, May/June/year rollover, missing/text/boolean/
invalid timestamps, wrong month/title/sheet/separator/headers, unexpected footer/
extra columns, invalid/out-of-month dates, repeated work orders, last-record zero
formats, standard XLSX footer compatibility, normalized schema, source hashes,
source changes, immutable corrections and real GUI counts/actions.

Windows/Linux CI, installed-wheel May/June processing and actual Windows executable
phase-36 desktop/restart checks are configured on branch pushes. Native Windows
and hosted outcomes cannot be inferred from Linux tests or a workflow definition;
GitHub API access is still blocked here. Actual May/June output acceptance remains
owner-manual on the authorized Windows computer, using the original reports.
