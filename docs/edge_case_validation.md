# Multi-month evidence and edge-case inventory

## What was actually supplied

Only January's three raw exports are attached to this task. The earlier February
service export was inspected in PR #4. No other monthly exports, legacy XLS files,
trusted cleaned outputs or approved financial baselines were supplied here.

| Month | Repair count stated by user | Service count stated by user | TMA count stated by user | Real-file evidence available |
|---|---:|---:|---:|---|
| January 2026 | 29 | 29 | 38 | All three raw files inspected; preview/process retained 29/29/38 |
| February 2026 | 5 | 5 | 67 | Service: previous fix retained 5; repair/TMA pending |
| March 2026 | 17 | 17 | 69 | Not attached |
| April 2026 | 33 | 35 | 59 | Not attached |
| May 2026 | 55 | 58 | Not stated | Not attached; legacy XLS layout/count pending |
| June 2026 | 69 | 70 | Not stated | Not attached; legacy XLS layout/count pending |

`tests/report_samples.py` generates invented examples for all 16 stated monthly
count cases. Passing those cases proves no hardcoded February limitation and
checks count/mapping behavior; it **does not** verify unseen monthly exports.
Records deliberately repeat to ensure legitimate repeated events survive.
Static synthetic repair/TMA fixtures show each newly observed layout. The earlier
synthetic service fixture remains. Raw attachments and local candidate outputs
are kept outside committed fixtures; source bytes were unchanged in local checks.

## Automated inventory

| Edge / risk | Checks and current behavior | Remaining evidence / decision |
|---|---|---|
| Counts and repeated summaries | All 16 synthetic month/count cases preview/process; repair/service report count once, TMA footer once; inconsistent/malformed metadata fails | Remaining real months and expected exclusion counts |
| Equipment IDs | `000439` survives observed repair/service layouts; textual `000123` survives XLSX and CSV serialization | Priced service subset still uses original inference; numeric Excel values with display-only zeros need examples/policy |
| Embedded repair labels | Original extraction of equipment name/ID/location/vendor; synthetic exact values asserted | Approved expected mappings and vendor defaults |
| Money/hours | Original fractions, `found`, malformed/blank duration defaults and rate tested; invalid-money/finite-output tests retained; summaries never summed | January financial discrepancy in compatibility matrix; no calculation fix attempted |
| CSV encoding / quoting | UTF-8 BOM/no-BOM, quoted commas/quotes/multiline service text, multiline repair source, malformed/blank/duplicate headers and row widths | Non-UTF-8 formats remain unsupported |
| Dates / periods | ISO service/repair dates; TMA MM/DD/YYYY; service cross-month scheduled/completed OR rule and last-day timestamps retained; repair/TMA mismatch fails | Ambiguous numeric dates, timezones and business reporting-period rules need approval |
| Status / missing price | Missing Cost accepted only exact service summary layout; price blank/warned; blank/unknown status original fallback with diagnostic | Approved status semantics; contradictory explicit statuses remain unchanged |
| Exclusions | Repair invalid date/no identity, service placeholders/PM suffix/`delete duplicate`, TMA invalid dates/blank or `total` IDs; category/count warnings | Detailed rejection audit and policy approval; all-output-excluded fails safely |
| TMA workbook shape | Exact title/header/footer, sheet count, columns and count checked; malformed/renamed workbook rejected; original transform/writer equivalence tested | Other titles/layouts/CSV and actual legacy XLS samples; trusted cleaned TMA output |
| Duplicates/corrections | Every new layout: renamed rerun skips, changed month requires bound token, previous revisions retained, bad correction leaves active output; same basename another month independent | Organizational multiuser publication remains deferred |
| GUI / packaging | TMA card, XLSX selection, sample, preview/process tested; existing responsive worker/correction tests retained; packaged smoke extended to load TMA via openpyxl | Managed-PC pilot and employee release approval remain separate |
| Failures / privacy | Category-only errors, no network in tests, no raw fixture content logged, corrupt manifests/artifacts fail closed; original upload hashes checked | No production publishing/logging/audit claims |

## Changes to behavior

- Exact 14-column repairs now validate repeated metadata, expose source counts and
  reported totals, preserve the ID as text and warn on financial disagreement.
  Existing calculations, descriptions/default heuristics and output preamble remain.
- Service summary layout works for every confirmed month, with status-fallback
  diagnostics added; the previous missing-price adapter/output schema is unchanged.
- TMA XLSX candidate processing is enabled only for the observed layout, through
  the original requests transform/writer. Original sources remain untouched;
  the newly bundled requests copy changes only its helper import to be relative.
- CompuClean wrapper versions advance for changed validation/diagnostics. Existing
  selected months therefore require normal correction review after this update.
  No outputs are silently replaced. TMA has a separate initial cleaner identity.
- Legacy XLS, alternate Excel/CSV work-order formats and production accuracy remain
  blocked by missing evidence. No SharePoint, Graph, authentication or Power BI work.

A local success is structural validation and creation of a **candidate**. Source
counts are reconciled against metadata, not against trusted cleaned records or
Power BI totals. No trusted expected output was available for comparison.
