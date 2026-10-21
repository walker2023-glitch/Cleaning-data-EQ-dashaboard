# Development (M2 offline desktop)

Read `README.md` and `design.md` fully before changes. Use a feature branch and
pull-request review. M1 is based on M0 commit `2889796`; PR #1 remains a separate
draft and must not be merged automatically. The M1 PR targets the M0 branch so
its review contains only M1 changes; retarget after M0 merges. M2 uses a separate
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
2026; TMA uses January 2026. Legacy candidate is still the default. Preview/process
it first if you want a saved comparison. Then choose **Power BI CSV candidate** in
Output format, reconfirm the month and preview/process. Format changes clear prior
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
