# Maintenance matching, classification and review — future milestone

This document is a design, not an implemented matching/classification engine.
No class, heuristic score, automatic approval or employee identity capture is added
in this export milestone. SourceMaintenanceTag is literal source metadata only.

## Evidence and limitations

The original service cleaner removes trailing `- (PM)` and `- (Repair)` with
case-insensitive regexes, and removes placeholder/`delete duplicate...` records.
RawDescription must therefore survive separately before suffix stripping. A final
PM/Repair token can be recorded without asserting its business meaning. The
inspected January and February service samples have untagged descriptions; they
cannot establish tag reliability. Synthetic suffix examples test preservation, not label accuracy.

CompuClean repair/service inputs have equipment IDs and dates, descriptive text
and locations; services lack a structured shared work-order ID. The inspected
January sources have overlapping equipment/completion-date keys but also repeated
keys, so that key alone is not proof of a unique event. The TMA schema provides
Work Order #, Request Date, Requestor, Request and Assigned To, **no structured
equipment ID, location, service event ID or completion date**. A TMA request date
is not interchangeable with service completion. Text mentions may be clues but
are not verified keys. A matching TMA work order does not prove corrective repair;
even the repair report's title is not an approved class label.

## Separate matching from classification

Proposed stages:

1. Version inputs and assign source-revision record IDs. Preserve raw fields and
   business identifiers verbatim; do not silently strip zeros or join empty IDs.
2. Generate candidate links using exact equipment ID and compatible dates for
   CompuClean; optionally constrain verified locations. Exact work-order joins are
   allowed only when a verified shared identifier actually exists in both schemas.
3. Evaluate links using equipment identity, scheduled/completed/request date roles,
   exact/normalized text, location and time-window evidence. Text similarity is a
   ranking aid after identity/date evidence, not a stand-alone proof. Do not use
   requestor/assignee names as event identity keys.
4. Return matched-candidate, ambiguous, unmatched or conflicting link states with
   all relevant candidate IDs and evidence. Allow one-to-many/many-to-one links
   where business semantics require it; identical-looking transactions stay intact.
5. Classify from approved indicators and reviewed links, independently of whether
   a link exists. Store the class decision and link decisions separately.

Date windows must be approved per source pair. Start with exact same-day candidates
for CompuClean, flag cross-month records explicitly, and review boundary/backlog
cases before widening any window. Inspect adjacent monthly exports together but
retain each event's source period. A date-window limit is a candidate-generation
policy, never an exclusion from the exported source transaction table.

If introducing text normalization, retain original text, language/abbreviation
assumptions and version; do not drop negative phrases or meaningful equipment
numbers. A future heuristic score is an ordinal ranking/evidence-strength measure,
**not a calibrated probability**. Always show which attributes agree/disagree,
missing fields, date distance, candidate cardinality and rule version.

## Proposed deterministic classification policy

Categories: Preventive Maintenance, Corrective Repair, Other Maintenance,
Needs Review. The following rules require domain validation before implementation:

| Condition | Proposed suggestion / action |
|---|---|
| Conflicting source tags, manual evidence or competing event links | Needs Review; show conflict, never silently choose the highest score |
| Verified source PM indicator with no contradictory evidence | Preventive Maintenance; cite exact source cell and approved rule version |
| Verified Repair indicator or reviewed repair evidence demonstrating corrective work | Corrective Repair; cite indicator and human-approved meaning |
| Explicit approved evidence of maintenance outside PM/corrective taxonomy | Other Maintenance; require an approved reason code |
| No reliable indicator, only a TMA match, missing identifiers, ambiguous links or unvalidated suffix semantics | Needs Review; do not use Other Maintenance as a default bucket |

Until suffix meanings and source-report semantics pass a labeled validation gate,
PM/Repair tags are unverified evidence and should suggest review rather than
supply an automatic class. Negative/mixed examples are essential (PM work with a
TMA request, inspection followed by repair, duplicate descriptions for separate
visits). Matching a report called Repair is evidence to inspect, not ground truth.

## Employee review and overrides

Proposed review screen: service record with raw/cleaned description and dates,
suggested class, link state, explanation, all candidate links, contradictory/missing
evidence and previous human decisions. Filters: needs review, ambiguous, unmatched,
cross-month, changed source/rule, and high-impact cases. No color-only indicators.

A reviewer can approve/reject a link, approve/change a class, mark unresolved, and
record a reason. Capture reviewer identity via a future approved identity boundary;
an offline reviewer label is self-asserted, never described as authenticated. Store
review ID, source/linked revision hashes, original suggestion, chosen class,
reason, reviewer/time, rule/matching versions and superseded decision reference in
an append-only decision history. Restrict access to private text/employee fields.

Manual overrides take precedence for the exact reviewed revisions and remain
visible/auditable. A corrected source, changed candidate set, changed rule or stale
approval creates a re-review task; never carry an override onto a different event
solely because descriptions look similar. Preserve old overrides historically.
Export only explicitly approved decisions to a separate versioned classification
table keyed to source revision IDs; never overwrite the transaction source fields.
Publishing classifications inherits the financial/output approval gates and must
not imply approval of unrelated monetary values or of an entire month.

## Labeled evaluation and release gates

Obtain authorized manually labeled examples with a written class/link rubric and
adjudicate disagreements. Label matches (including no-match/ambiguous) separately
from maintenance classes. Include all months/source types, cross-month events,
leading-zero/absent IDs, repeat visits, tag-free/conflicting descriptions, unknown
locations, invalid dates and PM/TMA counterexamples. Keep private data out of Git.

Split evaluation by time/equipment/work-order groups to prevent the same event or
corrected export leaking between tuning and holdout sets. Compare a deterministic
baseline with any added text ranking. Report counts and uncertainty intervals,
per-class precision/recall and confusion matrix; link precision/recall, false
matches and missed links; unmatched/ambiguous rates; Needs Review coverage,
automatic-decision coverage and error rates; reviewer workload/time and override
rates. Review a sample of automatic decisions, not only the flagged queue.

Use adjudicated evidence and review outcomes to assess calibration only if a
future model explicitly claims probabilities; heuristic scores must not do so.
Document data limitations (especially TMA's missing structured equipment/event
keys and uncertain request-date semantics) alongside metrics. Domain owners must
set thresholds, acceptable false-link costs and pilot criteria **before** evaluating
the holdout set. Require an approved labeled holdout, explanation audit, override
replay/revision safety and employee pilot before enabling classifications. AI is
not proposed until deterministic behavior and labeled evidence justify a separate
reviewed milestone. No matching/classification code is delivered here.
