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

## Departmental local workflow follow-up

The default desktop format is now normalized Power BI CSV candidate; injected
DesktopWorkflow callers and CLI retain legacy defaults. Folder configuration and
month discovery add a mixed-type selection mode; the visible checklist identifies
missing types. The worker handles discovery, mixed preview/process and explicit
review-packet export. Existing per-entry correction UI/tokens are reused; no
cleaning rule is implemented in the new event handlers. Changing report cards
leaves mixed mode, and changing month requires rescanning before mixed preview.
Single-file picker/history flows remain available. Choosing another output root
leaves workspace mode; loading a workspace always selects its normalized store.
Packets and outputs remain explicitly unapproved, and sync is never claimed.

A local full-suite correction test exposed a native CPython/Tk crash: automatic
cyclic GC invoked a Tk font finalizer on the pandas worker thread. The app now
disables automatic cyclic GC during the GUI lifetime and performs periodic cyclic
collection on the Tk/main thread (including while the worker is active). Normal
reference counting still operates. Closing joins the finished worker, collects
remaining cycles on the main thread and restores the prior GC setting. This
single-window process policy prevents automatic worker-thread Tcl finalization;
it does not modify pandas or cleaning behavior. A regression check verifies worker
GC state/main-thread collection and restoration. Fresh-process test isolation is
retained, with no failure retries or skipped cases.

## Visual settings and offline guidance

| File | New responsibility |
|---|---|
| settings.py | Versioned strict user preferences, legacy import parsing, atomic local saves, folder checks and conservative candidate-storage policy |
| ui/settings_page.py | Scrollable visual form, native Browse callbacks, readonly paths, validation indicators and pinned Save/Check/Reset actions |
| ui/preferences.py | SettingsMixin event orchestration: separate serial worker, first-run/startup validation, confirmed creation, apply/reset/import/template and coalesced help-preference writes |
| ui/help_content.py | Structured centralized brief/detailed/dashboard/affected-files/next-step/warning/guide registry |
| ui/guidance.py | Main-thread hover/focus timers, disabled-control bindings, bounded styled Tk popup and F1 alternative |
| ui/app.py | New Settings/navigation/global guide controls, state-aware help, adaptive compact layout and bindings to unchanged monthly workflow |
| resources/guides/user_guide.md | Exact offline copy of maintained employee instructions |
| ui/smoke.py | Actual-window settings/help exercises and a fresh-process persisted-startup check |
| packaging/EquipmentDataManager.spec, packaging/build.ps1 | Include offline guide resource and employee-facing supplementary guides in Windows distribution |
| tests/test_user_settings.py, tests/test_guided_help.py, tests/test_desktop_widgets.py | Settings safety, help contracts and real-window integration regressions |

Processing and settings have independent workers/queues. Workers never call Tk;
filesystem validation/creation and atomic preference writes run off the GUI thread.
Folder changes apply only after valid Save, clearing source/previews/correction
acknowledgements. Help-only preference writes preserve saved folder choices and
processing state; rapid changes coalesce into the latest serial write. While a
folder operation blocks settings changes, the global help toggle/manual Help
remain available. Closing waits for active work through deferred completion.

Normal startup loads/checks profile settings; explicit output-root/injected callers
preserve isolated M2 test/developer behavior. A --settings-file override exercises
full startup in a separate test profile. Corrupt configuration remains untouched
by automatic help-preference writes until explicit Save/Reset. Imported settings
are a draft and require local-storage reconfirmation. The old session-only loader
is retained in Advanced Settings and still checks candidate storage policy.

Settings persistence is a separate versioned file, not an engine manifest migration.
No cleaning adapter/calculation/schema, SQLite revision/correction logic or monthly
packet content contract is changed. No Microsoft or production publisher is added.
