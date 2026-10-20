# Equipment Data Manager — Design & Implementation Specification

**Status:** Proposed design, not yet implemented  
**Audience:** AI coding agent (Cursor, Codex, etc.), developer, departmental maintainer  
**Target:** Windows 10/11 desktop application distributed through departmental SharePoint  
**Project:** Facilities Equipment Maintenance Power BI Dashboard  
**Last updated:** 2026-10-20

## 0. Agent instructions and boundaries

Build the application described below incrementally. **Do not modify the production Power BI report, existing SharePoint files, or historical cleaned datasets without explicit approval.** Start by inspecting the actual existing Python cleaning modules and representative sanitized exports. Preserve verified behavior, schema, and calculations. If source code or samples are missing, implement interfaces and fixtures but do not invent CompuClean field mappings.

**This document is a design specification, not evidence that permissions, schemas, or connectors already work.** Ask for required configuration and obtain IT approval for organizational authentication. Do not bypass tenant security, MFA, device policy, or executable restrictions. Never embed credentials, access tokens, client secrets, or private source data in the repository, installer, or logs.

Implementation priorities: data correctness > recoverability > security > usability > performance > aesthetics. Commit changes in small, reversible milestones with tests and clear release notes.

## 1. Context and goal

The department has a working Power BI equipment maintenance dashboard (MVP). Its historical data currently comes from monthly files:

| Source system | Official report | Current model concept | Input |
|---|---|---|---|
| CompuClean | Repair Report | `Compuclean list` (combined repair history) | CSV export, one reporting month per file |
| CompuClean | Service Orders List | `Service_Orders` | CSV export, one reporting month per file |
| TMA | Work Orders (provided by Tim) | Work order/request data | Format/schema must be verified from real samples |
| Potential future | Equipment inventory, Workday | Inventory / labor capacity | Not in initial scope; design for extensibility |

Employees currently obtain the reports, run Python scripts to clean **individual** files, import each cleaned file into Power BI, and manually append monthly queries. SharePoint has folders for `01_Raw_Data`, `02_Cleaned_Data`, `03_Power_BI`, `04_Scripts`, `05_Documentation`, and `06_Logs`. Exact SharePoint site/library/folder IDs must be discovered or configured; do not hardcode a guessed URL.

**Goal:** A nontechnical authorized employee downloads the approved Windows application from SharePoint, signs in using their own Microsoft 365 work identity, previews raw reports already stored in SharePoint, clicks **Process New Reports**, reviews validation results, and finds correctly standardized CSV outputs in SharePoint's Cleaned Data folders. No SharePoint sync requirement, VS Code, Python installation, or direct Power BI model editing.

**Non-goals for v1:** automatic CompuClean/TMA extraction, scheduled/background execution, direct Power BI semantic-model changes, Power BI refresh API integration, SQL database, a web server, unattended service account, or full equipment lifecycle analytics.

## 2. Employee journey and interface

1. Download and launch approved `EquipmentDataManager` Windows release.
2. Click **Sign in with Microsoft**; use organizational sign-in (including MFA/conditional access).
3. App verifies access to the configured SharePoint document library and required folders.
4. Click **Scan Raw Reports**. App lists report type, filename, detected reporting month, status, and warnings.
5. Review **New**, **Already processed**, **Changed since last processing**, **Unrecognized**, **Missing month**, and **Needs review** statuses.
6. Click **Process Selected** (or **Process New Reports**). Show a confirmation summarizing intended outputs; changed/replacement months require explicit confirmation.
7. App downloads inputs into an isolated local temporary workspace, cleans and validates, then uploads validated outputs into corresponding cleaned-data folders.
8. Show success/skip/failure counts, validation summaries, and a link to the relevant SharePoint folder. Provide **Export processing report** and **Open troubleshooting guide**.
9. Show **Refresh Power BI** instructions only; do not imply refresh occurred unless integrated and confirmed in a future release.

### Proposed screens

- **Home:** connection state, SharePoint location, last successful scan, large `Scan Raw Reports` and `Process New Reports` buttons, latest processing summary.
- **Files / Preview:** searchable table: source system, report type, period, original filename, file size, status, detected schema, issues, proposed output name. Allow selecting a subset.
- **Run details:** progress by file, cancellation before upload/commit, counts and validation warnings; never show raw credentials.
- **History:** processed file records and prior run summaries; filters by report type/period; export logs.
- **Settings:** configured SharePoint site/library/folder mappings, sign out, cache location, version, diagnostic export. Do not expose arbitrary unsafe file paths by default.
- **Help:** step-by-step SOP, expected report names and CSV export guidance, IT contact, known limitations.

Accessibility: keyboard navigation, readable error messages, sufficient contrast, no color-only statuses, responsive layout at typical 1080p and scaled Windows display settings. Run processing in a worker thread/task so the GUI remains responsive; marshal updates safely to the UI thread.

## 3. Architecture

```text
Windows Desktop GUI (CustomTkinter)
    |
    +-- Application controller / processing coordinator
    |     +-- report classifier + reporting period parser
    |     +-- manifest / idempotency / conflict detector
    |     +-- cleaning adapters (existing Python modules)
    |     +-- schema and reconciliation validators
    |     +-- transactional publish coordinator
    |     +-- structured audit log
    |
    +-- Authentication adapter (MSAL public client)
    +-- SharePoint repository adapter (Microsoft Graph)
              |
              +-- SharePoint / 01_Raw_Data / [report type]
              +-- SharePoint / 02_Cleaned_Data / [report type]
              +-- SharePoint / 06_Logs / [approved logs/manifests]
```

Use dependency injection/interfaces so local filesystem fixtures can replace Microsoft Graph in automated tests. The cleaning engine must be independently callable from a CLI and GUI, enabling later scheduling or a cloud front end without rewriting cleaners.

Suggested repository layout:

```text
equipment-data-manager/
  design.md
  README.md
  pyproject.toml
  requirements.lock              # or another reproducible lockfile
  src/equipment_data_manager/
    __main__.py
    ui/                          # CustomTkinter views
    auth/msal_auth.py
    storage/interface.py
    storage/graph_sharepoint.py
    storage/local_fixture.py
    processing/coordinator.py
    processing/classifier.py
    processing/manifest.py
    processing/validators.py
    processing/cleaners/
      repairs.py
      service_orders.py
      work_orders.py
      equipment.py              # future/optional
    config.py
    logging_setup.py
  tests/
    fixtures/                    # synthetic or sanitized, never private production data
    test_classification.py
    test_cleaners.py
    test_idempotency.py
    test_validation.py
    test_publish.py
    test_auth_errors.py
  packaging/
    build.ps1
    pyinstaller.spec
  docs/
    user_guide.md
    admin_setup.md
    recovery.md
    data_contracts.md
    release_notes.md
```

## 4. Microsoft identity and SharePoint integration

### Required IT setup

1. Confirm departmental authorization for a custom desktop client and data-processing workflow.
2. Register an application in **Microsoft Entra ID** (or have IT register it) as a **public/native client** with appropriate tenant restrictions and redirect URI supported by MSAL. Do **not** create a client secret for the packaged desktop application.
3. Obtain the tenant ID, application/client ID, allowed authority, and approved **delegated Microsoft Graph permissions**. Prefer least-privilege access scoped to the intended SharePoint site/library when supported by the organization's tenant and grant model (e.g. `Sites.Selected` with appropriate site grant); confirm feasibility with IT. Do not assume a specific permission will work without testing; broader `Files.ReadWrite.All`/`Sites.ReadWrite.All` should not be requested merely for convenience.
4. Confirm whether administrator consent is required, and configure it through IT. The signed-in user must independently have SharePoint permissions for reading raw data and writing cleaned data/logs.
5. Confirm approved token-cache behavior, device security, and policies for running unsigned/custom executables.
6. Obtain exact SharePoint site ID, drive/library ID, and paths for raw/cleaned/log folders. Resolve via supported Graph endpoints and persist stable IDs in configuration where practical.

### Sign-in and tokens

- Use **MSAL for Python** public client interactive authorization (system browser / supported redirect) with MFA and conditional access; silent token acquisition where permitted.
- Store token cache securely using an approved Windows-protected mechanism (for example a DPAPI-backed secure cache); never write plaintext refresh tokens into SharePoint, JSON configuration, or logs.
- Support sign-out, expired token recovery, denied consent, insufficient permissions, and offline/network errors.
- Verify signed-in account and target SharePoint site before any upload.
- Do not use username/password collection, app-embedded secrets, or a privileged service account in the desktop binary.

### Microsoft Graph repository behavior

- List folder children with pagination; follow `@odata.nextLink` safely.
- Download raw files using supported Graph content endpoints into a temporary workspace.
- Upload cleaned outputs using simple upload for small files or upload sessions for larger files, as appropriate.
- Respect HTTP 429/503 throttling and `Retry-After`, use bounded retries with exponential backoff, timeouts, and clear errors.
- Use item IDs and ETags / conditional operations where supported to avoid overwriting files changed by another user. Do not silently overwrite an existing cleaned report.
- Do not rely solely on filenames or SharePoint modified timestamps for identity. Compute SHA-256 content hashes and record source item ID/version/ETag, report type, reporting period, cleaner version, output hash, and processing status.
- A failed upload or validation must leave the last known-good cleaned output intact. Use staged output plus a controlled commit/replacement strategy; do not claim multi-file atomicity across SharePoint operations.
- For first release, restrict processing to one operator at a time through documented procedure or implement a shared lease/lock with expiry and conflict detection. Local-only locks do **not** protect against two employees on different computers.

## 5. File classification, naming, and data contracts

Expected SharePoint folders (configure actual names):

```text
Equipment Dashboard/
  01_Raw_Data/
    Repair_Reports/
    Service_Orders/
    Work_Orders/
    Equipment_Inventory/        # future
  02_Cleaned_Data/
    Repair_Reports/
    Service_Orders/
    Work_Orders/
    Equipment_Inventory/        # future
  06_Logs/
```

Output filename convention: `Source_ReportType_YYYY-MM.csv`, for example `CompuClean_RepairReports_2026-09.csv`, `CompuClean_ServiceOrders_2026-09.csv`, `TMA_WorkOrders_2026-09.csv`. Keep original filenames and source metadata in the manifest. Never alter raw exports. **Reporting period must be verified from report contents and/or a user-confirmed period**, not inferred from filename alone.

- Repair Reports: monthly transaction files; combine across nonoverlapping months in Power BI.
- Service Orders List: monthly transaction files; combine across nonoverlapping months.
- TMA Work Orders: supplied by Tim; actual schema, file format, date field, and cleaning needs require inspection.
- Equipment Inventory (future): likely a snapshot; **do not append snapshots as transactions**. Use latest validated snapshot for current inventory unless historical inventory tracking is explicitly designed.

Before coding transformations, build `docs/data_contracts.md` from real source exports: expected columns, types, aliases, row grain, date semantics, required vs optional fields, units, totals, and known exceptions. Verify whether date filters include the entire last day of the month. Never silently discard unknown columns or records without logging why.

## 6. Reuse existing cleaning scripts

Prior project README identified the following modules, which must be retrieved and inspected before implementation:

- `clean/repairs_row_clean.py`
- `clean/service_row_clean.py`
- `clean/requests_row_clean.py`
- `clean/list_clean.py`
- `clean/row_clean_common.py`

These modules were identified by the prior project's README; their actual code and current compatibility must be verified. Old dashboard startup, admin, recovery, and valuation scripts are **not** the production cleaning engine by default.

Refactor the actual cleaners into side-effect-free adapters where feasible:

```python
class Cleaner(Protocol):
    def clean(self, raw_bytes: bytes, *, source_name: str, period: str) -> CleanResult: ...
```

`CleanResult` should include output bytes/dataframe, row counts, schema, warnings, source period, and reconciliation metrics. Adapters must not depend on a developer's Downloads folder or move raw files. Handle encodings, preamble/header rows, blank and duplicate headers, date parsing, monetary values, labor hours, and ID normalization according to verified behavior. Fail clearly on unknown layouts rather than producing misleading data.

## 7. Validation and duplicate protection

Before publishing each cleaned file:

- Confirm expected report type and month; require explicit review when uncertain.
- Validate required columns and parseable types; report rejected rows with reasons (without unnecessarily exposing personal data).
- Compare raw and cleaned record counts with documented exclusions; do not assume counts must always be equal.
- Check that dates belong to the selected period or explicitly flag cross-period records.
- Reconcile repair count, repair labor hours, parts cost, labor cost, and estimated total against source report totals **where available and semantically comparable**.
- Check for duplicated source files, duplicated months, and possible duplicate records. Never deduplicate business records solely because values look identical; separate service events can share fields.
- Skip identical raw content processed with the same cleaner version; reprocess changed content or changed cleaner versions after review.
- If a month already exists, show a diff summary and require explicit confirmation for replacement; preserve previous validated output/version.
- If validation fails, do not publish; show a plain-language message and create a diagnostic log.

A processing manifest may be a SharePoint list (preferred for concurrency/queries if approved) or an explicitly controlled JSON document for a single-operator prototype. Do not assume that independently edited JSON manifests are safe for concurrent writes.

## 8. Power BI integration — later milestone

Initially, **do not change the current PBIX**. Once outputs are validated:

1. In a copy of the PBIX, create SharePoint Folder queries filtered to the specific `02_Cleaned_Data` report-type paths and `.csv` files.
2. Combine monthly cleaned files by report type. Prevent accidental inclusion of temporary, archive, or duplicate outputs.
3. Compare new results with existing manually appended queries: row counts, months, IDs, repair totals, costs, hours, date ranges, and slicer behavior.
4. Preserve the identities of existing reporting tables (`Compuclean list`, `Service_Orders`, and work-order tables) when updating query source logic, to minimize relationship/DAX breakage. Do not delete and recreate tables merely to rename them.
5. Confirm `Building_Dim`, calendar relationships, map locations, measures, and all report pages still work. Previous table renaming caused calculated-table/relationship errors.
6. Only then publish to a test workspace and arrange Power BI Service refresh with an approved long-lived connection owner. Desktop app v1 only displays instructions for refresh.

## 9. Security, privacy, and operational controls

- Use only authorized departmental accounts and approved organizational data handling.
- Do not store CompuClean/TMA credentials in this app. The app never logs into those source systems.
- Store transient raw files under an application-controlled temp directory; clean them up after processing according to policy, including after errors.
- Avoid logging work-order descriptions, names, or other sensitive fields; prefer file IDs, counts, hashes, and error categories.
- Limit Graph permissions to required files/site; validate destination path to prevent writing outside approved folders.
- Verify source and release integrity; obtain IT approval for code signing / endpoint security distribution. Never tell users to disable antivirus or bypass SmartScreen.
- Provide reproducible builds, dependency pinning, software bill of materials if required, and vulnerability review.
- Ensure a future employee can administer configuration and recover outputs without the original developer's account.

## 10. Packaging and SharePoint distribution

- Develop/test on Windows with a pinned supported Python version.
- Use PyInstaller to bundle the app and dependencies. Start with `onedir` for easier debugging; optionally distribute `onefile` after testing. Verify the actual cleaner modules and bundled resources are included.
- Publish a versioned ZIP in `04_Scripts/Data_Manager/Releases/`, e.g. `EquipmentDataManager_v0.1.0_win64.zip`, plus checksum, release notes, and a short installation guide.
- Employees download and extract locally, then run the executable. **Do not run the binary directly from SharePoint web preview.** The app connects to SharePoint after sign-in.
- Test on a second IT-managed Windows PC without Python installed, with standard-user privileges, corporate network policies, MFA, and restricted SharePoint permissions.
- Define a support/update policy. Prefer replacing the local app with a tested newer release; no unapproved self-updater.

## 11. Milestones and acceptance criteria

### M0 — Discovery and fixtures

- Obtain original cleaners and sanitized raw/cleaned examples for Repair Report, Service Orders List, and TMA Work Orders.
- Confirm report schemas, exact SharePoint folder layout, IT restrictions, and Power BI baseline totals.
- Write data contracts and a comparison baseline.
- **Done when:** each report has a verified sample and expected output; unknowns are documented.

### M1 — Local processing engine (no Microsoft integration)

- Implement adapters, classifier, period detection, validation, manifest interface, and local fixture repository.
- Provide CLI command and automated tests.
- **Done when:** representative inputs yield expected cleaned files; reruns skip unchanged data; changed months require explicit replacement; raw files remain untouched.

### M2 — Graph authentication and SharePoint repository

- Integrate MSAL delegated sign-in and Graph file operations using IT-approved registration/permissions.
- Add retry, pagination, safe upload, conflict detection, and secure token caching.
- **Done when:** an authorized test user can list, download, and upload a test file to approved folders; unauthorized access fails safely.

### M3 — Desktop GUI

- Implement Home, Preview, Processing, History, Settings, and Help screens.
- Add responsive progress, user confirmation, and readable errors.
- **Done when:** a nontechnical test employee can process a new sample month without seeing code or using a terminal.

### M4 — Validation, packaging, and pilot

- Validate July–September historical examples and a newly received month against trusted source totals.
- Test repeated runs, corrections, missing files, corrupted inputs, Graph throttling, expired sign-in, and two-operator conflicts.
- Package for Windows and test on a different managed computer.
- **Done when:** no silent duplicate month, no destructive overwrite, no unreported failed upload, and correct outputs are visible in SharePoint.

### M5 — Power BI folder ingestion (separate approved change)

- Build/test SharePoint folder queries in a backup PBIX; reconcile with existing tables and all visuals.
- **Done when:** adding a validated monthly cleaned CSV makes it appear in the refreshed report without manually importing or appending another query.

## 12. Test matrix

At minimum automate tests for: valid repair CSV; valid service CSV; TMA fixture when obtained; malformed/unknown CSV; empty file; encoding variation; duplicate headers; invalid date; partial reporting period; duplicate raw upload; changed file same month; changed cleaner version; mismatched totals; missing SharePoint permissions; Graph pagination; throttling; token expiration; interrupted download; interrupted upload; concurrent processing; Windows packaged release without Python installed.

Include golden-file comparisons against *sanitized* known-good outputs, with documented tolerances for numeric totals. Never test on production files with write access by default.

## 13. Handoff deliverables

- Versioned Windows executable release and checksum.
- Complete source code and pinned dependencies.
- `README.md` for developers, `user_guide.md` for nontechnical employees, `admin_setup.md` for IT, `recovery.md` for restoration.
- Data source inventory and data contracts.
- Automated test suite, fixture data, validation report format.
- Documented Graph permissions, SharePoint site/library/folder IDs, and configuration process (without secrets).
- Release/change log, known issues, and ownership contacts.

## 14. Decisions needed before implementation

1. Will IT approve a public-client Entra app registration and delegated Microsoft Graph permissions? Who owns the registration?
2. What exact SharePoint site, library, and folders are used? Who has read/write access?
3. Can employees run a packaged unsigned Windows application, or is code signing required?
4. Where are the actual `clean/*.py` modules and sample raw/cleaned exports? Does TMA need a different cleaner?
5. Are cleaned CSVs expected to replace the current manual append tables immediately, or only after a separate validation milestone?
6. Should the first release enforce one designated operator, or is simultaneous multiuser processing a requirement?
7. What is the approved retention policy for raw reports, cleaned outputs, local temporary files, and processing logs?

**Recommended first coding task:** inspect the actual cleaning modules and representative files, document the exact data contracts, and build the M1 local processing engine with tests. Do **not** begin with a GUI mockup or Microsoft authentication before proving the data outputs are correct.
