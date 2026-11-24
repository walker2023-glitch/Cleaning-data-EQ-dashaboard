# Documentation readiness, remaining effort and owner decisions

**Decision update:** Option A has been selected. Its [final implementation design](milestone_3b_final_design.md)
now estimates 6–9 engineering days plus Windows acceptance and still requires final
schema/reader approval. The older alternative-selection questions/estimates below
are preserved as the prior readiness audit, not a request to select A again.

Audit date November 24, 2026; main b23a5e6. This is a technical supplement.
The owner's separate master guide `docs/README.md` is intentionally **not rewritten**.
Its historical statements are identified below for later owner-controlled integration.

## Gaps and approved documentation work

| Area | Verified gap | Action in this preparation |
|---|---|---|
| Monthly update | Guide introduction still described an unmerged implementation | Add dated merged-status note; retain original approval limits and procedures |
| Windows packaging | Early current-sounding v2/phase-51 paragraphs coexist with old phase-30/36 history | Add authoritative current v3/phase-55 header; retain historical evidence below |
| Acceptance tooling | Intro says M2 not on main; runner paragraph describes phase 51 only | Clearly label original record as historical and document exact-SHA workflow plus phase 55 for 3a; preserve old-checkout phase-51 compatibility |
| Employee acceptance | Full technical steps exist but no short recorded-outcome checklist | New checklist with artifact identity, initial/add/retry/correct/rebuild/remove/stale/stop/restart and manual Windows gates |
| Failure recovery | 3a preserves `.s` but no active rollback exists | Link exact non-activation recovery procedure; 3b proposal explicitly separates version retention from active rollback |
| Power BI | Earlier canonical findings and older “no metadata” procedure can be misread; V3 has different names/lookup semantics | New evidence-tiered mapping with eight target objects, missing-model evidence and manual comparison gates |
| Owner master guide | `docs/README.md` line 117 says M2 branch remains ahead of main; baseline predates M2/3a | Record gap only. Owner may update after approved review; do not overwrite the seven-section project |
| Older monthly labels | `monthly_workflow.md` uses Historical Data; older guides name History/Review & Approval | Preserve historical sections. Use current-label crosswalk below; do not globally replace historical claims |
| Installation/handoff | Portable prototype build is documented; signing, installer policy, designated maintainer/escalation, managed-PC rollout and accessibility sign-off incomplete | Track as release/handoff acceptance tasks, not claims of an installer/departmental release |

Current verified labels for later integration:

- Navigation: Process Reports, Results, Process Multiple Months, Settings, Help.
- Earlier candidate revisions: Settings → Processing History.
- Multi-month candidates: Process Multiple Months → Batch processing.
- Hybrid output: Power BI snapshot → Monthly Historical Update; Choose completed
  baseline / Initial build (no baseline) / Choose new local output location /
  Review monthly update / Generate confirmed monthly update.
- Temporary comparison: Power BI snapshot → Development tools (show) → Create
  simplified comparison export. No permanent V1/V2/V3 UI selector.
- Review & Approval remains a hidden foundation, not a routine navigation step.

Test readiness: existing 25 monthly cases, four new widgets and all earlier tests
cover the approved behavior. Do not add duplicate tests solely to grow a count.
New activation/crash/rollback/reader-coordination tests belong to the **unapproved**
3b implementation. Existing type-defect regression documents current behavior;
changing its expectation requires the separately approved fix.

## Remaining work estimate

Indicative working effort, not elapsed delivery promises. Owner availability, access,
model size and IT procurement can dominate the critical path. Do not sum overlapping
acceptance days twice.

| Work | Engineering/testing estimate | Owner/department participation / gate |
|---|---:|---|
| 3a implementation/review prep | Complete, already merged PR #31 | 0.5–1 day employee Windows walkthrough; record exceptions |
| Strict manifest-type prerequisite | 0.5–1.5 days after scoped approval | Owner approves fix and malformed-input compatibility policy |
| 3b option A local backup-PBIX prototype | 5–8 days including tests/docs | 1–2 days Windows/recovery walkthrough; architecture/output contract approval first |
| Alternative 3b option B | 7–11 days **instead of A**, not additional | Accept maintenance window and more recovery complexity |
| Current model inventory + backup comparison | 2–4 technical days plus 1–3 validation days | Private model metadata, finance/model owners, full coverage and dimensions; no redesign allowance |
| Release/employee handoff hardening | 3–5 technical days plus 1–2 acceptance days | Maintainer, packaging/signing/install policy and managed-PC access |

For option A, approximately **11–19 engineering working days** remain after decisions
(0.5–1.5 + 5–8 + 2–4 + 3–5, rounded), plus overlapping owner/data validation. This is a
local prototype/handoff readiness estimate, **not production release certification**.
Shared/synced publication, automatic refresh, formal approval infrastructure,
installer procurement and unknown DAX/model redesign are excluded. Resolve actual
model blockers before quoting a production completion date.

## Recommended next owner decision

First record 3a employee acceptance. Then approve or revise the bounded 3b proposal:
local backup-PBIX binding only, option A versus B, canonical versus V3 reader contract,
strict validation prerequisite, refresh exclusion, settings/record schemas, retained
versions and explicit recovery authority. A general request to finish the product
must not be treated as permission to bypass these new state/production boundaries.

Independent work completed here: live state/merge/CI verification, code/spec audit,
full existing regression and synthetic acceptance, technical documentation corrections,
Windows checklist, two activation designs, eight-object mapping, gaps and estimates.
No independent application work remains under this authorization; stop for review.
