# Milestone 3b architecture proposal — approval required

**Owner decision update:** Option A and its local-backup product boundaries are now
selected. See [the exact final design](milestone_3b_final_design.md), proposed schemas
and acceptance plan for the remaining approval. The earlier fields below are an
architecture sketch, not the final schema. No activation implementation is included.

**Planning only. No implementation authorization or production activation.**
Baseline: merged 3a main b23a5e6. Employee need: stop manually repointing a backup
Power BI input while retaining a verified previous version and a clear recovery path.
Required next step toward the approved vision; estimated work is conditional below.

## Existing constraints and evidence

- `historical_dataset.py` creates a new six-file/four-table canonical snapshot,
  fsyncs exclusive file writes, validates `.s`, then renames into a previously absent
  `snapshot`. It does not replace an existing active directory.
- V3 is a five-table **DevelopmentComparison**, `CandidateUnverified/NotApproved`,
  `production_ready: false`. Its existing helper explicitly requires development
  opt-in. Selecting it locally cannot convert it into approved production data.
- `Settings` currently stores raw/candidate/reserved-approved roots and preferences;
  there is no stable dataset root or active-version authority. A new activation root
  requires an approved settings schema/migration, separate from candidate history.
- `review.ReviewService.approve/publish` explicitly reject authoritative actions.
  Local backup-PBIX binding must be approved as a separate operational action,
  retaining these restrictions. Do not repurpose reserved-approved storage or enable
  Publish/Approve to implement local selection.
- Reuse fixed-local/unsynced/UNC/link/reparse-point/overlap and Windows path checks.
  Require a dedicated fixed-local root outside raw/candidates/approved/production.
  Same-volume staging matters; no sync client, network share or cross-volume rename.
- The Python V3 scalar-type defect is known. A separately approved strict metadata
  validation fix, or an explicitly approved strict activation gate, is a prerequisite
  to trusting activation metadata. It is not silently fixed by this proposal.

## Option A — immutable versions and one stable selector (recommended prototype)

Keep completed, validated versions immutable under a dedicated local root. A small
`active.json` selects one relative version path and its manifest digest. Replace only
that selector through same-directory exclusive temp-write, flush/read-back/validation
and file replacement. Previous pointer/version stays available for recovery. Candidate
history and all existing export files/schemas remain untouched.

A NEW explicitly approved Power Query wrapper would resolve this selector and call
the existing typed canonical or V3 helper against that exact completed folder. Its
stable root parameter is configured once in a backup PBIX. Existing helpers stay
compatible. Python verifies hashes before declaring the selection ready; current M
helpers do not provide independent SHA-256 verification.

**Important limit:** a single file replacement is not a model-wide refresh transaction.
Power Query may evaluate different queries separately; a shared query/Table.Buffer
alone does not prove one global pointer read. Require a supported exclusive manual
refresh window: future app action freezes activation before the employee refreshes
Power BI manually; explicit completion releases it. Persist the hold conservatively
across app restarts; never clear it automatically after a crash. All cooperating EDM
instances respect it. Outside-procedure refreshes/external writers remain unsupported.
No automatic refresh or process-detection claim substitutes for this protocol.

Proposed records, **not implemented**:

| Record | Exact proposed fields / lifecycle |
|---|---|
| `active.json` | `schema: "edm-local-binding-v1"`, `purpose: "LocalBackupPBIXSelection"`, `generation` positive integer, `relative_version` traversal-free relative text, `output_contract` explicit canonical or V3 identifier, `manifest_sha256` 64-hex, `previous_binding_sha256` nullable 64-hex, `production_ready: false`; atomically replaced only after confirmed validation |
| `activation-journal.json` | `schema: "edm-local-journal-v1"`, `operation_id` UUID text, `old_binding` nullable complete binding, `new_binding` complete binding, `phase` one of `prepared/committed/recovery_required`; retained until post-replacement verification completes, then archived privately |
| `refresh-hold.json` | `schema: "edm-local-refresh-v1"`, `binding_sha256` 64-hex, `hold_id` UUID text, `state: "manual_refresh_in_progress"`; created before supported manual refresh, removed only by explicit employee completion/recovery |

A future settings migration adds only `local_test_activation_root` plus explicit
local-test acknowledgement; existing settings readers need a versioned migration,
not unknown-key tolerance. Owner must approve exact final schemas and reader behavior.
No dates/folder ordering become authority; output manifests keep their current status.

Concurrency: stdlib local OS lock for EDM writers, expected-old-binding digest check,
exclusive output containers and strict record types/paths. Lock/flush/replace behavior
must be verified natively on Windows, including open handles, antivirus and access
denial. Interrupted replacement does not justify claiming power-loss durability;
validate pointer, journal and both versions on startup. An inconsistent/unverifiable
state blocks activation/refresh and shows explicit recovery choices, never “latest”.

Rollback is an explicit confirmed selector change to a still-valid retained version,
with the same checks/refresh exclusion; it does not regenerate or delete history.
No automatic retention deletion in the first implementation.

**Tradeoff:** small activation write surface and easy rollback, but requires an
approved selector contract, new backup-PBIX reader setup and manual refresh exclusion.
It does not support unchanged literal CSV paths inside the current PBIX.

## Option B — stable literal CSV directory with journaled replacement

Stage and validate a complete sibling directory on the same local volume. With Power
BI closed/not refreshing and an exclusive application writer lock: journal intent,
rename the existing stable directory to a retained backup, rename staging to the
stable name, validate and commit. If the second rename fails, restore the verified
old directory. On interrupted startup reconcile the journal with validated directories;
never infer authority from directory dates. Rollback uses the same explicit process.

This keeps literal stable CSV paths and existing folder-based helper calls. However,
two renames leave a possible absent-directory interval. Four/five individual file
replacements would also expose mixed versions and are rejected as a design. Windows
may reject directory replacement/renames when handles/permissions interfere; do not
assume POSIX directory exchange or use a junction/symlink to bypass current checks.
Recovery can itself fail and must block rather than pretend the old output is active.
Require the same manual no-refresh window and explicit local-test permission boundary.
A reader must never silently consume a partially copied directory.

**Tradeoff:** less initial M connection change, more filesystem mutation, journal and
recovery complexity, disk-space overhead and a visible gap on crash/failure. Viable
for a controlled offline backup-PBIX prototype; no uninterrupted-reader guarantee.

## Recommendation, alternatives and decision

Recommend **A for a local backup-PBIX prototype**, with manual refresh hold and strict
validation. It changes one binding rather than replacing data in place and keeps
rollback simple. Choose B only if unchanged literal CSV paths are a confirmed hard
requirement and the owner accepts an offline maintenance window and recovery cost.
Doing nothing remains safe: 3a already creates complete versions; manually selecting
one for a backup PBIX avoids new activation state but retains monthly maintenance.

Before implementation, approve all of:

1. Prototype is local backup-PBIX selection only; formal production approval/publication
   remains disabled. A real production destination requires a later explicit decision.
2. Active reader contract: canonical four tables or explicitly opted-in V3 five-table
   development view. Do not silently promote V3 or drop Equipment by assuming canonical.
3. A versus B, stable root policy, refresh exclusion, record/settings schema and rollback.
4. Separately scoped strict manifest validation prerequisite and its regressions.
5. Retention (keep all initially), recovery authority, employee sign-off and test budget.

## Acceptance and effort

Both options must demonstrate new selection/identical no-op, exact before/after
coverage and revision review, explicit activation/removal/replacement/rollback consent,
source/baseline immutability, tamper/type/path rejection, old-binding compare-and-swap,
two simultaneous apps, disk full/access denied/open handle, every injected crash
boundary, startup recovery, invalid previous version, held-refresh rejection, and
manual Power BI refresh reading one intended complete generation. Test Windows and
Linux behavior separately; run actual M/DAX/visual comparisons in a backup PBIX.
No test touches departmental candidate stores or production.

Indicative engineering + automated testing: A **5–8 working days**, B **7–11 days**;
add **1–2 owner/Windows acceptance days** and availability for model validation.
Estimates include staged failure/recovery tests and docs, not departmental approvals,
unknown model redesign, shared storage, signing/installer procurement or production
rollout. Confirm architecture and model contract first; no deadline promise.

Online Python/Windows API reference retrieval returned HTTP 403 in this environment.
Filesystem claims are design constraints to verify against the installed/native
Windows APIs and failure tests before implementation; no native atomic-activation
experiment was performed during this documentation-only audit.
