# Milestone 3b acceptance and Windows failure-injection plan

**Proposed tests, not executed activation evidence.** The activation manager, state
files, Settings migration and new wrapper do not exist yet. Existing strict manifest
fix tests/builds are reported separately; passing those does not validate this design.
Run this plan only after owner approval and implementation of the pinned schemas and
canonical-only reader. Use invented local workspaces and a backup/blank PBIX only.

## Automated invariants and failpoints

Every test verifies: original raw/candidate/source snapshots unchanged; every previously
completed version/history receipt retained; active selector either verified old or
verified new after a commit boundary; no successful refresh hold/reader on invalid
state; no unknown version selected; explicit confirmation and root writer lock required.

Future implementation should expose an injected test-only fault callback at named
boundaries. A subprocess worker reports a boundary through a private pipe; the parent
can deny the next filesystem call or terminate the child. No shipped environment
variable/backdoor, altered Power BI process or production path is used. Capture exit
code, exact control hashes, directory listing and recovered state privately. Use real
processes/native filesystem semantics in addition to mocked OSError unit tests.

| Test ID / failpoint | Injected condition | Required result and recovery |
|---|---|---|
| INIT-01 `root_before_metadata` | Kill after exclusive root/lock creation | No active selector; partial root not silently adopted; report uninitialized/maintenance needed |
| IMPORT-01 `copy_file_N` | Disk-full/access-denied after each of six copied files | Owned incomplete version cleaned on caught error; source and old completed versions untouched |
| IMPORT-02 `before_snapshot_rename` | Terminate process with validated `.s` | `.s` not eligible; never active; retain incomplete artifact for diagnosis |
| IMPORT-03 `after_snapshot_rename` | Terminate before any activation plan | Complete unselected version retained; no automatic activation |
| ACT-01 `before_history_write` | Access denied, no free space | Selector unchanged; no completed operation reported |
| ACT-02 `after_history_write` | Kill before journal write | Orphan receipt retained but never active/rollback authority |
| ACT-03 `journal_prepared` | Kill after durable prepared journal | Old selector retained (or absent initially); explicit Abort archives aborted |
| ACT-04 `before_selector_replace` | Alter current selector/target evidence | Stale rejection; no replacement of unexpected pointer |
| ACT-05 `selector_replace` | Native sharing violation/open handle/no delete-share | No force-close; old selector unchanged if replace failed; verified journal supports abort/recovery |
| ACT-06 `after_selector_replace` | Kill before phase update | New selector may be committed; startup recognizes exact new hash, offers Finish; no silent second activation |
| ACT-07 `after_selector_verification` | Fail journal phase/archival write | Report selection may have changed/recovery required; Begin refresh blocked |
| ACT-08 `after_archive_write` | Kill before live-journal removal | Matching terminal archive/live record handled idempotently after explicit recovery; versions retained |
| ACT-09 `post_replace_validation` | Corrupt new target externally | Fail closed; do not silently restore another pointer or report Saved |
| META-01 | Duplicate keys, NaN/Infinity, bool/int/float aliases, unknown keys/version, >64KiB/depth16, invalid dates/IDs/hash | Reject control metadata; no overwrite, fallback or “absent” coercion |
| PATH-01 | UNC, mapped/network/removable drive, OneDrive/sync, junction/reparse/placeholder, alternate stream, traversal, protected-root overlap | Preflight and locked recheck reject; no writes outside owned local test root |
| CONC-01 | Two processes activate from same expected-old plan | One lock winner; other Busy or stale; at most one generation committed |
| CONC-02 | Activation versus rollback/import/hold begin/Settings root change | Same lock arbitrates; holds/pending journals block forbidden mutations |
| CONC-03 | Kill lock owner; second process retry | OS lock releases; permanent lock-file existence is not stale ownership; recover journal before new write |
| HOLD-01 | Crash after hold write / app restart | Hold persists, activation remains disabled; explicit expected-ID finish required |
| HOLD-02 | Stale app finishes old hold ID or selector mismatch | Reject; newer hold cannot be removed |
| HOLD-03 | Truncated/invalid hold or journal | Fail closed, no reset/delete shortcut; maintainer review |
| ROLL-01 | Verified prior committed version | New generation/selection ID, explicit rollback and change consent; old records untouched |
| ROLL-02 | Missing/corrupt target or orphan history receipt | Rollback blocked; no alternate “latest good” choice |
| SET-01 | v1/v2 load and ordinary save | No activation/default root; unchanged existing preferences/workspace behavior |
| SET-02 | First v3 save failure after profile backup | Old Settings retained, exclusive original-byte backup verified; no implicit activation |
| SET-03 | Disable/root change during hold/journal | Block; retain old root/versions; no authority copied to a new root |
| UI-01 | No confirmation, changed plan/mode/range/root, cancellation | No activation; fresh complete review required |
| RESTART-01 | Valid idle/held/prepared/new-pointer/invalid states | Correct design-table state shown, no automatic refresh or activation |

Run the deterministic process-failure matrix on Linux and native Windows; run Windows
open-handle/no-delete-share, Defender/enterprise-policy observations and long-path
preflight separately. An OS process kill is not a power-loss test. Record actual
filesystem/OS results; do not generalize Linux rename success to Windows. Simulated
failures alone do not prove hardware durability. Test unclean reboot only on an
approved disposable VM, with permission and snapshots, not an employee workstation.

## Backup-PBIX verification procedure (after implementation)

1. Approve the canonical-only contract. Prepare a NEW invented workspace and fixed-local
   prototype root, root A and root B for negative tests. Keep production PBIX closed.
   Record app/executable revision/hash, root schema digest and four report kinds.
2. Generate two complete canonical snapshots with known month/count differences and
   one reviewed older-month correction, using the existing workflow. Verify hashes,
   counts, nulls and financial semantics before import. Keep originals read-only.
3. Enable the prototype in Settings with explicit confirmation. Import snapshot A into
   a new retained version. Confirm the exact first activation plan; inspect canonical
   root/active/history records and version digests with the app validator.
4. In a separately saved backup or blank PBIX, add the new `fnReadLocalBackupActiveV1`
   wrapper and the unchanged canonical helper. Set VersionRoot once. Create NEW,
   disconnected queries for repairs, service_orders, tma_work_orders and
   repair_financial_summary with explicit LocalBackupPrototype=true. Do not replace
   Equipment/Building_Dim/Requests/Work Order or existing DAX/relationships.
5. Without a hold, wrapper must error. Begin manual backup refresh in EDM, then refresh
   the four queries manually. Verify all read version A, correct nullable dates/numbers,
   text IDs, rows/repeats and separate financial measures. No automatic refresh occurs.
6. While the hold remains, a second EDM instance attempts activation of B and rollback:
   both block. Exercise separately evaluated queries, background query previews and
   repeated evaluations. Table.Buffer/shared queries are not assumed global locks.
7. Explicitly finish refresh only after all previews/refreshes complete or Desktop is
   closed. Preview/confirm activation of B. Begin a NEW hold; manual refresh must read
   B across all four tables without editing VersionRoot. Earlier A remains intact.
8. Finish hold, preview/confirm rollback to A (fresh generation), begin another hold
   and manually refresh. Counts/values return to A; B remains retained.
9. On disposable copies test mismatched root ID, missing control, invalid metadata,
   missing snapshot and altered counts/hashes: app preflight/reader must fail closed;
   no empty-table fallback or partial-success claim. Record actual Microsoft runtime
   errors instead of inferring them from Python tests.
10. Record pages, filter contexts, measures, precision/rounding and relationship impacts
    with model/finance owners. The current four-table prototype is not the full V3
    Equipment/mapping migration. Actual production rollout is a separate decision.

Release gate: complete regression + real native packaged smoke/restart, this failure
matrix, manual hold discipline, Settings migration/rollback-profile procedure, keyboard/
DPI/accessibility and explicit employee acceptance. Capture all limitations privately.
No production data, live publication, formal approval or SharePoint operation is tested.
