# Development (M2 offline desktop)

Read `README.md` and `design.md` fully before changes. Use a feature branch and
pull-request review. M1 is based on M0 commit `2889796`; PR #1 is now merged.
PRs #2–#7 remain open in a dependency chain; do not merge or retarget them
automatically. See `roadmap.md` for the current branch/PR review. The M1 PR
still targets the M0 branch pending maintainer review. M2 uses a separate
`feature/m2-desktop-gui` branch based on M1 commit `0449dce`, and its PR targets
`feature/m1-cleaning-engine`. Do not merge either parent PR automatically.

Cloud tasks are already isolated. Use the existing checkout and do not create a
worktree unless explicitly requested. Use Python 3.12.14 (`.python-version`) and
uv 0.12.23. From the repository root:

```sh
uv sync --frozen --all-extras
uv run --frozen --all-extras pytest
uv run --frozen --extra desktop equipment-data-manager-desktop
uv run --frozen --all-extras equipment-data-manager --check-config config.example.toml
uv build
uv run --isolated --no-project --with ./dist/equipment_data_manager-0.2.0-py3-none-any.whl python -I -m equipment_data_manager
uv run --isolated --no-project --with ./dist/equipment_data_manager-0.2.0-py3-none-any.whl python -I -m equipment_data_manager process tests/fixtures/synthetic/repairs_input.csv --report-type repairs --period 2026-09 --output-dir data/wheel-smoke
```

GUI tests require a display. On headless Linux use `xvfb-run -a` before the pytest
command; this cloud instance was tested with a local Xorg dummy display instead.
The multi-month follow-up passes 185 tests locally, including real-widget tests
and the prior M0/M1/M2 suite.
The desktop can also be launched with `python -m equipment_data_manager.ui.app`
inside the uv environment. It opens a native window, not a web preview.

Use `packaging/build.ps1` on Windows for a windowed onedir prototype. Windows CI
also runs the packaged executable's synthetic GUI smoke workflow before uploading
the ZIP/checksum artifact. See `windows_packaging.md` for exact build/test commands,
employee preview instructions and the remaining managed-PC release gate.

These commands work in PowerShell and POSIX shells. `uv sync` creates `.venv`;
no global pandas installation is needed. CI bootstraps uv with the hosted Python
3.12, then uses `uv python install 3.12.14` for the pinned project runtime;
setup-python lacks that exact Windows build.

The engine requires pinned pandas and openpyxl for the observed TMA XLSX.
The optional `legacy` extra supplies xlrd for discovery; XLS remains blocked.
The `desktop` extra pins CustomTkinter/Pillow and `packaging` pins PyInstaller.
The lockfile pins dependencies and artifact hashes. Update `uv.lock` only with
reviewed dependency changes and rerun all tests. Build tooling is pinned in
`pyproject.toml`. Bump the relevant adapter version if reading, formatting or
validation behavior changes; source and pandas versions are already in its identity.

## Package layout

| Location | Purpose |
|---|---|
| `processing/interfaces.py` | Cleaner and candidate CSV/schema/metric contracts |
| `processing/models.py` | Requests, statuses and revision/result metadata |
| `processing/cleaners.py` | Supported-layout guards and source-preserving wrappers |
| `processing/_legacy/` | Four bundled original modules; only imports changed |
| `processing/coordinator.py` | Bytes/path inputs, sequential work and review decisions |
| `processing/manifest.py` | Local SQLite selection and immutable CSV revisions |
| `legacy/clean/` | All six untouched uploads with checked SHA-256 hashes |
| `storage/` | Future storage contracts and disabled Graph implementation |
| `ui/app.py` | CustomTkinter views and native dialogs; main-thread rendering |
| `ui/workflow.py` | File-source boundary and preview/process orchestration |
| `ui/worker.py` | Background execution with queue-delivered progress/results |
| `resources/samples/` | Bundled synthetic CSVs, identical to source-derived fixtures |
| `packaging/` | Windows PyInstaller specification, entry point and build script |
| `tests/` | Offline characterization, failure injection and workflow tests |

The coordinator is callable without CLI/GUI or Graph. See
[cleaning_architecture.md](cleaning_architecture.md) for the Python API and
transaction/recovery boundaries, and [testing.md](testing.md) for tests and limits.

## Fixture and output handling

Keep experiments/output under ignored `data/` or an authorized local temporary
directory. No real exports, credentials, tokens, PBIX files or organizational
settings belong in commits. SQLite manifests are ignored, but CSVs outside ignored
paths are not automatically safe to commit. Commit only reviewed synthetic or
explicitly sanitized fixtures under `tests/fixtures/`, with provenance, expected
counts, exclusions, totals and tolerances. Current examples are source-derived,
not approved production validation. Do not change calculation/date/exclusion behavior
without verified fixtures and explicit approval. Tests verify the vendored copies
differ from the untouched originals only in package-relative imports.

## Deferred integration

M0 configuration remains offline-only; Microsoft fields are inert placeholders.
M2 adds the local GUI only. No MSAL, credentials, network client or token cache is added. The Graph
stub still raises on every operation. Local locking protects this output store
only; it is not a cross-computer SharePoint lease. IT approval, conditional Graph
uploads and secure Windows token caching remain deferred until separately approved.

## Test the multi-month branch in VS Code

Fetch and check out `feature/multi-month-compatibility`. It is based on the February
service fix; no parent PR is merged automatically. Select `.venv\Scripts\python.exe`
as the Windows interpreter after the first command below. In VS Code's integrated
PowerShell terminal, from the repository root:

```powershell
uv sync --frozen --all-extras
uv run --frozen --all-extras pytest
uv run --frozen --all-extras python tests/report_samples.py --output-dir data/monthly-samples
uv run --frozen --extra desktop equipment-data-manager-desktop --output-dir data/monthly-review
```

Use a fresh sample directory: the generator refuses to overwrite files. For each
sample, choose its report card and month/year, select the file, confirm the month,
then preview/process. The generator creates six repair, six service and four TMA
files using the stated counts and entirely invented content. Select one month at
a time; the GUI intentionally does not infer a different month for every file.
The bundled TMA sample uses January 2026; the two CompuClean bundled samples retain
September 2026. Repeat a file to see a skip. A changed file for the same month
requires correction review and keeps the previous output.

To try the supplied **raw** inputs, store them in an authorized ignored local
folder, select the correct report card and January 2026. Expect 29 repairs, 29
service orders or 38 TMA work orders, plus unverified-accuracy warnings. The repair
candidate additionally warns of financial disagreement: do not treat that as a
validated result. No trusted expected cleaned output was supplied. Inspect CSVs
as text in VS Code to check leading zeros (spreadsheet auto-inference can hide them).
See `edge_case_validation.md` for remaining months/XLS and unresolved questions.

## January failure diagnostics

See [January investigation and Windows VS Code steps](january_rejection_investigation.md)
for the new branch, the isolated Windows test command, native XLSX/XLS filters,
runtime checks and write-free CLI date/exclusion traces. The same supplied January
inputs pass locally; the reported Windows CSV rejections remain unreproduced.
Do not weaken period checks or change financial rules to force acceptance.

## Power BI candidate branch in VS Code

Close the app before syncing, open the repository (not an extracted prototype ZIP),
then use its integrated PowerShell terminal:

```powershell
git fetch origin
git switch feature/powerbi-candidate-exports
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app --output-dir data/export-review
```

Select a report and **Load synthetic sample**. CompuClean samples use September
2026; TMA uses January 2026. Power BI CSV candidate is now the desktop default.
Choose Legacy candidate explicitly if you want a saved comparison, then switch
back to Power BI CSV candidate, reconfirm the month and preview/process. Format changes clear prior
previews/correction confirmations. Both modes use the existing cleaners; each has
an independent candidate history. The base output folder's powerbi_candidates
subdirectory holds normalized revisions; no approved-current folder is created.

Open the selected result's CSV in VS Code as text. Expect one header, ReportMonth,
ISO dates and text IDs with their source zeros. No repair/TMA title or summary rows
should appear. RawDescription and SourceMaintenanceTag preserve service evidence;
they are not classifications. Missing repair parts/estimated totals are blank in
the normalized fields, with original arithmetic retained in explicit Legacy columns.
Keep real inputs/outputs private under an approved ignored location.

CLI preview example (remove `--preview` to save a candidate):

```powershell
python -m uv run --frozen equipment-data-manager process tests/fixtures/synthetic/repairs_summary_layout.csv --report-type repairs --period 2026-01 --output-dir data/export-review --output-format powerbi --preview
```

Use `service_orders` with the February service fixture/month, or `tma_work_orders`
with `tma_title_header_footer.xlsx`/January 2026. Omitting `--output-format powerbi`
uses legacy mode. Repeats skip; corrected months require the existing bound review
workflow independently in each mode. Production publication is blocked regardless
of local correction acknowledgement. Never combine candidate versions directories
in Power BI. See `powerbi_output_design.md` for schemas/folder design and
`maintenance_classification_design.md` for the future, unimplemented classifier.

## Monthly workflow branch in VS Code

Close all app windows first, open the Git repository (not an extracted release),
then run in PowerShell:

```powershell
git fetch origin
git switch feature/monthly-department-workflow
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
Copy-Item workspace.example.toml workspace.local.toml
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app
```

Edit workspace.local.toml privately. For Windows paths use forward slashes or TOML
single-quoted literal strings; avoid unescaped backslashes in double quotes.
Follow `monthly_workflow.md` to arrange raw/YYYY-MM/report_type, load the TOML,
discover, preview/process and explicitly export a review packet. Existing single-file
selection still works. No extra dependency or lockfile update is required.

For invented inputs, the existing generator remains available:

```powershell
python -m uv run --frozen python tests/report_samples.py --output-dir data/monthly-samples
```

Copy the generated January repairs CSV into data/monthly-raw/2026-01/repairs, the
January service CSV into service_orders and January XLSX into tma_work_orders.
Create those directories with Explorer. Use the example configuration's paths
(relative to the repo-root TOML), load it, and choose January 2026. Expected synthetic
counts are 29 repairs, 29 services and 38 TMA rows. Repeating the run skips; changing
a source for the same month requires correction review. Move one raw input to a
nested history folder to test the missing checklist without deleting it. To test
packet blocking for a new missing month, select February before processing its
three candidates. An existing month can still export its previously selected
current candidates; failed later processing does not erase them.

`monthly.py` owns folder routing and immutable review packets. `DesktopWorkflow`
groups mixed-type previews through existing per-type conflict checks; the engine
and original cleaners are untouched. `powerquery_contract.py` supplies offline
reference validation; the M example is in powerquery/. See the integration guide
for the explicit candidate-only sandbox procedure and remaining real-M pilot gate.

## Settings and Guided Mode preview

Close the app, open the Git repository in VS Code (not a downloaded prototype
folder), and use PowerShell:

```powershell
git fetch origin
git switch feature/settings-guided-mode
python -m uv sync --frozen --all-extras
python -m uv run --frozen --all-extras python .github/run_tests.py
python -m uv run --frozen --extra desktop python -m equipment_data_manager.ui.app --settings-file data/ux-preview/settings.toml
```

Use a fresh .toml path under ignored data/ for a genuine first-run test without
changing the normal profile settings. Use another filename for a second fresh
setup; do not delete personal configuration/history. Browse to private local pilot
folders (the existing synthetic monthly generator can populate raw folders).
Save once, select a month and run the ordinary discovery/preview/process/packet
workflow. Change Guided Mode/detail, wait for the preferences operation to finish,
close and rerun the exact same command: folder choices and help preferences should
restore, with no setup page if locations remain valid. Without --settings-file and
--output-dir, the app uses its normal per-user preferences path. --output-dir is a
developer isolated-session override; it intentionally does not auto-apply normal
profile workspace settings. Injected workflows likewise remain isolated for tests.

To test errors, select overlapping folders, a known sync candidate location or a
missing location and decline creation. Existing config/data must remain intact.
Use Reset to Defaults (with confirmation) to return this preview profile to setup.
For corrupt-file recovery, use an invented malformed **test** TOML under data/,
not a real user's configuration. The UI retains it until explicit valid Save/Reset.
Advanced import accepts the prior workspace format; imported locations are a draft
and require local-storage reconfirmation. The legacy session-only loader remains
available under Advanced Settings for compatibility.

Hover/focus a disabled Process button, press F1, compare Brief/Detailed, switch
Guided Mode off and use manual Help. On Results inspect date/exclusion failures,
financial warnings, duplicates and correction guidance. Changing help preferences
must preserve preview entries and correction tokens. See guided_mode.md for adding
registry content and settings_guide.md for storage/check limitations.

Build on Windows with packaging/build.ps1. The actual executable smoke now saves
visual form settings, changes guidance preferences, reads its bundled employee
guide and starts a fresh executable process to verify persisted startup, in
addition to the existing cleaning/monthly/correction/export checks. No real user
profile config or departmental reports are used. Obtain the **new branch's** build
artifact; switching Git branches does not update an earlier downloaded ZIP.

## Power BI pilot development

Branch: feature/powerbi-integration-pilot, based on feature/settings-guided-mode.
See [pilot steps](powerbi_pilot.md) for VS Code commands and the distinction between
a cloned project and an extracted executable ZIP. No GUI or cleaner changes are
needed. The offline module `equipment_data_manager.powerbi_pilot` assembles explicit
review packets, validates a pinned snapshot and creates reconciliation reports.
`examples/create_powerbi_pilot.py` uses only invented CSV/XLSX inputs through the
real engine. `examples/powerbi_pilot_reconciliation.csv` is its invented-baseline
report, not a departmental comparison. Never commit private baseline CSVs.

## Repair financial schema v2

Use feature/repair-financial-mapping from the Git project, not an executable ZIP.
See repair_financial_v2.md for VS Code/private preview commands, separate summaries
and backup-PBIX migration. LegacyCsvCleaner and PowerBiCleaner v1 remain unchanged;
the v2 wrapper reuses their exact retained-record trace and calculated values.
Desktop Power BI mode and CLI powerbi use v2 repairs; explicit CLI powerbi-v1 and
the processing.powerbi factory preserve v1 compatibility. No dependency changes.

## Milestone A readiness tooling

Branch feature/powerbi-real-data-readiness is based on PR #11, not main. Follow
powerbi_real_data_readiness.md for precise source-clone commands and a complete
fictional walkthrough. powerbi_readiness.py is a read-only assessment layer over
hash-checked snapshot data; it never cleans, changes statuses, authenticates or
publishes. Private expected/source-index CSVs and assessment folders belong under
ignored data/ or another approved local private directory. Exit 2 means report
saved with review questions, not approval. Real M execution/model tests are manual.
