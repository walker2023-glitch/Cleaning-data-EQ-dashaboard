# Milestone 3b final implementation design — approval pending

November 24, 2026. The owner selected **Option A** and approved fixed-local,
backup-PBIX-only product boundaries. This document finalizes a proposed implementation;
**schemas and reader contract still require owner approval**. No activation service,
selector, journal, hold, Settings migration or M wrapper is implemented here. The
[earlier architecture comparison](milestone_3b_proposal.md) remains context; this
specific proposal supersedes its illustrative schema names/fields if approved.

## 1. Reader decision and scope

**Recommended initial reader: canonical four-table `historical-powerbi-v1` only.**
The selector/Settings/root schema pins that contract. V1/V2/V3 comparison generation,
validation and helpers remain available unchanged outside this stable reader. V3 is
still a five-table DevelopmentComparison with explicit opt-in, not production approval.
Equipment_History.csv and V3 Building/EquipmentType/MaintenanceType are therefore NOT
provided by the initial stable reader. This prototype proves activation/recovery; it
does not claim a complete migration of the existing eight-object Power BI model.

Owner must approve canonical-only or request a revised explicit V3 profile before
implementation. Supporting both would require profile isolation, reader/schema changes
and distinct acceptance; do not add a format switch or infer it from filenames.
No authoritative approval/publishing API is called or enabled. `production_ready`
remains false; canonical outputs retain CandidateUnverified/NotApproved. A root named
“backup” cannot prove that a PBIX is a backup: employee declaration and departmental
policy remain required. No production destination, network/sync or automatic refresh.

## 2. Exact paths and immutable versions

Example configured fixed-local root `C:\EDM-Backup-Test` (chosen by employee, not
hardcoded). Relative layout uses `/` in JSON, native separators only when resolving:

```text
<root>/root.json
<root>/active.json                         absent before first confirmed activation
<root>/activation-journal.json             at most one pending operation
<root>/refresh-hold.json                   absent outside explicit manual refresh
<root>/.control/writer.lock                permanent 1-byte OS lock file
<root>/.tmp-<uuid4hex>.json                 exclusively owned metadata temp
<root>/versions/<version_id>/snapshot/     original exact six canonical files
<root>/versions/<version_id>/.s/           incomplete staging only; never read by M
<root>/history/<selection_id>.json         immutable complete binding (active schema)
<root>/journal-history/<operation_id>.json immutable terminal journal
```

No active/journal/hold/history file goes inside `snapshot`, preserving its exact
six-file contract. Completed versions are immutable **by application policy**, not
by pretending Windows directory read-only flags prevent same-user edits. Verify
hashes before use; external changes fail closed. Keep all completed versions and
selection/journal history; no retention deletion or automated pruning initially.

Version preparation imports one explicitly selected completed canonical snapshot
from the currently configured workspace (configuration fingerprint must match).
Revalidate/capture its six exact files. Require existing canonical contract values:
complete=true, stopped=false, production_ready=false, source_bytes_verified=false,
compatibility_gaps_acknowledged=true, CandidateUnverified/NotApproved, empty missing
selections/exclusions, original DatasetPlan fingerprint and valid canonical financial
schema. These are activation preflight rules, not changes to existing generated exports.
Copy stable verified bytes exclusively into
`versions/<uuid>/.s`, validate the original DatasetPlan fingerprint and reread hashes, recheck source evidence, then rename
`.s` to the previously absent `snapshot`. Never re-clean, recompute finances or change
candidate selections. The original output stays untouched. A crash leaving a complete
validated snapshot but no active selection does not activate it; it is merely an
explicitly selectable retained version. Partial `.s` is retained after abrupt death
and is ineligible; caught failures clean only their owned incomplete container.

Reject roots overlapping raw/candidates/reserved-approved, the application/source
installation or Settings directory (either ancestor direction). Apply current
fixed-disk, UNC/sync-root/name/reparse-point/symlink/junction/placeholder checks to
all existing ancestors and every accessed file; reject aliases to protected roots.
Recheck after lock acquisition and before mutation. All staging/control/version
paths must be on the same local volume. Keep current Windows UTF-16 path preflight;
no long-path policy changes. Do not rely on junctions or cross-volume replacement.

## 3. Normative proposed schemas and parsing

[The complete proposed JSON Schemas](milestone_3b_schemas.proposed.json) define the
exact five object types, required keys, enums and scalar types. They are documentation,
not application configuration or an executable implementation. No new dependency is
proposed; future validation uses explicit stdlib gates and these schemas as the spec.

| File/object | Schema discriminator | Purpose |
|---|---|---|
| root.json | edm-backup-root-v1 | Immutable root identity, fixed canonical reader contract |
| active.json, history entry | edm-backup-active-v1 | Root/version/selection IDs, monotonic generation, exact snapshot manifest digest and previous selection |
| activation-journal.json | edm-backup-journal-v1 | Operation ID/type/phase, complete old/new bindings and exact byte digests |
| refresh-hold.json | edm-backup-refresh-v1 | Root/selection/generation/binding digest and unique manual-refresh hold ID |
| Settings TOML encoded model | version = 3 | Existing folders/preferences plus local_backup_pbix configuration |

All metadata: strict UTF-8, maximum 64 KiB/file, JSON nesting maximum 16, duplicate
keys/non-finite constants/BOM/trailing garbage rejected. Required/unknown keys are
exact. Every integer requires `type(value) is int`, never bool or an integral float;
JSON Schema's mathematical integer interpretation alone is insufficient. Flags
require exact bool. No scalar coercion. UUIDs are lowercase RFC4122 uuid4 hex; hashes
are lowercase SHA-256; UTC timestamps use valid calendar instants with six fractional
digits and `Z`, never authority for ordering. Generation is 1..2,147,483,647; exhaustion
blocks rather than wraps. Strings are case-sensitive.

Writer encoding: sorted keys, compact separators, ensure_ascii=False, allow_nan=False,
UTF-8 plus exactly one LF. Hashes cover **those exact bytes including LF**. History
and selector contain identical bytes. External metadata with different whitespace
must not silently retain an old byte fingerprint; owner must re-review stale plans.

Cross-field invariants (mandatory in addition to schema):

- Root IDs match Settings/root/active/journal/hold/history. Contract is canonical-only.
- relative_snapshot is exactly `versions/<version_id>/snapshot`; no absolute path,
  drive, backslash, alternate stream, traversal or alternate ID. Resolve beneath root
  and validate links/volume again; manifest file names are existing fixed constants.
- First binding: generation 1 and previous_selection_id null. Later binding: old
  generation + 1 and previous_selection_id = old selection_id. Rollback ALSO creates
  a new selection/generation; never decrement or overwrite an old history entry.
- Rollback targets must be reachable through the committed active history chain;
  orphan pre-commit history records are not evidence of a prior active selection.
- Journal hashes equal canonical old/new bytes; old hash/binding are both null or
  both present. New selection ID is fresh; old/new root IDs equal root.json. Journal
  operation ID names its archive. Existing history collisions block; no overwrite.
- Hold selection/generation/digest equal the current active binding; binding_json_base64
  is the canonical Base64 encoding of its exact bytes (strict decode/reencode and digest
  verified by Python). It is redundant evidence, not authority for a different binding.
  Invalid hold or
  journal blocks mutation/refresh; absence is not inferred from a parse failure.
- Settings enabled=true requires a nonempty absolute validated root and matching
  non-null root_id. New disabled/unconfigured state has empty root and null ID;
  disabling a previously configured prototype retains root/ID and all stored data.

## 4. Lock and durable-write protocol

All mutations (root initialization, import, activation, rollback, hold begin/end,
recovery, root-setting changes) acquire the same root writer lock **nonblocking**.
Windows: fixed open fd, byte 0, `msvcrt.locking(..., LK_NBLCK, 1)`; Linux:
`fcntl.flock(..., LOCK_EX|LOCK_NB)`. Seek 0 and preallocate one byte during exclusive
root initialization; keep fd open for the full operation. Never unlink the lock file,
use PID-file freshness, timeouts or directory timestamps as ownership. Verify lock
file/path identity around acquisition; reject links and unsupported platforms.
Close releases the OS lock; process death releases it. Stale lock-file existence
alone is not “busy”. Locks coordinate cooperating EDM instances, not hostile writers.

Initialization uses exclusive mkdir/file creation with a trusted existing parent;
loser of concurrent initialization fails busy/uninitialized and retries validation,
never adopts partial metadata. No active selection is created during Settings save.

Metadata updates: exclusive temp in the same root, write/flush/fsync/read-back-check,
close handles, recheck expected-old digest and target paths, then `os.replace` of the
single file; reread and strictly verify after replacement. Keep recovery evidence.
File fsync plus same-volume replacement is not a universal power-loss/directory-
durability guarantee on Windows. Handle sharing violations/antivirus/access denial
as failures, never force-close another process, retry indefinitely or report success.
No multi-file replacement is described as atomic. Native failure tests are required.

## 5. Activation state transitions and confirmation

Session-only plan captures root/Settings identity, current selector bytes or confirmed
absence, target version/hash, full old/new coverage, record/revision differences,
warnings, operation and destination. Read-only preview may show busy/held state but
cannot authorize writes. Selection or evidence changes invalidate confirmation.
Every activation/rollback has final confirmation; replacements/removals additionally
require explicit displayed change consent. Employee action is not business approval.

Under the lock, with no hold/pending journal, freshly validate everything:

1. Same active version AND same manifest digest → No Update Needed, **no writes**.
2. Reserve fresh selection/operation IDs. Write immutable new history binding.
3. Write journal `prepared` with old/new binding bytes/digests.
4. Recheck old selector and target hashes. Replace active.json once: this is the
   selection commit point; no CSV moves or overwrites happen.
5. Verify new selector, history and completed target; journal → `selector_replaced`
   → `committed`. Write terminal archive exclusively/read-back verify, then remove
   only this operation's live journal. Return Saved only after verification/archival.

Before step 4 failure: old selector remains; retain diagnosable pending journal or
archive `aborted` once its unchanged-old state is verified. After step 4 error: report
**selection may have changed; recovery required**, never “nothing changed”. No new
manual refresh can begin while a journal remains. No silent automatic rollback,
activation of “latest”, deletion of prior versions or replay into candidate history.

## 6. Recovery and rollback

Startup checks this configured root under the lock before enabling prototype writes.
It does not scan folder ordering to choose an active version. Completed snapshots
remain available read-only even when state is blocked.

| Observed durable state | Behavior and explicit recovery action |
|---|---|
| No journal, valid active/history/version, no hold | Ready; normal preview required |
| No active/journal/history selection (new root) | Uninitialized selection; explicit first activation only |
| Prepared journal; active exactly old (or absent for first activation) | Prior state retained; offer confirmed Abort pending operation; archive aborted, keep all versions/history |
| Journal; active exactly new and all new evidence valid | Offer confirmed Finish recorded activation; archive committed, no selector change |
| Exact known selector/history, but selected version is corrupt/incomplete; a reachable committed previous version validates | Recovery Required; offer explicitly confirmed recovery rollback to that verified version, as a fresh generation; never auto-select it |
| Unknown/malformed selector, inconsistent history or unexpected phase/digest | Recovery Required; no automatic pointer repair or refresh. Retain evidence for authorized maintainer review |
| Valid persistent hold after restart | Refresh In Progress; never expire/clear automatically; finish via explicit hold protocol |
| Partial temp/.s or orphan history/version | Never use as active authority; retain for diagnosis. Valid complete unselected version may be explicitly selected later |

Initial prototype does **not** regenerate corrupt control metadata by guessing from
folders. Normal interruption yields verifiable old/new states; actual metadata loss
or external corruption requires a separately authorized maintainer repair. This is
a deliberate fail-closed limit, not a promise of universal automatic recovery.

Rollback chooses a verified retained history/version, previews its before/after
coverage and warnings, then uses the SAME transaction protocol with operation=rollback,
a fresh selection ID and incremented generation. It requires valid current metadata,
no refresh hold, final rollback confirmation and any removal/replacement consent.
If the old retained version is invalid, rollback is blocked; never silently choose
another version. No old snapshot/record is modified or deleted.

Recovery rollback may proceed when the current CONTROL binding/history are exact and
valid but its selected DATA version fails validation. Display current data as invalid/
not assessed, validate the explicitly chosen reachable prior version, and require
specific recovery/rollback confirmation. Archive any failed live journal as
recovery_required before preparing the new rollback journal under the same lock;
retain its old/new evidence. A crash between archival and new preparation leaves the
known invalid current version blocked, with the verified history chain still available
for the same explicit recovery. The new rollback uses current generation + 1 and the
usual commit protocol; it may not bypass invalid ROOT/SELECTOR/HISTORY metadata.
No normal activation or refresh is allowed while the current version is invalid.

## 7. Manual refresh hold and M wrapper

`Begin manual backup refresh`: acquire lock, require no journal/hold, strictly validate
root/active/history/version and hashes, then exclusively write/read-back verify hold
pinning that exact binding, including its complete exact bytes as binding_json_base64. Release lock. It launches or refreshes NOTHING.

While any hold exists, all cooperating app instances reject import/activation/
rollback/root-change mutations. `Finish manual refresh` requires expected hold ID,
unchanged active binding, fresh validation, and explicit employee confirmation that
all Power BI preview/refresh activity has finished or Desktop is closed. Remove only
that exact hold under lock. Crash does not clear it. A malformed hold is not removable
through a convenient reset button; it blocks and needs maintainer review.

Proposed NEW wrapper signature (not implemented):

```powerquery
fnReadLocalBackupActiveV1(VersionRoot as text, ReportKind as text,
                        AllowLocalBackupPrototype as logical) as table
```

Only ReportKind repairs/service_orders/tma_work_orders/repair_financial_summary and
explicit true are supported. No Equipment or V3 autodetection. Root is configured
once in a backup PBIX parameter. Wrapper reads root.json, active.json and hold,
checks fields/types/schema/root IDs/generation/relative path and binding match,
and compares Binary.ToText of the buffered active.json bytes (Base64) with the hold
record's binding_json_base64. Thus altered selector bytes, including equal-valued
numeric encodings, cannot pass merely through M numeric equality,
then invokes unchanged fnReadHistoricalSnapshot on that one snapshot with explicit
unapproved-backup opt-in. Use bounded nonrecursive root metadata listing to distinguish absent controls from
read/permission errors; do not recursively enumerate CSVs or turn read errors into
“missing”. Missing hold/active, journal present or inconsistent control
metadata yields an error, not an empty table or fallback. Force the returned table's
validation/materialization and recheck selector/hold identity before returning;
implementation must test actual lazy-evaluation behavior in Desktop.

A shared M query/Table.Buffer is NOT a model-wide snapshot lock. The persisted hold
is what prevents EDM selection changes across independently evaluated queries. M checks representable runtime types/integrality and exact selector-byte equality;
it does not independently reproduce the complete strict Python parser. M
cannot claim Python-equivalent SHA-256 verification; Begin refresh performed that
preflight. External same-user edits, out-of-procedure refresh and premature employee
release are outside the supported protocol. Do not claim Power BI process detection
or cryptographic reader enforcement. For query-editor previews, begin a hold too.

## 8. Settings migration and implementation slices

TOML version 3 represents the exact settings_v3 object in the proposed schema. Read
v1/v2 without writes, preserving all existing fields; prototype defaults disabled.
Ordinary old-behavior Save may remain version 2 until the employee explicitly enables
this feature. On first confirmed prototype Save, write an exclusive byte-exact
`settings.pre-v3.<uuid>.toml` backup beside Settings, then atomically save v3 using
existing SettingsStore safeguards. No automatic downgrade; older apps may reject v3
and must use documented manual profile restoration. Disabling retains root/history.
Changing root/disable is blocked while that root has a hold/journal/unverifiable state;
no copying or migration of active authority to a new root implicitly.

After approval AND merge of strict validation prerequisites, implement separate
reviewable slices: (1) strict control records/path/OS lock tests, (2) immutable import,
(3) confirmed selector transaction/history, (4) interruption recovery/rollback,
(5) hold and Settings/UI integration, (6) new canonical-only M wrapper and backup
Desktop validation, (7) native Windows packaging/failure matrix/docs. Keep existing
canonical/comparison helpers and financial/cleaning/classification code unchanged.
No dependency, network service or production publishing expansion is planned.

## 9. Approval questions and effort

Owner approval still required for the final five schemas and cross-field rules,
canonical-only initial reader/import scope, persistent hold/explicit manual recovery
limits, settings-v3 compatibility and backup policy. If V3 is required initially,
revise the reader/profile proposal before coding. These are explicit decisions,
not implementation guesses. No further architectural choice is delegated implicitly.

Expected effort: **6–9 engineering working days** including the strict control-state,
failure/concurrency tests, wrapper/UI/docs; add **1–2 Windows/employee acceptance days**
and model-owner availability. This refines the earlier 5–8 day sketch after specifying
hold/recovery/settings behavior. Strict validation PR work is separate and already
implemented for review. Unknown model redesign, production rollout and signed installer
work remain excluded. See [acceptance plan](milestone_3b_acceptance_plan.md) and
[exact next prompt](milestone_3b_next_prompt.md).
