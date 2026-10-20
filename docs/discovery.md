# M0/M1 source discovery inventory

## Evidence and status

The repository initially contained `README.md`, `design.md`, and `.gitignore`.
Both documents were read fully. There was no Python project, dependency manifest,
test runner, application code, CI, source report, expected cleaned report, or
organizational configuration. The six uploaded Python modules are preserved under
`legacy/clean/` without modifications and are now available for inspection.

M0 scaffolding and discovery are implemented. **M0 acceptance remains pending**:
each report still needs a verified raw/expected pair and approved baseline totals;
SharePoint layout and IT restrictions are not confirmed. No production Microsoft
or SharePoint operation was attempted.

## Supplied source inventory

| File | Observed behavior | Outstanding evidence |
|---|---|---|
| `repairs_row_clean.py` | DataFrame transform, CSV reader, local CSV writer with three preamble rows; uses `row_clean_common` | Approved repair sample, expected output, exclusions, rate/hours policy |
| `service_row_clean.py` | Flat Service Orders List aliases and legacy Equipment Details context rows; filters by scheduled OR completed month | Samples for each supported layout, date semantics, exclusions and totals |
| `requests_row_clean.py` | CSV/XLS/XLSX reader scanning first 25 rows for `Work Order #`; selects five request columns | Whether this format is the actual TMA report; sample for each required format |
| `row_clean_common.py` | Local paths, dollar/hour parsing, month parsing, shared constants | Approval for default hours, labor rate, filename/year fallback |
| `list_clean.py` | Inventory CSV loading, aliases, ID deduplication, current-date age, lookup/category enrichment, merged summary | Missing original `dashboard.taxonomy`, optional sanitized `Type.csv`; inventory is outside initial report scope |
| `__init__.py` | Package description only | None |

All six requested uploads are present. Do not ask for the same scripts again
unless a corrected/versioned original supersedes them. Missing source is the
inventory helper and potentially a distinct TMA cleaner, not a license to invent
either module's behavior.

## Dependencies and platform

- Existing row cleaners require pandas. Request `.xlsx` reads require openpyxl;
  legacy `.xls` reads require xlrd. These are pinned in the `legacy` extra and
  `uv.lock`. Source uploads had no dependency pins; these versions are an M0
  development baseline, not proof of every historical layout's compatibility.
- Inventory additionally requires the missing `dashboard.taxonomy` functions:
  `load_equip_type_map`, `normalize_equip_type`, `norm_equip_id`, and
  `infer_equip_category_from_name`. No substitute is provided.
- Python 3.12.14 is the pinned development baseline. pytest is the M0 test runner.
  M0 core uses only the standard library. GUI, MSAL, Graph HTTP client, secure
  token-cache and PyInstaller dependencies are deliberately deferred until needed
  in M2–M4; no executable or sign-in support is claimed.
- Linux cloud validation exercises the offline workflow. CI is configured for
  Windows and Linux, but a Windows CI configuration is not evidence of a completed
  Windows run or a managed-PC executable test.

## Compatibility concerns for later adapters

These are source observations, not fixes or approved business rules:

- Shared labor rate is `12.5`; `found` maps to `0.5` hours; blank/unrecognized
  duration defaults to `1.0` hour unless the row mentions `found`. Fraction parsing
  takes the matched fraction (mixed-number semantics need review). Dollar parse
  failures become zero. These choices can affect reconciliation.
- Filename month detection assumes year 2026 if absent. Repair/service output
  names omit year. Repairs are not filtered to a confirmed period. These differ
  from the proposed confirmed-period and year-qualified naming contract.
- Repairs drop records missing both equipment fields or a parseable completed
  date; requests drop empty/`total` work-order rows and invalid request dates.
  Service drops certain descriptions, missing schedule text, and rows outside
  both date months. No structured rejected-row report is provided.
- CSV readers use pandas inference and replacement of decoding errors. Leading
  zero IDs, date ambiguity, malformed/duplicate headers, unknown columns, and
  corrupted encodings need real-fixture coverage. Output selection discards
  unselected source columns; approved preservation/diagnostic rules are needed.
- Repair output has a preamble; request output has a title then header, formats
  dates as MM/DD/YYYY, and uses a legacy title. Service emits a plain CSV with
  ISO dates. Do not silently treat all three as the same Power BI contract.
- Inventory deduplicates IDs, uses today's date for age, and reads relative lookup
  paths. Row `main()` functions derive paths relative to their package and writers
  can overwrite outputs. No manifest, rollback, version conflict handling, period
  approval, or publication validation exists in these scripts.

## M1 integration findings

All six files were reinspected. Repairs and flat Service Orders Lists have usable
pure transformations and are wrapped without calculation/exclusion changes.
`row_clean_common` supplies their pandas-dependent helpers. The requests module's
five-column shape and Excel readers do not prove TMA compatibility, so that adapter
remains blocked. Inventory still cannot import without the original taxonomy
helpers; no replacement is guessed. Original local paths, month-name/year fallback,
per-file naming and local `main`/`process_file` entry points are bypassed.

The M1 wheel bundles copies of repair/service/common modules with only relative
import changes; all six originals remain untouched. pandas is now a core runtime
dependency. Excel readers remain an optional discovery extra. Package identity
includes wrapper version, vendored-source hash and pandas version.

Supported adapter layouts are conservative source-derived CSV subsets, documented
in `cleaning_architecture.md`. The engine adds explicit guards, category/count
warnings and local duplicate/replacement safety, without rewriting transforms.
Synthetic tests cover that workflow and compare wrappers against original
transforms/writers. Golden comparisons against approved sanitized examples and
source/Power BI reconciliation remain open. See `milestones.md` for current status.
