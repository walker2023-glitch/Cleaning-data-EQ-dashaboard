"""Settings event handlers; filesystem operations use a separate serial worker."""
from dataclasses import replace
from pathlib import Path
from queue import Empty
from tkinter import filedialog, messagebox

from equipment_data_manager.monthly import Workspace
from equipment_data_manager.processing.models import ProcessingError
from equipment_data_manager.settings import (
    FOLDER_KEYS, SettingsStore, UserSettings, candidate_location_error,
    create_confirmed_folders, parse_settings, validate_locations,
)
from equipment_data_manager.ui.workflow import DesktopWorkflow
from equipment_data_manager.ui.worker import BackgroundWorker


class SettingsMixin:
    def initialize_settings(self, path):
        self.settings_store = SettingsStore(path)
        self.settings_worker = BackgroundWorker()
        self.saved_settings = UserSettings()
        self.settings_task = None
        self.pending_preferences = False
        self.preferences_writable = True

    def browse_setting(self, key):
        if self.worker.busy or self.settings_worker.busy:
            return
        chosen = filedialog.askdirectory(parent=self, title=f'Select {key.replace("_", " ")}', mustexist=False)
        if chosen:
            self.settings_page.path_vars[key].set(chosen)
            if key == 'candidate_folder':
                self.settings_page.local_confirmed.set(False)
            self.settings_page.message.configure(text='Folder choice changed. Check Locations, then Save Settings. Existing files will not be moved.')

    def use_recommended_candidate(self):
        if self.worker.busy or self.settings_worker.busy:
            return
        self.settings_page.path_vars['candidate_folder'].set(str(self.initial_output_root))
        self.settings_page.local_confirmed.set(False)
        self.settings_page.message.configure(text='Recommended local candidate folder selected. Confirm local storage, then Check Locations and Save Settings. Nothing is created until you confirm.')

    def settings_blocking(self):
        return self.settings_worker.busy and self.settings_task != 'preferences'

    def start_settings_job(self, kind, operation, snapshot=None):
        if self.settings_worker.busy:
            return False
        self.settings_task, self.settings_snapshot = kind, snapshot
        if self.settings_worker.start(lambda progress, stop: operation()):
            self.settings_page.busy(kind != 'preferences')
            if kind != 'preferences':
                self._busy_controls(True)
                self.settings_page.message.configure(text='Checking settings... Your existing reports stay unchanged.')
            return True
        return False

    def load_startup_settings(self):
        self.preferences_writable = False
        def load():
            settings = self.settings_store.load()
            return settings, validate_locations(settings) if settings else None
        self.start_settings_job('load', load)

    def check_settings(self):
        self.validate_settings_form('check')

    def save_settings(self):
        self.validate_settings_form('save')

    def validate_settings_form(self, intent):
        if self.worker.busy or self.settings_worker.busy:
            return
        snapshot = self.settings_page.snapshot()
        self.start_settings_job(intent, lambda: validate_locations(snapshot, probe=True), snapshot)

    def reset_settings(self):
        if self.worker.busy or self.settings_worker.busy:
            return
        if messagebox.askyesno('Reset application settings?',
                'Forget folder choices and restore Guided Mode Detailed and Power BI CSV Candidate? Your reports, history and review packets will not be moved or deleted.', parent=self):
            defaults = UserSettings()
            self.start_settings_job('reset', lambda: self._persist(defaults), defaults)

    def _persist(self, settings):
        settings=replace(settings,folders={k:str(Path(v).resolve()) if v.strip() else "" for k,v in settings.folders.items()})
        self.settings_store.save(settings)
        return settings

    def import_settings(self):
        if self.worker.busy or self.settings_worker.busy:
            return
        path = filedialog.askopenfilename(parent=self, title='Import local settings', filetypes=[('TOML settings','*.toml')])
        if path:
            path = Path(path)
            self.start_settings_job('import', lambda: parse_settings(path.read_text(encoding='utf-8'),base=path.resolve().parent))

    def export_settings_template(self):
        if self.worker.busy or self.settings_worker.busy:
            return
        target = filedialog.asksaveasfilename(parent=self,title='Export sanitized template',
            initialfile='equipment-data-manager-template.toml',defaultextension='.toml',filetypes=[('TOML template','*.toml')],confirmoverwrite=True)
        if target:
            path=Path(target)
            if path.suffix.lower() != '.toml' or path.resolve() == self.settings_store.path.resolve():
                self.settings_page.message.configure(text='Choose a separate .toml template file, not your active settings file.')
                return
            self.start_settings_job('template',lambda: SettingsStore(path).save(UserSettings()))

    def selected_period_or_saved(self):
        try:
            return self.period()
        except ProcessingError:
            return self.saved_settings.preferences.reporting_period

    def reporting_month_changed(self, *_):
        self.business_review_page.invalidate('Reporting month changed. Refresh review evidence before requesting approval.')
        if self._restoring_period:
            return
        self._period_user_changed = True
        try:
            self.period()
        except ProcessingError:
            self.status.set('Choose a valid month and four-digit year. The last saved reporting month was retained.')
            return
        self.status.set('Reporting month selected: '+self.period()+'. Refresh review evidence; confirm before processing.')
        # Do not create candidate/settings directories during write-free first-run
        # preview. Explicit setup/help save enables persistence on this profile.
        if self.settings_store.path.exists():
            self.pending_preferences = True
            self.flush_help_preferences()

    def restore_reporting_period(self, settings):
        period = settings.preferences.reporting_period
        if period and not self._period_user_changed:
            from equipment_data_manager.ui.app import MONTHS
            self._restoring_period = True
            try:
                self.month.set(MONTHS[int(period[5:])-1])
                self.year.set(period[:4])
            finally:
                self._restoring_period = False

    def help_preferences_changed(self, *_):
        self.guidance.hide()
        self.refresh_help()
        self.pending_preferences = True
        self.flush_help_preferences()

    def flush_help_preferences(self):
        if self.pending_preferences and not self.settings_worker.busy and not self.preferences_writable:
            self.pending_preferences=False
            self.settings_page.message.configure(text='Month and help preferences apply only to this session. Save valid Settings to remember them; the unreadable settings file was retained.')
            return
        if self.pending_preferences and not self.settings_worker.busy:
            self.pending_preferences=False
            settings=replace(self.saved_settings,preferences=replace(self.saved_settings.preferences,
                guided=self.guided.get(),detail=self.explanation_level.get().lower(),
                reporting_period=self.selected_period_or_saved()))
            self.start_settings_job('preferences',lambda: self._persist(settings),settings)

    def apply_workspace(self, workspace, output_format='powerbi'):
        self.workspace=workspace
        self.monthly_selection=None
        self.sources=self.previews=self.results=()
        self.approvals.clear()
        self.workflow=DesktopWorkflow(workspace.candidate_folder,output_format=output_format)
        self.business_review_page.invalidate('Folder settings changed. Refresh evidence for the current candidate folder.')
        self.output_format.set('Power BI CSV candidate' if output_format=='powerbi' else 'Legacy candidate')
        self._selection_changed()
        self.folder_label.configure(text=f'Local candidates: {self.workflow.output_root}')
        self.checklist.configure(text='Folders configured. Choose a month and Discover month. Outputs remain candidates; synchronization is unverified.')

    def apply_help_preferences(self, settings):
        if not self.pending_preferences:
            self.guided.set(settings.preferences.guided)
            self.explanation_level.set(settings.preferences.detail.title())
        self.guidance.hide()
        self.refresh_help()

    def poll_settings(self):
        try:
            while True:
                event=self.settings_worker.events.get_nowait()
                if event.kind == 'progress':
                    continue
                self.settings_worker.busy=False
                kind,snapshot=self.settings_task,self.settings_snapshot
                self.settings_page.busy(self.worker.busy)
                self._busy_controls(self.worker.busy)
                if event.kind=='error':
                    message='Settings could not be read or saved safely. The existing file was kept. Check permissions, or select folders and save again.'
                    if kind=='preferences':
                        message='Reporting month and help choices could not be saved. They apply only to this session; the previous settings file was kept. Check permissions, then Save Settings.'
                    self.settings_page.message.configure(text=message)
                    self.status.set(message)
                    if kind=='load':
                        self.show_page('Settings')
                        self.settings_page.welcome.configure(text='Welcome: set up your folders')
                elif kind=='load':
                    settings,check=event.payload
                    self.preferences_writable=True
                    if settings is not None:
                        self.saved_settings=settings
                        self.restore_reporting_period(settings)
                        self.settings_page.populate(settings)
                        self.apply_help_preferences(settings)
                        self.settings_page.show_check(check)
                    if settings is not None and check.valid:
                        self.apply_workspace(check.workspace, settings.preferences.output_format)
                        self.show_page('Process Reports')
                        self.status.set('Saved settings restored. Reporting month: '+self.month.get()+' '+self.year.get()+'. Confirm the source month before processing.')
                    else:
                        self.show_page('Settings')
                        self.settings_page.welcome.configure(text='Welcome: set up your folders' if settings is None or not all(settings.folders.values()) else 'Check your saved folder locations')
                        self.settings_page.message.configure(text='Before monthly discovery, Browse to your original reports, local candidate folder and reserved approved folder. Check Locations and Save Settings.' if settings is None else 'Saved choices were retained, but a folder is missing, inaccessible or not safely configured. Resolve the indicators, then save. No folder is created automatically at startup.')
                elif kind in ('check','save','create-check','create-save'):
                    check=event.payload
                    self.settings_page.show_check(check)
                    if check.missing:
                        locations='\n'.join(str(path) for path in check.missing)
                        if messagebox.askyesno('Create selected missing folders?',
                            'Create these folders? No existing files will be changed. The Approved folder is empty/reserved only; this does not publish reports.\n\n'+locations,parent=self):
                            next_kind='create-save' if kind in ('save','create-save') else 'create-check'
                            self.start_settings_job(next_kind,lambda s=snapshot: create_confirmed_folders(s),snapshot)
                        else:
                            self.settings_page.message.configure(text='Folders were not created and settings were not saved. Choose existing folders or confirm creation when ready.')
                    elif check.valid and kind in ('save','create-save'):
                        # Global help controls can change during validation; preserve
                        # their latest value without adopting unsaved folder edits.
                        snapshot=replace(snapshot,preferences=replace(snapshot.preferences,
                            guided=self.guided.get(),detail=self.explanation_level.get().lower(),
                            reporting_period=self.selected_period_or_saved()))
                        self.start_settings_job('commit',lambda s=snapshot:self._persist(s),snapshot)
                    else:
                        self.settings_page.message.configure(text='Locations checked. Save Settings to remember them.' if check.valid else 'Settings not saved. Resolve the folder indicators, then try again.')
                elif kind=='commit':
                    self.preferences_writable=True
                    self.saved_settings=event.payload
                    self.apply_workspace(Workspace(**{k:Path(v) for k,v in event.payload.folders.items()}),event.payload.preferences.output_format)
                    self.settings_page.welcome.configure(text='Settings')
                    self.settings_page.message.configure(text='Settings saved on this computer. No reports or history were moved.')
                    self.show_page('Process Reports')
                    self.status.set('Settings saved. Select the reporting month, then Discover month.')
                elif kind=='reset':
                    self.preferences_writable=True
                    self.saved_settings=event.payload
                    self.workspace=self.monthly_selection=None
                    self.sources=self.previews=self.results=()
                    self.approvals.clear()
                    self.workflow=DesktopWorkflow(self.initial_output_root,output_format='powerbi')
                    self.output_format.set('Power BI CSV candidate')
                    self.folder_label.configure(text=f'Local candidates: {self.workflow.output_root}')
                    self.month_confirmed.set(False)
                    self.settings_page.populate(event.payload)
                    self.apply_help_preferences(event.payload)
                    self.settings_page.welcome.configure(text='Welcome: set up your folders')
                    self.show_page('Settings')
                    self.settings_page.message.configure(text='Defaults restored. Your reports and history remain unchanged. Choose folders and save to begin again.')
                elif kind=='import':
                    imported=replace(event.payload,preferences=replace(event.payload.preferences,candidate_local_confirmed=False))
                    self.settings_page.populate(imported)
                    self.apply_help_preferences(event.payload)
                    self.show_page('Settings')
                    self.settings_page.message.configure(text='Imported as a draft. Check local candidate storage, Check Locations, then Save Settings to apply and remember these choices.')
                elif kind=='template':
                    self.settings_page.message.configure(text='Sanitized template exported with blank folders and default preferences. Actual paths and credentials are not included.')
                elif kind=='preferences':
                    self.saved_settings=event.payload
                self.flush_help_preferences()
                if self.close_pending and not self.worker.busy and not self.settings_worker.busy:
                    self._close()
                    return True
        except Empty:
            pass
        return False
