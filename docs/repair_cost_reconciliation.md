# Repair-cost reconciliation — unresolved business gate

## Evidence and current behavior

Previously inspected January input has 29 retained repair records. Source summary
fields disagree with the unchanged cleaner's financial totals. The earlier private
inspection found both Textbox38 and Textbox16 sums equal the reported overall cost
in that sample (see format_compatibility.md). This calls the existing parts mapping
into question; it does **not** establish either field's business meaning. Private
amounts are deliberately absent here. No new source export or trusted expected
cleaned result has been provided for this pilot.

The preserved repairs_row_clean.py currently treats Textbox38 as parts, parses
Details into hours, calculates per-row labor as round(hours × 12.5, 2), and per-row
estimated total as round(parts + labor, 2). The preserved row_clean_common.py uses
0.5 hours for `found`, 1 hour for otherwise blank/unrecognized duration, fraction
and first-number heuristics, and malformed/missing money as zero. It may inspect
other cells for `found`. These are code observations, not approved finance policy.
Textbox16 is preserved as raw text, not interpreted as a charge.

The exact summary-layout adapter reads one consistent Total Labor/Parts/Cost and
repair count, checks the count against source records, and warns on disagreement.
It must not sum repeated summary cells across records. Normalized output retains
LegacyPartsCost/LegacyEstimatedTotalCost for exact comparison while PartsCost and
EstimatedTotalCost are null if source parts were missing/malformed. LaborCost is
still the original estimate. No formula, rate, rounding, default, mapping, date
rule or exclusion is changed by the pilot.

Possible explanations include an already-combined cost being counted as parts,
report totals using different scope or financial basis, and hours/rate/default
policy differences. These are hypotheses requiring evidence; do not fix by choosing
whichever field reproduces a total. Equal grand totals can conceal offsetting
parts/labor errors. The synthetic January case deliberately illustrates this.

## Decisions and evidence needed

| Decision | Evidence required | Owner / gate |
|---|---|---|
| What do Textbox38 and Textbox16 mean? | Report field definitions/version plus sanitized row-level raw/expected pairs, explicit zero/blank/credit examples | CompuClean report owner + finance |
| Are summary Labor/Parts/Cost actual, estimated, allocated, tax-inclusive, and in which units/currency? | Source report definition, one monthly total counted once, matching filter/date scope | Report owner + finance |
| Is Details elapsed time or person-hours? | Multiple technicians, fractions, found/blank/invalid examples and expected hours | Facilities owner |
| Are 12.5 rate, found=0.5, blank=1 and heuristics authorized? | Written policy/effective dates and approved baselines | Finance + Facilities |
| Where/when is rounding applied? | Per-row vs aggregate totals, decimal/fixed-decimal choice, tolerance and negative/refund policy | Finance + model owner |
| How should missing money affect measures? | Expected null/zero behavior and coverage indicators; existing DAX definitions | Finance + model owner |
| What counts as a repair and reporting month? | Row grain, exclusions, repeated events and corrected-month policy | Facilities + model owner |

For each approved-to-handle month, keep a private reconciliation packet containing
source fingerprints/layout/version, single source totals, raw/accepted/excluded
counts/reasons, original legacy totals, normalized known sums/null counts, existing
Power BI measure values/definitions/filter scope, explicit differences, reviewer
questions and decisions. Use the generated baseline CSV/report as the numerical
comparison, with evidence references to that packet. Never commit private reports,
finance values or employee descriptions to the public repository.

Until these decisions and trusted fixture comparisons are reviewed, costs remain
unverified candidates. Production migration is blocked. Any eventual mapping or
calculation change requires explicit approval and its own fixture-backed feature
branch; arithmetic agreement in this pilot is not that approval.
