# Legacy TMA compatibility — candidate support, May still unverified

## Baseline and exact cause

This focused branch, feature/legacy-tma-compatibility, depends on
feature/historical-folder-discovery at **c425841**. Main remains **bd21499** (PR #17)
at inspection; the historical-discovery head is not an ancestor of main. The
GitHub API returns HTTP 403, so its PR number/open-review/check status cannot be
verified here. The new PR targets the historical-discovery branch; do not merge
or duplicate that prerequisite automatically. Retarget to main only after the
owner merges the prerequisite and verifies ancestry/CI.

Previously three separate gates rejected May: the shared-folder matcher only knew
Work Orders Month YYYY; historical discovery rejected XLS extensions; and the
coordinator rejected XLS before the XLSX-only, five-column adapter could run.
The preserved requests cleaner already supplies a missing Assigned To column as
blank. That behavior is now reused; no second cleaning transform is introduced.

**The actual May workbook is not attached/inspected in this task.** The owner
reports four columns. Tests establish candidate support for a strict synthetic
four-column BIFF8 workbook, not equivalence to the actual May export. Its exact
title, header/footer, sheet structure, IDs, dates and totals must still be checked.
Unknown structure fails closed; no mappings, missing dates or period are invented.

## Discovery and processing contract

Shared year/month discovery accepts this additional anchored, case-insensitive
family, with **1–30 decimal digits** between the closing parenthesis and `.xls`:

`CU_Repair_WO_History_-_Previous_Month_(HI-042b)<digits>.xls`

No alternate report code, arbitrary suffix/copy marker, arbitrary XLS filename or
XLSX with this legacy stem is guessed. Existing Work Orders Month YYYY names and
both folder layouts remain. A filename match is not schema validation. XLS/XLSX
matches in the same month are ambiguous even if their contents agree; neither
format wins. Original names, local provider identities/versions, sizes and hashes
are preserved. Standard type folders and manual selection can explicitly route
other basenames to TMA, but the contents must pass the same strict adapter.

Supported candidate workbook structure for either extension:

1. One worksheet, first row `CU Repair WO History — May 2026` for the selected May
   period (the corresponding explicit English month/year for other periods).
   Remaining first-row cells blank. No extra preamble or Previous Month title guess.
2. Second row exactly Work Order #, Request Date, Requestor, Request, and optionally
   Assigned To in that order. No other missing, extra or duplicated headers.
3. Body records, then last row exactly `Total: N records` in the first cell alone;
   N must match the source body-record count, not the cleaned count.

The existing date parser, blank-ID/total-ID/invalid-date exclusions, repeated
transaction retention, CSV writer and ISO Power BI wrapper remain. Retained dates
outside the confirmed reporting month still reject the report; the explicit title
must also match. Filename Previous_Month never determines a period. An additional
count warning reports parseable out-of-period source dates, including source
records subject to original exclusions; it does not change which records survive.
Missing Requestor/Request *values* retain the existing behavior; their source
*headers* remain required. No new business exclusions are introduced.

## Scoped XLS reader and identifiers

Pinned xlrd **2.0.2** is now a core dependency, available in CLI/default desktop and
installed wheels without the legacy extra. The legacy extra name remains for
existing commands. XLS requires the OLE compound signature and BIFF8 (Excel
97–2003); raw older BIFF, HTML/XML/CSV or ZIP/XLSX masquerading as XLS is rejected.
The read uses bytes in memory, no Excel/COM automation. xlrd and openpyxl read
stored/cached values; macros/formulas/external content are not executed or refreshed.
Encrypted (including BIFF FILEPASS), corrupted, multiple-sheet and ambiguous
workbooks fail safely with category-only errors. Reader diagnostics are discarded
in a private in-memory stream, never printed with workbook data.

TMA processing is capped at 64 MiB original bytes; XLS additionally allows at most
100,003 rows and 4–5 columns before pandas conversion. These are input/shape limits,
not a hard guarantee of peak process memory or a sandbox against hostile files.
Keep using authorized sources. Original files are read only. Existing provider
availability/version/hash guards and immutable candidate corrections remain.

Text IDs retain leading zeros and alphanumeric characters. A numeric integer with
an unambiguous all-zero Excel number format (2–20 zeros) retains that displayed
padding. General/0 numeric integers retain the stored integer and warn that absent
leading zeros cannot be inferred. Fractional, negative, unsafe-precision (>2^53−1),
date/boolean IDs and other numeric display formats are rejected as ambiguous.
Native Excel date cells follow the reader's existing pandas/date transform.
Arbitrary custom numeric-ID formats require reviewed examples, not guesses.

## Missing assignments and output compatibility

Only Assigned To may be absent. The preserved cleaner supplies blank values,
keeping the legacy five-column writer and normalized TMA schema 1/powerbi-v1.
Warnings identify `tma_assigned_to_source_column_missing`, source affected-record
count and retained affected-record count. A reconciliation metric also records
retained work orders missing the source assignment column. A present-but-blank
assignment stays missing without incorrectly reporting a missing source column.
No employee, default assignment, zero or literal string `null` is substituted.

**CSV has no typed null**: the missing AssignedTo is an empty field, as in existing
outputs. Existing pilot text contracts intentionally read blank text as `""`;
they are unchanged. If actual M nulls are required for comparisons/DAX, create a
separate BACKUP-PBIX view using `powerquery/TmaNullableAssignments.pq`. That example
maps empty AssignedTo to null without modifying the original table/query or any
financial columns. Actual Power Query Desktop execution still requires owner
acceptance; no production query or PBIX was changed. Do not claim the old pilot
already produces a typed null.

The adapter keeps its existing public class name TmaXlsxCleaner for integration
compatibility, but supports both workbook formats. Cleaner identity changes to
`tma-workbook-v2:xlrd-2.0.2:...` (and the normal Power BI wrapper prefix). This is
**not** a financial or CSV schema version change. Previously selected TMA candidates
remain untouched/readable. Processing their same raw file with this new cleaner
may require explicit correction review because the cleaner identity changed;
no automatic replacement or approval occurs. Repeated new-version runs still skip.
CompuClean transforms, financial v2 calculations/columns and review authority are
unchanged.

## Manual May acceptance on Windows / VS Code

Use the cloned repository folder in VS Code (not the downloaded executable ZIP).
Close running copies before dependency sync to avoid Windows launcher file locks.

```powershell
git fetch origin
git switch --track origin/feature/legacy-tma-compatibility
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app --settings-file data/may-private-test/settings.toml
```

If the branch already exists, switch to it and use git pull --ff-only. Use a NEW
private local test candidate folder, outside OneDrive/SharePoint/network storage.
Do not point a test at approved outputs or a production Power BI ingestion folder.
Only the owner initiates this real-report test on the authorized computer.

1. Open the original May workbook read only using the authorized local procedure.
   Inspect the real sheet count, title, exact four/five headers, footer count,
   date range and text/formatted IDs. Do not save, rename or convert the original.
   If its structure differs from the strict contract above, stop and provide a
   sanitized structural example for review; do not edit it to make it pass.
2. Configure Raw Data as the authorized locally available 01_Raw_Data root;
   choose SharePoint year/month layout. Set NEW trusted-local candidates and a
   separate reserved approved folder; confirm, Check Locations, Save Settings.
3. Select May 2026 → Discover month. The documented legacy filename should be
   identified as TMA. Inspect Historical Data for captured path, size, version,
   hash and any ambiguity. Other report types can be missing for a TMA-only test;
   a complete monthly packet still requires all three types.
4. Confirm May, then Preview Processing. Compare source/retained counts and dates
   against the original report, including exclusions. If title/dates disagree,
   preview must fail; do not override the period or exclusions to accept it.
5. Check missing-assignment warnings and affected counts. AssignedTo must be
   blank/null and all legitimate IDs/dates/requests retained. Compare repeated
   work orders individually; do not deduplicate legitimate transactions.
6. Only after reviewing the preview, Process into the separate local test directory.
   Inspect the header-first TMA CSV, SourceFileName, SourceFileSHA256, ReportMonth,
   ISO RequestDate, text WorkOrderId, blank AssignedTo and CandidateUnverified.
   Independently compute the original hash, e.g. `Get-FileHash -Algorithm SHA256
   -LiteralPath <private-original-path>`, and compare locally; never put private
   paths/reports into GitHub. Confirm the original bytes remain unchanged.
7. Re-preview: unchanged input should skip. For a corrected file, use a separate
   authorized correction test copy; rediscover, review the existing correction
   acknowledgement, then process. Preserve old candidate revisions. If a source
   changes between discovery/preview/processing, rediscover and preview again.
8. Validate January–April examples separately. Do not approve/publish anything or
   alter production SharePoint/Power BI. Record private workbook/version, source
   hash, counts, date range, affected assignments, exclusions and owner findings.
   Arithmetic success and CI are not business approval of the actual May report.

If an export is actually HTML/XML disguised as XLS, encrypted or structurally
unknown, the safe error is expected. Obtain an authorized genuine supported export
or supply a sanitized structure for a new adapter. A manually reviewed separate
XLSX copy can be tested locally, preserving the original and recording both hashes;
the same strict schema/period checks apply and no automatic conversion/linkage is
claimed. Never merely change an extension.

## Tests, packaging and blockers

Fixtures under tests/fixtures/synthetic/legacy_tma are invented BIFF8, generated
with fixture-only xlwt/olefile (neither is an application dependency). The encrypted
marker fixture asserts xlrd's real FILEPASS rejection; it is not departmental data
or an encryption/decryption implementation. A bundled synthetic four-column XLS
is byte-identical and used by the phase-33 source/executable smoke.

Coverage includes January–April XLSX parity with the original cleaner, four/five
columns, blank/missing assignments, native date cells, text and formatted-zero IDs,
strict names and near misses, invalid/corrupted/encrypted/ambiguous workbooks,
XLS/XLSX duplicates, wrong title/month/dates, original exclusions/repeated records,
source changes, skips/corrections/old revisions, GUI and normalized-schema/provenance.
Former XLS-disabled tests now assert actual invalid-workbook rejection and no
writes; their safety coverage was updated for the intentionally supported format,
not removed to accept arbitrary bytes.

Final Linux regression: **684 passed, 0 failures, 0 errors, 0 skips**. Wheel/sdist
build, default installed-wheel XLS processing and source/installed-wheel phase-33
desktop plus restart passed. Windows/Linux CI and installed-wheel XLS processing
are configured. PyInstaller
explicitly includes xlrd and the synthetic XLS resource. Actual native Windows
build/phase-33/restart must pass on Windows; Linux checks are not that evidence.
GitHub API access remains blocked, so hosted outcomes are unverified here. The real
May workbook/schema, owner baseline acceptance and any nonstandard layouts remain
blockers; reviewer authority, production publishing and direct Graph remain disabled.
