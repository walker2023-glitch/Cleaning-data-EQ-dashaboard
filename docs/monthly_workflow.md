# Monthly local workflow

This workflow produces **review candidates**, not approved production data. Power
BI CSV candidate is the desktop's recommended/default format; Legacy candidate
remains available. CLI and DesktopWorkflow API defaults stay legacy for backwards
compatibility. Cleaning calculations, date rules and exclusions are unchanged.

## Configure once

Copy `workspace.example.toml` to ignored `workspace.local.toml`, then edit its
three paths. Relative paths resolve beside the TOML file; absolute paths also
work. Do not commit departmental paths. Raw, candidate and reserved approved
folders must be separate, with no nesting/overlap, including resolved links.
The separate M0 `config.example.toml` remains offline-only and unchanged.

Arrange locally available inputs like this (filenames are unrestricted):

```text
raw_folder/
  2026-01/
    repairs/             one current raw CSV
    service_orders/      one current raw CSV
    tma_work_orders/     one current raw XLSX
  2026-02/...
candidate_folder/        trusted LOCAL disk, single operator
  powerbi_candidates/   SQLite + immutable candidate versions
  review_packets/       immutable, explicitly exported candidate snapshots
approved_folder/        reserved; NOT created or written by this application
```

Only direct CSV/XLSX files in the selected month/type folders are discovered.
Nested history, other months, temporary files and linked files are not ingested.
TMA `.xls` files are included only to show the specific unsupported-format error;
renaming XLS to XLSX does not convert it. Type/month folders are routing hints:
the real adapters still validate file contents and reporting periods. All three
report types are required for a complete review packet in this prototype; an
intentionally absent/zero-activity report needs a future approved completeness
policy. Do not invent blank reports to satisfy that gate.

## Employee monthly procedure

1. Open the application. Click **Load folder configuration**, select your local
   TOML file, then select the reporting month/year.
2. Click **Discover month**. Read the missing-report checklist and availability
   messages. Get the correct raw exports for missing types. Discovery does not
   download files or verify synchronization.
3. Check **I confirmed this reporting month**, then **Preview Processing**.
   Review every filename, type, month, count, exclusion trace and warning.
   If two different files claim one type/month, move the superseded input to a
   history subfolder outside the direct scan or use individual file selection.
   Preserve the originals according to your retention policy; the app never moves
   or edits them. Identical-content repeats safely skip.
4. Resolve invalid previews first. Missing types do not stop candidate processing
   of valid available types, but do stop exporting a complete packet. Review and
   explicitly acknowledge each potential correction with the existing dialog.
   Correction acknowledgement selects a **candidate revision**, not business approval.
5. Click **Process Reports**. Review Results; a run can partially succeed if a
   source becomes unavailable or changes after preview. Each file is independent;
   previously saved candidates remain intact. Re-preview after any failure.
6. After successful processing, click **Export review packet**. This reads the
   manifest-selected current candidates for the displayed month, requires all
   three types, verifies hashes/counts/schema, and copies them into a new folder.
   It does not export an unprocessed correction or promise an all-or-nothing
   monthly processing transaction. Check that you processed the intended inputs
   before export; export uses the last successful current candidates, even if a
   later processing attempt failed. The packet records revision IDs and hashes.
7. Find the packet under candidate_folder/review_packets/YYYY-MM-unique-id. Each
   report subfolder contains one header-first CSV. `packet.json` lists files,
   hashes, row counts and warnings, and explicitly says production_ready=false,
   sync_verified=false and CandidateUnverified. Re-export creates a separate
   packet; it never overwrites an earlier packet. Protect descriptions/names in
   these artifacts as departmental data. The employee guide remains applicable
   for single-file processing, history and local correction comparison.

Changing the month after discovery requires discovery again. Selecting individual
files leaves monthly selection mode; changing the output folder leaves configured
workspace mode. Format changes clear previews/approvals, and legacy mode cannot
export a standardized packet. Folder operations run on the existing worker so
slow file reads do not block the window. Cancellation is between cleaning files;
a discovery or packet write already underway finishes before the worker stops.

## Readiness language

| State | Meaning | Power BI use |
|---|---|---|
| Missing / rejected / correction unconfirmed | Selection or validation unresolved | None |
| Current candidate | Existing engine passed structural checks; warnings may remain | Private comparison only |
| Review packet | Complete three-type month copied from current manifest selections | Separate review PBIX only, explicit candidate mode |
| Approved production snapshot | NOT IMPLEMENTED; requires business/finance approval and future publisher | Production ingestion remains blocked |

No current file is production ready. The CSV shape is ready for review, but it
still carries CandidateUnverified. Never change that text manually to imply
approval. Local correction confirmation is not financial approval.

## Synced folders and recovery

Raw folders can point at an authorized locally available sync folder. Ensure files
are fully downloaded using the organization's approved sync-client procedure.
The app can confirm readable bytes and a stable preview hash, not OneDrive upload
completion, latest remote version, cloud ETag, tenant access or synchronization
health. Missing/unreadable/cloud-only files fail visibly; consult the sync client
and IT. Do not rename partial downloads into reports.

Keep SQLite/candidate state on a trusted local disk with one operator. Independently
synced SQLite stores do not provide shared locks and are unsupported. If IT permits,
copy a finished immutable review packet to a separate synced **candidate review**
location and verify cloud availability separately. Do not point the app's approved
folder at its raw/candidate roots or publish packets there. No sync-client SDK,
remote upload or sync-completion claim is present.

On damaged/missing existing outputs, retain the store and contact the maintainer;
do not delete the manifest to bypass integrity checks. A failed packet write removes
its staging directory; interruption can leave a hidden .staging directory, which
is never a completed packet. Snapshot rename is local only, not a cloud transaction.
Backup/retention, Windows junction/ACL policy and a second-PC recovery drill still
need departmental/IT validation. A trusted application-owned directory is required;
these checks are not a sandbox against malicious concurrent filesystem changes.
