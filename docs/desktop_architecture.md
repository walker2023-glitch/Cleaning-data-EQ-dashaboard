# M2 local desktop architecture

This user-directed M2 milestone is the **offline desktop prototype**. The original
`design.md` M2 Graph integration is postponed; no Microsoft functionality is added.
The cleaning modules, calculations, exclusions and M1 version identity remain unchanged.

## Boundaries

- `ui/app.py`: CustomTkinter navigation, supported report cards, month confirmation,
  native file/folder dialogs, preview/results, explicit correction dialog, history
  and help. It does not contain cleaning transformations or direct SQL.
- `ui/workflow.py`: GUI-independent source selection and preview/run orchestration.
  `FileSource.read(SourceFile)` supplies bytes; `LocalFileSource` is the only live
  implementation. A future remote adapter needs separate authorization and tests.
- `ui/worker.py`: one non-daemon executor worker plus a queue. Workers do not call
  Tk. The main thread drains progress/completion/error events using `after`.
- M1 coordinator: its new `preview()` shares the exact processing decisions and
  transformations, but uses a read-only SQLite connection and returns before any
  artifact creation. A nonexistent store is not created by preview/history.
- M1 store: `history()` reads completed immutable revisions and their current/previous
  selection; no schema migration, date inference, failed-attempt log or new business
  interpretation is introduced.

Preview snapshots file hashes. Processing rereads each source into bytes and
requires the hash to match the preview before calling M1. Selected originals are
never moved or written. Different proposed contents for the same report/month
block the selection. Identical selections/contents do not create duplicate output.

The GUI records a replacement token **only after** the operator checks the
correction dialog's approval box and confirms. M1 rechecks current manifest state
under its transaction at processing time. Changed content, cleaner version or
current revision invalidates the approval. New/duplicate/correction/error statuses
are presented before processing; failed previews cannot be processed through the UI.
Outputs and History are labelled candidates, never production-validated.

Month, type, file or output-store changes invalidate preview and approval state.
Controls are disabled during work; overlapping jobs are rejected. Stop/close requests
cancel between files and let an active M1 operation finish. Completed batch files
are retained. Worker errors display safe generic messages without raw source data.
Results hold candidate bytes in memory; do not log/repr them or persist raw report
contents in diagnostics. History does not verify integrity merely by listing a row;
M1 verifies existing output hashes before skip/replacement decisions.

## Packaging

The desktop extra pins CustomTkinter/Pillow; the packaging extra pins PyInstaller.
The CLI still works without GUI dependencies. `equipment-data-manager-desktop`
is a GUI entry point; `packaging/desktop_entry.py` is the windowed executable entry.
PyInstaller uses onedir, retaining CustomTkinter assets, bundled synthetic samples,
and the three vendored `.py` resources required by M1's source-byte hashes.

`ui/smoke.py` launches the actual window and drives its preview/process buttons,
duplicate skip, explicit correction checkbox/button, prior-revision retention and
history against bundled synthetic data in an isolated diagnostic directory.
Windows CI builds the actual executable, runs this smoke check with a timeout and
checks its exit status plus the JSON outcome. This automated smoke does not replace
a manual accessibility/usability pilot or a managed-PC test without Python.

No local web server, Microsoft SDK, token cache, SharePoint path or Power BI change
is part of this milestone. See `windows_packaging.md` and `user_guide.md` for handoff.
