# Exact next implementation prompt — send only after approval

This is a proposed future owner prompt, **not current authorization**. First review
and approve the final design, schemas, canonical-only reader and recovery limits.
The strict manifest PR must be reviewed/merged independently; no automatic merge.

Copy/send the following only if those decisions are accepted:

---

Equipment Data Manager — Implement Milestone 3b Local Backup-PBIX Prototype

I approve Option A as specified in
`docs/completion_readiness/milestone_3b_final_design.md`, including the exact proposed
schemas in `milestone_3b_schemas.proposed.json` with SHA-256
`17ef9618f79619df2be601d14d84bece8175d8cea81928ea696354ae6dd71663` and the acceptance plan. I approve the initial
**canonical four-table historical-powerbi-v1 reader only**, same-workspace immutable
snapshot import, persistent manual refresh hold, explicit rollback/recovery, Settings
v3/profile backup and the documented fail-closed maintainer boundary for corrupt metadata.
V1/V2/V3 comparison exports remain unchanged and are not promoted to production.

Fetch and verify latest remote main. Verify merged Milestone 3a, the owner-approved
strict manifest validation fix, and the reviewed design/schema content above. If a
prerequisite is absent or differs, report it; do not silently cherry-pick, merge or
change schemas. Start a NEW feature branch from verified main.

Implement only the approved root, immutable import, active selector/history,
activation journal, OS writer lock, persistent manual refresh hold, explicit rollback,
startup recovery, Settings migration and new canonical-only stable-root M wrapper.
Use the exact path/state/confirmation/validation protocol and failure tests. Preserve
all source/candidate/completed versions, finances, classifications, canonical and
V1/V2/V3 contracts. No unapproved dependencies, production/network/sync activation,
authoritative approval/publication, SharePoint access or automatic Power BI refresh.

Run the full regression suite, malformed-state/concurrency/crash-boundary tests,
source/wheel/native executable desktop/restart checks, native Windows failure matrix
and backup-PBIX procedure where available. Clearly separate automated, native, manual
and unavailable evidence. Push and prepare PR(s) for review; do not merge, deploy or
publish. Report commit SHA, test/build results, PR/compare links, migration/recovery
instructions and limitations. Stop for approval if the design, schemas, reader
contract, production boundary or dependency requirements must change.

---

If V3 or both readers are required initially, **do not send this prompt unchanged**.
Request/approve a revised profile/schema/reader plan first. Remaining effort is
6–9 engineering working days plus 1–2 Windows acceptance days and model-owner time;
that is a scope estimate, not an automatic production release promise.
