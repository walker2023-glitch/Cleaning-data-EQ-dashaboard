# Inputs needed for verified cleaning and desktop pilot (M0–M2)

## Identity-readiness next decisions

No additional real reports or credentials are needed for the UX tests. Before live
reviewer identity work, name the data/IT policy owners and choose authoritative
reviewer-role/resource verification, tenant/public-client registration/redirect/
scopes, conditional access, signed evidence/receipts, revocation/expiry/separation of
duties and cache/retention policy. Keep actual tenant/user/assertion data private.
A successful sign-in alone cannot approve a candidate. See approval_ux_identity_readiness.md.
Windows managed-PC usability/scaling/profile migration and exact-head hosted build
checks remain separate evidence gates. Existing raw/expected/business requirements
below remain; do not resend already-tested January/February files just for UI work.

## Approval milestone decisions

Do not resend already-tested January/February reports merely for this foundation.
Owner reports successful Windows OneDrive raw reads and real v2 Desktop imports.
Next inputs are decisions: designated reviewers and independently verifiable
identity/role authority; revocation/expiry and separation-of-duties policy;
required independent evidence, accepted financial/null/completeness exceptions,
local-request retention/support owner, and final approved-artifact/status contract.
IT must authorize test resources, delegated scopes/resource grants, protected cache
and executable policies before live connectivity. Neither a typed name nor a local
checkbox may establish approval. Keep actual departmental configuration, audit
notes, expectations, source indexes and identity evidence private. See
approval_publishing_foundation.md and sharepoint_live_pilot.md.

## What is needed after the desktop prototype

January raw repair/service CSVs and TMA XLSX are now inspected, together with the
prior February service sample. They are inputs only: no trusted cleaned output
was supplied. See `format_compatibility.md` and `edge_case_validation.md` for the
observed layouts, source-count checks and synthetic monthly cases.

Still needed: the remaining February–June raw exports, actual legacy XLS exports
(and their expected counts), and approved cleaned examples/baselines. Do not resend
the already supplied January files or February service sample. TMA XLSX can now
produce provisional candidates using the original requests writer; alternate
layouts/XLS remain blocked. Confirm the candidate title/five-column CSV against
the trusted downstream loader before departmental use.

**Repair blocker:** January reported financial totals differ from the unchanged
cleaner's totals. Explain Textbox38 versus Textbox16 and the intended parts/labor
semantics, duration defaults and rate. Supply a trusted cleaned repair output and
approved labor/parts/cost totals before any mapping/calculation change.

For a desktop pilot, identify an authorized reviewer and IT-managed Windows 10/11
PC without Python. Confirm allowed executable/signing policy, an approved local
candidate folder, retention/support ownership, display scaling/accessibility needs,
and whether the preview/correction warnings are understandable to Facilities staff.
No Microsoft registration or production folder access is needed to try bundled
synthetic samples. Microsoft/Graph work still needs separate approval.

## What M1 now makes available

An offline coordinator and CLI wrap the supplied repair and flat-service CSV
transforms without changing their calculations/exclusions. Synthetic tests cover
the API, duplicates, corrected months, failed processing and preserved originals.
Production accuracy remains unverified. The observed TMA title/header/footer XLSX
now uses the requests cleaner as a provisional candidate contract. Legacy XLS,
service context layouts and other encodings are not enabled.

The highest-priority next inputs are one approved raw/expected pair for repairs,
one for flat service orders, and a trusted cleaned TMA example to compare with the existing requests cleaner. Include the counts/totals and policies described below.
No need to resend the six existing uploads.

## Source scripts

Already supplied and preserved: `__init__.py`, `repairs_row_clean.py`,
`service_row_clean.py`, `requests_row_clean.py`, `row_clean_common.py`, and
`list_clean.py`. Confirm their version/provenance and whether these are the
currently trusted production cleaners; provide corrected originals if needed.

Still needed:

- If inventory becomes in scope: original `dashboard/taxonomy.py` and any local
  dependencies it imports, plus a sanitized equipment `Type.csv` lookup and
  equipment sample. Inventory is optional and does not block the three-report M0.
- Confirm that the supplied requests cleaner is the currently approved TMA cleaner.
  The January input matches it structurally; trusted output approval is still open.
  If a different production cleaner exists, supply its helpers/dependency versions.
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

## Before normalized exports or classification can be published

Review the proposed schema-v1 contracts in `powerbi_output_design.md`, especially
null financial presentation versus explicit Legacy calculated fields, text IDs,
raw descriptions/status/tags and source-bound row IDs. Supply trusted cleaned
comparisons and approve Power Query types/decimal precision only after resolving
the repair money-field/rate/default-hours questions. No current-approved publisher
or ingestion-folder migration is enabled by producing these candidates.

For the separate classifier milestone, supply authorized manually labeled match
and class examples (including unmatched/conflicting/cross-month/PM-with-TMA cases),
confirm whether PM/Repair suffixes actually occur and their reliability, define
other-maintenance taxonomy and review ownership, and approve date windows and
false-match/review-workload thresholds. TMA currently lacks structured shared
equipment/location/event keys; identify any additional supported fields before
proposing exact joins. See `maintenance_classification_design.md`. No employee
identity/authentication is invented for the offline review design.

## Monthly departmental workflow decisions

- Confirm whether all three reports are required every month and how a genuine
  zero-activity month is evidenced; current packet export requires all three
  nonempty supported candidates. Do not supply fabricated blank reports.
- Choose private local raw/candidate roots and a reserved approved destination,
  local/synced availability policy, single operator, backup/retention/support owner.
  Keep SQLite local; no OneDrive synchronization verification is implemented.
- Name business/finance/model reviewers for `validation_checklist.md`; supply
  trusted cleaned pairs and comparable counts/hours/parts/labor/estimated totals.
  Resolve repair Textbox38/Textbox16/default/rate semantics before production use.
- Approve a separate Power Query review PBIX pilot and precision/null policy;
  the M example/offline contract tests do not authorize production migration.
- For connected work, provide IT's decisions in `sharepoint_integration_plan.md`
  plus separate authorization for registration/test-site auth and operations.
  Do not send secrets, tokens or production access to unblock a local prototype.

## Power BI integration pilot inputs

The runnable synthetic multi-month pilot is in powerbi_pilot.md. For actual model
reconciliation, provide an authorized **non-secret column/type inventory** of
Compuclean list, Service_Orders and the real TMA table, impacted DAX expressions,
relationship/calendar/Building_Dim keys and filter directions, sort/RLS behavior,
and private monthly measure exports with their exact filter/date scope. A production
PBIX or credentials are not needed for repository work. Fill generated baseline
observations locally; do not commit departmental totals or confidential metadata.

Supply trusted raw/expected pairs, one-copy source summary totals, accepted/excluded
counts, hours/financial baselines, and finance decisions in
repair_cost_reconciliation.md. Confirm nullable-money precision/tolerances,
service reporting-month versus calendar basis, corrected-month selection and
zero-activity evidence. Blank observations remain unknown; invented synthetic
baselines never stand in for the existing dashboard. Record actual Power BI Desktop
version and M/relationship/DAX/visual outcomes in the backup-PBIX pilot checklist.

## Repair financial mapping follow-up

The owner confirmed formatted individual costs mean Total Cost. The local January
CSV's equal Textbox38/Textbox16 cells reconcile under v2. Still needed privately:
formatted January repair XLSX, raw February repair CSV (and formatted version),
nonzero multi-repair equipment examples identifying individual amount vs subtotal,
trusted expected outputs and finance/model approval of the remaining hours/rate,
null/precision and monthly-vs-equipment measure policies. Do not resend January raw
CSV. Unequal financial cells remain unassigned; no subtotal mapping is guessed.
See repair_financial_v2.md. Do not commit actual financial amounts or raw reports.

## Milestone A update — owner evidence on 2026-10-27

Owner reports January/February v2 reconciliation and successful synthetic Desktop
import with the previous repair schema. Do not request those already-tested inputs
again merely to run the local readiness SOP. All six real sources/packets are not
present here: use explicit local packets, private expected metrics and original-file
index as instructed in powerbi_real_data_readiness.md. Service/TMA accepted counts,
exact DAX/relationship inventory and the real v2 Desktop regression record still
need to be supplied/recorded privately; do not invent them from synthetic fixtures.

Next milestone B needs an authorized sanitized Equipment List by Location raw/expected
pair, two dated snapshots, online/offline and duplicate semantics, unresolved location
examples and actual Building_Dim key/map contract. Its original helper/Type.csv are
missing; code aliases are not verification of the source layout. Inventory remains
outside three-report monthly completeness. Nonzero unequal repair subtotal meanings,
hours/rate/cross-month service policies and authenticated approval remain open.

## Milestone C inputs and limits

No credentials/live access are needed for the foundation or offline demo. Owner reports
successful real-data Power BI checks/imports/visuals and a separate inventory matrix;
do not request previously tested reports again merely to exercise storage mocks.
Before a connected read-only test PR, IT must supply/approve the public-client Entra
registration, delegated scope/resource-grant combination, exact nonproduction site/
library/raw/probe IDs, permitted download hosts, protected-cache/ACL/retention/sign-out
policy, device/proxy/executable restrictions and authorized test users. Keep actual
configuration local; never send secrets/tokens in chat/GitHub. See the live-pilot
checklist. Real HTTP/SDK wiring and authenticated approval/publication remain absent.
