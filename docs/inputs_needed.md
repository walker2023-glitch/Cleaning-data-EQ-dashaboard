# Inputs needed to finish discovery

## Source scripts

Already supplied and preserved: `__init__.py`, `repairs_row_clean.py`,
`service_row_clean.py`, `requests_row_clean.py`, `row_clean_common.py`, and
`list_clean.py`. Confirm their version/provenance and whether these are the
currently trusted production cleaners; provide corrected originals if needed.

Still needed:

- If inventory becomes in scope: original `dashboard/taxonomy.py` and any local
  dependencies it imports, plus a sanitized equipment `Type.csv` lookup and
  equipment sample. Inventory is optional and does not block the three-report M0.
- Confirm whether the uploaded requests cleaner is used for TMA Work Orders.
  If not, supply the actual TMA cleaner and its helper modules/dependency versions;
  if no cleaner exists, say so and supply the schema before implementation.
- Any existing approved output loader/schema definitions needed to interpret the
  legacy preambles (the repair source references `load_repairs`), plus prior
  dependency pins if available. Do not send dashboard credentials or private PBIX.

## Required sanitized fixture pairs

For **each** of Repair Report, Service Orders List, and TMA Work Orders, supply:

1. A small authorized raw export and its corresponding trusted cleaned output.
   Preserve layout, delimiter/encoding, preamble rows, column names/order, data
   types, blank cells, line endings and relevant date/number formats. For service,
   provide each layout that must be supported; for requests, each required input
   format (CSV, XLS, XLSX). Replace names, locations, IDs, vendors, descriptions,
   and any private values consistently in raw/expected pairs.
2. The confirmed reporting month, source/report version, row grain, required and
   optional columns, raw/accepted/rejected row counts and reasons, known exclusions,
   source totals, and the expected cleaned schema and filename. Include approved
   baseline Power BI counts/totals without providing a production report file.
3. Comparable reconciliation totals and tolerances: repairs, hours, parts, labor,
   estimated total where available; service/TMA totals only where meaningful.
   Confirm the labor-rate/default-hours policy, not just sample arithmetic.
4. An ordinary month plus boundary/error examples: last-day timestamps, cross-month
   scheduled/completed dates, invalid dates, missing/duplicate headers, leading-zero
   IDs, quotes/commas/encoding variants, empty file, summary/preamble rows, blank
   durations and `found`, malformed money, legitimate identical transactions, and
   a corrected file for the same month. July–September plus a new month are useful
   for the later pilot; a small verified pair per report is the immediate M0 gate.
5. A short provenance/approval note and sanitization description. Prefer synthetic
   replacements preserving semantics. Confirm authorization before committing even
   sanitized data, and inspect it for sensitive content first.

Current `tests/fixtures/synthetic/` files were authored solely from source-code
observations. They do not satisfy the verified departmental fixture gate.

## Configuration and decisions (no secrets in chat or commits)

Provide non-secret decisions through approved project channels; keep real local
settings in ignored configuration or approved environment settings:

- IT approval/owner for a native public-client Entra registration, tenant scope,
  redirect URI, approved delegated Graph scopes/site grants and user permissions.
  No client secret is needed or permitted in the desktop application.
- Exact approved test SharePoint site/library/folder IDs and report folder mapping,
  plus eventual production mapping through secure local configuration. No guessed
  tenant hostname or live discovery is used in M0.
- Token-cache/retention/logging policy, one-operator versus concurrent workflow,
  signing/executable restrictions, approved Windows/Python baseline, and support owner.
- Output header/preamble requirements and whether a future Power BI migration is
  approved separately. M0 makes no Power BI changes.

Actual tokens, passwords, client secrets, private exports, and personal data must
never be supplied through chat or committed as fixtures/configuration.
