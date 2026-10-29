# Monthly validation and approval checklist

Use an authorized private worksheet per report/month/source hash/cleaner version/
export version and candidate revision. Record reviewer, date, evidence location,
expected/actual values, approved tolerances and pass/fail/blocked. An empty check
or matching count is not approval. Never commit departmental evidence or amounts.
The application currently records structural results/warnings, not these business
approvals or authenticated reviewer identity.

- [ ] Identify source/version and month; retain immutable original and hash. Confirm
  all three report types are present, or obtain an approved zero-activity policy.
- [ ] Repairs: compare raw count, repeated source repair total (one copy only),
  exclusions by reason, retained rows, sum of RepairCount and trusted baseline.
- [ ] Service orders: compare source Total Service Orders once, raw count, exclusions
  by first reason, retained count and trusted baseline. Check scheduled-OR-completed
  inclusion, cross-month dates, status fallback, no-price nulls and legitimate repeats.
- [ ] TMA: title month, body count, footer count, blank/total-ID and invalid-date
  exclusions, retained work orders and trusted baseline. Validate the observed XLSX
  layout; XLS/alternate layouts need separate evidence, not an extension rename.
- [ ] Labor hours: compare accepted source duration semantics, original defaults/
  `found` heuristics, rounding and summed RepairPersonHours with approved examples.
- [ ] Parts cost: establish Textbox38 and Textbox16 meanings/units before judging
  comparable totals. Compare per-row and monthly values with trusted output.
- [ ] Labor cost: approve the existing 12.5 rate, hours/defaults and rounding; compare
  monthly LaborCost with a semantically comparable source/baseline.
- [ ] Estimated totals: compare original parts-plus-labor output with approved
  estimates separately from actual financial expenses. Do not substitute a repeated
  report summary into each transaction or add Legacy comparison fields as new costs.
- [ ] Missing values: count unknown/malformed/zero cost, duration and dates, blank IDs,
  unknown status and source metadata. Normalized nullable money is distinct from
  known zero; LegacyPartsCost/LegacyEstimatedTotalCost retain prior arithmetic for
  comparison only. Review null-dependent DAX behavior before migration.
- [ ] Dates/identifiers: retain text zeros, ISO dates and month semantics; verify
  last-day times, invalid dates, Unicode, quotations and multiline descriptions.
- [ ] Duplicates: identical raw reruns/renames skip, equal transaction values remain
  separate; only one current candidate per type/month is selected. Folder ingestion
  must reject two current CSVs with the same ReportMonth, even identical contents.
- [ ] Corrections: compare previous/proposed counts, exclusions/hours/costs; explicitly
  acknowledge the source-bound correction token; retain previous revision/packet.
  Revalidate corrected month against the business baseline before any later approval.
- [ ] Failure/recovery: changed source after preview, missing/tampered output,
  interrupted processing/export and unavailable sync file leave previous selections
  intact. Check partial results; do not assume a monthly run is transactional.
- [ ] Power BI reviewer: validate types, decimal precision, schema, row grain,
  relationships, DAX and visuals in a backup/copy; record expected versus actual
  monthly and grand totals and null/zero behavior.
- [ ] Departmental/finance data owner approves counts AND financial semantics;
  IT approves device, permissions, signing, retention and eventual storage controls;
  model owner approves query migration and refresh ownership. Approve production
  separately only after the future publisher/approval audit has been implemented.

## Unresolved repair-cost discrepancy — production blocker

The inspected January source reported totals disagree with the unchanged cleaner.
Textbox38 is used as PartsCost, while source Textbox38/Textbox16 observations call
that interpretation into question. Labor is derived from Details/default hours
and the existing 12.5 rate. Those meanings/rules are unresolved. No financial
mapping, formula, rate, exclusion or rounding change is authorized by this work.
Actual confidential totals are deliberately omitted.

Needed: trusted raw/cleaned repair pair, field definitions, comparable approved
labor/parts/estimated totals, duration/default/rate decisions and finance owner
approval. Then a separate reviewed change may resolve the discrepancy with explicit
approval and regression fixtures. Until then **no production publication**, even
if structural checks and all automated tests pass. Service/TMA also need trusted
expected outputs and baseline/schema approval. User-reported successful processing
establishes usability/compatibility evidence, not full production accuracy.
