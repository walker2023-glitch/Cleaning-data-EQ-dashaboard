"""Real Tk widgets and M1 integration. Linux requires DISPLAY (xvfb-run in CI)."""

from pathlib import Path
from threading import Event
from time import monotonic

import pytest

from equipment_data_manager.processing.models import ProcessingStatus as Status, ReportType
from equipment_data_manager.ui.workflow import DesktopWorkflow
from equipment_data_manager.ui.app import EquipmentDataManager


def pump(app, predicate, timeout=8):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        app.update()
        if predicate():
            return
        Event().wait(0.01)
    raise AssertionError(f"Desktop condition timed out: {app.status.get()}")


@pytest.fixture
def app(tmp_path):
    window = EquipmentDataManager(tmp_path / "outputs", workflow=DesktopWorkflow(tmp_path / "outputs"))
    window.update()
    yield window
    if window.worker.busy:
        window.worker.stop()
        pump(window, lambda: not window.worker.busy)
    window._close()


def prepare(app):
    app.sample_button.invoke()
    app.month_confirmed.set(True)
    app.preview_button.invoke()
    pump(app, lambda: not app.worker.busy)


def test_launch_real_widgets_select_sample_preview_process_and_history(app):
    assert app.title() == "Equipment Data Manager"
    assert app.process_button.cget("state") == "disabled"
    prepare(app)
    assert app.previews[0].result.status == Status.SUCCESS
    assert not app.workflow.output_root.exists()
    assert app.process_button.cget("state") == "normal"
    row = app.table.item("0", "values")
    assert row[1:3] == ("Repair Reports", "2026-09")
    app.process_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.page == "Results"
    assert app.results[0].result.status == Status.SUCCESS
    assert "unverified" in app.detail.get("1.0", "end").lower() or "not been verified" in app.detail.get("1.0", "end")
    app.navigation["History"].invoke()
    pump(app, lambda: not app.worker.busy)
    assert len(app.history_table.get_children()) == 1


def test_file_picker_and_type_handling_use_real_service_engine(app, monkeypatch):
    fixture = Path(__file__).parent / "fixtures/synthetic/service_input.csv"
    monkeypatch.setattr("equipment_data_manager.ui.app.filedialog.askopenfilenames", lambda **kwargs: (str(fixture), str(fixture)))
    app.report_buttons[1].invoke()
    app.select_button.invoke()
    assert len(app.sources) == 1
    app.month.set("September")
    app.year.set("2026")
    app.month_confirmed.set(True)
    app.preview_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].report_type == ReportType.SERVICE_ORDERS
    app.process_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.results[0].result.status == Status.SUCCESS


def test_invalid_selection_and_month_give_actionable_feedback(app):
    app.preview_button.invoke()
    assert "Select local files" in app.status.get()
    app.sample_button.invoke()
    app.preview_button.invoke()
    assert "Confirm" in app.status.get()
    app.year.set("bad")
    app.month_confirmed.set(True)
    app.preview_button.invoke()
    assert "valid reporting month" in app.status.get()
    assert not app.worker.busy
    assert not app.workflow.output_root.exists()


def test_changed_selection_clears_preview_and_approval(app):
    prepare(app)
    app.approvals[0] = "synthetic-old-approval"
    app.month.set("October")
    assert app.previews == ()
    assert app.approvals == {}
    assert not app.month_confirmed.get()
    assert app.process_button.cget("state") == "disabled"


def test_repeated_run_is_skipped_and_correction_requires_dialog_checkbox(app, tmp_path):
    path = tmp_path / "raw.csv"
    app.sample_button.invoke()
    path.write_bytes(Path(app.sources[0].reference).read_bytes())
    app.set_files([str(path)])
    app.month_confirmed.set(True)
    app.start_preview()
    pump(app, lambda: not app.worker.busy)
    app.start_process()
    pump(app, lambda: not app.worker.busy)
    original = app.results[0].result.output_location
    app.show_page("Process Reports")
    app.start_preview()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].result.status == Status.SKIPPED
    path.write_bytes(path.read_bytes().replace(b"$10.00", b"$20.00"))
    app.start_preview()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].result.status == Status.NEEDS_REVIEW
    assert app.process_button.cget("state") == "disabled"
    app.review_button.invoke()
    app.update()
    assert app.dialog.confirm_button.cget("state") == "disabled"
    app.dialog.confirm_button.invoke()
    assert not app.can_process()
    app.dialog.confirmation_check.toggle()
    app.dialog.confirm_button.invoke()
    assert app.can_process()
    app.process_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.results[0].result.status == Status.SUCCESS
    assert original.is_file()
    assert original != app.results[0].result.output_location


def test_tma_rejects_compuclean_csv_even_programmatically(app):
    app.sample_button.invoke()
    app.report.set(ReportType.TMA_WORK_ORDERS.value)
    app.month_confirmed.set(True)
    app.start_preview()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].result.code == "unsupported_file_format"
    assert not app.can_process()
    app.start_process()
    assert not app.workflow.output_root.exists()


def test_long_running_operation_keeps_event_loop_responsive(app, monkeypatch):
    entered, release = Event(), Event()
    real_preview = app.workflow.preview

    def slow(*args):
        entered.set()
        assert release.wait(4)
        return real_preview(*args)

    monkeypatch.setattr(app.workflow, "preview", slow)
    app.sample_button.invoke()
    app.month_confirmed.set(True)
    app.start_preview()
    try:
        assert entered.wait(2)
        assert app.worker.busy
        assert app.select_button.cget("state") == "disabled"
        ticks = []
        app.after(50, lambda: ticks.append("main-thread-alive"))
        pump(app, lambda: bool(ticks))
        assert app.worker.busy
        app.stop_button.invoke()
        assert app.worker.cancelled.is_set()
    finally:
        release.set()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].result.code == "cancelled"
    assert not app.workflow.output_root.exists()


def test_worker_failure_is_recoverable_without_displaying_private_errors(app, monkeypatch):
    def failed(*args):
        raise ValueError("SYNTHETIC_PRIVATE_RAW_VALUE")

    app.sample_button.invoke()
    app.month_confirmed.set(True)
    with monkeypatch.context() as patch:
        patch.setattr(app.workflow, "preview", failed)
        app.start_preview()
        pump(app, lambda: not app.worker.busy)
    assert "SYNTHETIC_PRIVATE_RAW_VALUE" not in app.status.get()
    assert "could not finish" in app.status.get()
    assert app.process_button.cget("state") == "disabled"
    app.start_preview()
    pump(app, lambda: not app.worker.busy)
    assert app.can_process()


def test_close_during_work_defers_destroy_until_active_job_finishes(app, monkeypatch):
    # Exercise the close decision without destroying the fixture's window twice.
    app.worker.busy = True
    monkeypatch.setattr("equipment_data_manager.ui.app.messagebox.askyesno", lambda *args, **kwargs: True)
    app.request_close()
    assert app.close_pending
    assert app.worker.cancelled.is_set()
    assert app.winfo_exists()
    app.close_pending = False
    app.worker.busy = False


def test_february_service_export_previews_and_processes_all_five_records(app):
    path = Path(__file__).parent / "fixtures/synthetic/service_orders_february_2026.csv"
    app.report_buttons[1].invoke()
    app.set_files([str(path)])
    app.month.set("February")
    app.year.set("2026")
    app.month_confirmed.set(True)
    app.preview_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].result.code == "ready_to_process"
    assert app.previews[0].result.output_rows == 5
    assert app.process_button.cget("state") == "normal"
    app.process_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.results[0].result.status == Status.SUCCESS
    assert app.results[0].result.input_rows == app.results[0].result.output_rows == 5


def test_tma_xlsx_card_sample_picker_preview_and_process(app, monkeypatch):
    app.report_buttons[2].invoke()
    app.sample_button.invoke()
    path = Path(app.sources[0].reference)
    assert path.suffix == '.xlsx'
    assert app.month.get() == 'January'
    observed = {}

    def choose(**kwargs):
        observed.update(kwargs)
        return (str(path),)

    monkeypatch.setattr('equipment_data_manager.ui.app.filedialog.askopenfilenames', choose)
    app.select_button.invoke()
    assert '*.xlsx' in observed['filetypes'][0][1]
    app.month_confirmed.set(True)
    app.preview_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].result.output_rows == 3
    app.process_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.results[0].result.status == Status.SUCCESS
    assert 'tma_output_contract_provisional' in app.results[0].result.warnings


@pytest.mark.parametrize('kind,factory,code,trace', [
    (ReportType.REPAIRS, 'repair_csv', 'output_period_mismatch', "'2/15/2026' -> 2026-02-15"),
    (ReportType.SERVICE_ORDERS, 'service_csv', 'no_output_rows', "'2/15/2026' -> 2026-02-15"),
])
def test_rejection_detail_shows_engine_month_and_source_date_trace(app, tmp_path, kind, factory, code, trace):
    import report_samples
    source = tmp_path / 'synthetic.csv'
    source.write_bytes(getattr(report_samples, factory)(2, 3))
    app.report.set(kind.value)
    app.set_files([str(source)])
    app.month_selector.set('January')
    app.year.set('2026')
    app.month_confirmed.set(True)
    app.preview_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].period == '2026-01'
    assert app.previews[0].result.code == code
    detail = app.detail.get('1.0', 'end')
    assert 'Engine reporting month: 2026-01' in detail
    assert trace in detail and 'Record 1:' in detail
    assert app.process_button.cget('state') == 'disabled'
    assert not app.workflow.output_root.exists()


def test_tma_legacy_xls_filter_returns_useful_engine_error(app, tmp_path, monkeypatch):
    source = tmp_path / 'legacy.xls'
    source.write_bytes(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1SYNTHETIC-NOT-A-REAL-XLS')
    observed = {}

    def choose(**kwargs):
        observed.update(kwargs)
        return (str(source),)

    monkeypatch.setattr('equipment_data_manager.ui.app.filedialog.askopenfilenames', choose)
    app.report_buttons[2].invoke()
    app.select_button.invoke()
    assert observed['filetypes'] == [('TMA XLSX reports', '*.xlsx'), ('Legacy XLS (unsupported)', '*.xls')]
    app.month_selector.set('January')
    app.year.set('2026')
    app.month_confirmed.set(True)
    app.preview_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].result.code == 'legacy_xls_awaiting_sample'
    assert 'Do not rename' in app.detail.get('1.0', 'end')
    assert 'TmaXlsxCleaner' in app.runtime_info and 'January diagnostics v1' in app.runtime_info
    assert source.read_bytes().startswith(b'\xd0\xcf\x11\xe0')
    assert not app.workflow.output_root.exists()


@pytest.mark.parametrize('kind,factory,extension', [
    (ReportType.REPAIRS, 'repair_csv', 'csv'),
    (ReportType.SERVICE_ORDERS, 'service_csv', 'csv'),
    (ReportType.TMA_WORK_ORDERS, 'tma_xlsx', 'xlsx'),
])
def test_powerbi_output_mode_uses_real_cleaner_and_separate_candidate_history(app, tmp_path, kind, factory, extension):
    import csv
    from io import StringIO
    import report_samples
    source = tmp_path / f'synthetic.{extension}'
    raw = getattr(report_samples, factory)(1, 3)
    source.write_bytes(raw)
    base_root = app.workflow.output_root
    app.report.set(kind.value)
    app.set_files([str(source)])
    app.format_selector.set('Power BI CSV candidate')
    app._output_format_changed()
    assert app.previews == () and not app.month_confirmed.get()
    assert app.workflow.output_root == base_root / 'powerbi_candidates'
    app.month_selector.set('January')
    app.year.set('2026')
    app.month_confirmed.set(True)
    app.preview_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.previews[0].result.code == 'ready_to_process'
    assert 'production_publication_blocked' in app.previews[0].result.warnings
    assert app.format_selector.cget('state') == 'readonly'
    assert not base_root.exists()
    app.process_button.invoke()
    pump(app, lambda: not app.worker.busy)
    result = app.results[0].result
    assert result.status == Status.SUCCESS and result.output_rows == 3
    rows = list(csv.DictReader(StringIO(result.output_location.read_bytes().decode('utf-8'))))
    assert len(rows) == 3 and rows[0]['ReportMonth'] == '2026-01'
    assert rows[0]['ValidationStatus'] == 'CandidateUnverified'
    assert source.read_bytes() == raw
    app.format_selector.set('Legacy candidate')
    app._output_format_changed()
    assert app.workflow.output_root == base_root
    assert not (base_root / 'manifest.sqlite3').exists()
    assert not app.previews and not app.approvals and app.process_button.cget('state') == 'disabled'


def test_application_defaults_to_recommended_powerbi_candidates(tmp_path):
    import gc
    was_enabled = gc.isenabled()
    window = EquipmentDataManager(tmp_path / 'outputs')
    try:
        window.update()
        assert window.workflow.output_format == 'powerbi'
        assert window.output_format.get() == 'Power BI CSV candidate'
        assert not window.workflow.output_root.exists()
    finally:
        window._close()
    assert gc.isenabled() == was_enabled


def test_monthly_discovery_preview_process_export_and_missing_feedback(app, tmp_path, monkeypatch):
    from equipment_data_manager.monthly import Workspace
    from test_monthly_workflow import populate
    workspace = Workspace(tmp_path / 'raw', tmp_path / 'candidate', tmp_path / 'approved')
    populate(workspace)
    config = tmp_path / 'workspace.toml'
    config.write_text('raw_folder="raw"\ncandidate_folder="candidate"\napproved_folder="approved"\n')
    monkeypatch.setattr('equipment_data_manager.ui.app.filedialog.askopenfilename', lambda **kwargs: str(config))
    app.workspace_button.invoke()
    assert app.workflow.output_format == 'powerbi'
    app.month.set('January'); app.year.set('2026')
    app.scan_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert len(app.sources) == 3 and len(app.monthly_selection.missing) == 0
    assert 'Missing reports: none' in app.checklist.cget('text')
    assert {app.table.item(str(i), 'values')[1] for i in range(3)} == {'Repair Reports', 'Service Orders List', 'TMA Work Orders'}
    app.month_confirmed.set(True)
    app.preview_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert app.can_process() and len(app.previews) == 3
    app.process_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert len(app.results) == 3 and all(e.result.status == Status.SUCCESS for e in app.results)
    app.packet_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert 'Candidate review packet saved' in app.status.get()
    assert not workspace.approved_folder.exists()
    assert len(list((workspace.candidate_folder / 'review_packets').iterdir())) == 1
    app.month.set('February'); app.month_confirmed.set(True)
    app.start_preview()
    assert 'Discover month again' in app.status.get()
    app.scan_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert len(app.monthly_selection.missing) == 3
    assert 'Repair Reports' in app.checklist.cget('text')
    app.packet_button.invoke()
    pump(app, lambda: not app.worker.busy)
    assert 'all three current Power BI candidates' in app.status.get()
    assert not workspace.approved_folder.exists()


def test_monthly_configuration_and_discovery_errors_are_actionable(app, tmp_path, monkeypatch):
    app.scan_button.invoke()
    assert 'Load folder configuration first' in app.status.get()
    config = tmp_path / 'invalid.toml'; config.write_text('private_setting="SYNTHETIC_PRIVATE"')
    monkeypatch.setattr('equipment_data_manager.ui.app.filedialog.askopenfilename', lambda **kwargs: str(config))
    app.workspace_button.invoke()
    assert 'Invalid folder configuration' in app.status.get()
    assert 'SYNTHETIC_PRIVATE' not in app.status.get()
    assert app.workspace is None


def test_configured_workspace_rejects_raw_or_approved_output_destinations(app, tmp_path, monkeypatch):
    from equipment_data_manager.monthly import Workspace
    workspace = Workspace(tmp_path / 'raw', tmp_path / 'candidates', tmp_path / 'approved')
    app.workspace = workspace
    previous = app.workflow
    for folder in (workspace.raw_folder, workspace.approved_folder):
        monkeypatch.setattr('equipment_data_manager.ui.app.filedialog.askdirectory', lambda **kwargs: str(folder))
        app.folder_button.invoke()
        assert app.workflow is previous and app.workspace is workspace
        assert 'separate from the configured raw and approved' in app.status.get()
    assert not workspace.approved_folder.exists()


def test_cyclic_tk_finalizers_are_collected_on_gui_thread_during_work(app, monkeypatch):
    import gc
    from threading import get_ident
    # The full-suite correction run exposed a real native crash when pandas
    # allocation collected a Tk font on its worker. Keep GC ownership on the GUI.
    main_thread = get_ident()
    collected = []
    real_collect = gc.collect
    monkeypatch.setattr(gc, 'collect', lambda: (collected.append(get_ident()), real_collect())[1])
    assert not gc.isenabled()
    app._last_gc = 0
    assert app.worker.start(lambda progress, stop: (get_ident(), gc.isenabled()))
    event = app.worker.events.get(timeout=4)
    assert event.kind == 'done' and event.payload[0] != main_thread and not event.payload[1]
    app.worker.busy = False
    app._collect_gui_cycles()
    assert collected == [main_thread]


def wait_settings(app):
    pump(app,lambda:not app.settings_worker.busy and not app.pending_preferences)


def fill_settings(app,tmp_path,monkeypatch,*,create=True):
    from equipment_data_manager.settings import FOLDER_KEYS
    chosen={key:tmp_path / key for key in FOLDER_KEYS}
    for key,path in chosen.items():
        if create:path.mkdir(exist_ok=True)
        monkeypatch.setattr('equipment_data_manager.ui.preferences.filedialog.askdirectory',lambda **kwargs:str(path))
        app.settings_page.browse_buttons[key].invoke()
    app.settings_page.local_confirmed.set(True)
    return chosen


def test_settings_first_run_browse_confirm_creation_and_save(tmp_path,monkeypatch):
    from equipment_data_manager.settings import SettingsStore
    path=tmp_path / 'private/settings.toml'
    window=EquipmentDataManager(tmp_path / 'default-candidates',settings_path=path)
    try:
        wait_settings(window)
        assert window.page=='Settings' and 'Welcome' in window.settings_page.welcome.cget('text')
        assert window.guided.get() and window.explanation_level.get()=='Detailed'
        window.settings_page.recommended_button.invoke()
        assert window.settings_page.path_vars['candidate_folder'].get()==str(window.initial_output_root)
        assert not window.settings_page.local_confirmed.get()
        choices=fill_settings(window,tmp_path,monkeypatch,create=False)
        confirmations=[]
        monkeypatch.setattr('equipment_data_manager.ui.preferences.messagebox.askyesno',lambda *args,**kwargs:confirmations.append(args) or True)
        window.settings_page.save_button.invoke()
        wait_settings(window)
        assert len(confirmations)==1 and 'Create selected' in confirmations[0][0]
        assert window.page=='Process Reports' and 'Settings saved' in window.status.get()
        assert all(path.is_dir() for path in choices.values())
        assert list(choices['approved_folder'].iterdir())==[]
        saved=SettingsStore(path).load()
        assert saved.folders['candidate_folder']==str(choices['candidate_folder'])
        assert saved.preferences.candidate_local_confirmed
    finally:
        wait_settings(window);window._close()


def test_settings_and_guided_preferences_restore_after_restart(tmp_path,monkeypatch):
    path=tmp_path / 'private/settings.toml'
    first=EquipmentDataManager(tmp_path / 'defaults',settings_path=path)
    try:
        wait_settings(first)
        choices=fill_settings(first,tmp_path,monkeypatch)
        first.settings_page.preferred_format.set('Legacy candidate')
        first.settings_page.save_button.invoke();wait_settings(first)
        first.guided_switch.toggle()
        first.help_level.set('Brief');first.help_preferences_changed()
        wait_settings(first)
        assert not first.guided.get()
    finally:
        wait_settings(first);first._close()
    second=EquipmentDataManager(tmp_path / 'defaults',settings_path=path)
    try:
        wait_settings(second)
        assert second.page=='Process Reports'
        assert not second.guided.get() and second.explanation_level.get()=='Brief'
        assert second.workflow.output_format=='legacy'
        assert second.workspace.raw_folder==choices['raw_folder']
        assert second.settings_page.path_vars['approved_folder'].get()==str(choices['approved_folder'])
    finally:
        wait_settings(second);second._close()


def test_declined_folder_creation_and_invalid_locations_do_not_save(app,tmp_path,monkeypatch):
    choices=fill_settings(app,tmp_path,monkeypatch,create=False)
    monkeypatch.setattr('equipment_data_manager.ui.preferences.messagebox.askyesno',lambda *args,**kwargs:False)
    app.settings_page.save_button.invoke();wait_settings(app)
    assert not app.settings_store.path.exists()
    assert all(not path.exists() for path in choices.values())
    assert 'not created' in app.settings_page.message.cget('text')
    app.settings_page.path_vars['approved_folder'].set(str(choices['raw_folder'] / 'nested'))
    app.settings_page.save_button.invoke();wait_settings(app)
    assert 'separate' in app.settings_page.indicators['raw_folder'].cget('text')
    assert not app.settings_store.path.exists()


def test_corrupted_configuration_recovery_keeps_original_until_explicit_save(tmp_path,monkeypatch):
    path=tmp_path / 'settings.toml';path.write_text('INVALID SYNTHETIC CONFIG')
    app=EquipmentDataManager(tmp_path / 'defaults',settings_path=path)
    try:
        wait_settings(app)
        assert app.page=='Settings' and 'existing file was kept' in app.settings_page.message.cget('text')
        assert path.read_text()=='INVALID SYNTHETIC CONFIG'
        fill_settings(app,tmp_path,monkeypatch)
        app.settings_page.save_button.invoke();wait_settings(app)
        assert app.page=='Process Reports' and path.read_text().startswith('version = 2')
        assert app.settings_store.load().preferences.reporting_period==app.period()
    finally:
        wait_settings(app);app._close()


def test_saved_unavailable_folder_returns_to_setup_without_creating_it(tmp_path):
    from equipment_data_manager.settings import Preferences, SettingsStore, UserSettings, FOLDER_KEYS
    path=tmp_path / 'settings.toml'
    settings=UserSettings({key:str(tmp_path / key) for key in FOLDER_KEYS},Preferences(candidate_local_confirmed=True))
    SettingsStore(path).save(settings)
    app=EquipmentDataManager(tmp_path / 'defaults',settings_path=path)
    try:
        wait_settings(app)
        assert app.page=='Settings' and app.workspace is None
        assert 'Check your saved' in app.settings_page.welcome.cget('text')
        assert not any(Path(value).exists() for value in settings.folders.values())
        assert 'No folder is created automatically' in app.settings_page.message.cget('text')
    finally:
        wait_settings(app);app._close()


def test_reset_confirmation_preserves_reports_and_history(app,tmp_path,monkeypatch):
    from equipment_data_manager.settings import UserSettings
    choices=fill_settings(app,tmp_path,monkeypatch)
    original=choices['raw_folder'] / 'original.csv';original.write_bytes(b'SYNTHETIC ORIGINAL')
    history=choices['candidate_folder'] / 'history.txt';history.write_bytes(b'SYNTHETIC HISTORY')
    app.settings_page.save_button.invoke();wait_settings(app)
    before=app.settings_store.path.read_bytes()
    monkeypatch.setattr('equipment_data_manager.ui.preferences.messagebox.askyesno',lambda *args,**kwargs:False)
    app.settings_page.reset_button.invoke()
    assert app.settings_store.path.read_bytes()==before and app.workspace is not None
    monkeypatch.setattr('equipment_data_manager.ui.preferences.messagebox.askyesno',lambda *args,**kwargs:True)
    app.settings_page.reset_button.invoke();wait_settings(app)
    assert app.workspace is None and app.page=='Settings'
    assert app.settings_store.load()==UserSettings()
    assert original.read_bytes()==b'SYNTHETIC ORIGINAL' and history.read_bytes()==b'SYNTHETIC HISTORY'
    assert app.guided.get() and app.explanation_level.get()=='Detailed'


def test_advanced_import_is_draft_until_saved_and_template_omits_private_paths(app,tmp_path,monkeypatch):
    path=tmp_path / 'legacy.toml'
    path.write_text('raw_folder="raw"\ncandidate_folder="candidate"\napproved_folder="approved"')
    monkeypatch.setattr('equipment_data_manager.ui.preferences.filedialog.askopenfilename',lambda **kwargs:str(path))
    app.settings_page.import_button.invoke();wait_settings(app)
    assert app.workspace is None and app.page=='Settings'
    assert app.settings_page.path_vars['raw_folder'].get()==str(tmp_path / 'raw')
    assert not app.settings_page.local_confirmed.get() and 'draft' in app.settings_page.message.cget('text')
    assert not app.settings_store.path.exists()
    template=tmp_path / 'sanitized.toml'
    monkeypatch.setattr('equipment_data_manager.ui.preferences.filedialog.asksaveasfilename',lambda **kwargs:str(template))
    app.settings_page.export_button.invoke();wait_settings(app)
    assert str(tmp_path) not in template.read_text() and 'raw_folder = ""' in template.read_text()


def test_known_sync_folder_cannot_be_saved_in_gui(app,tmp_path,monkeypatch):
    choices=fill_settings(app,tmp_path,monkeypatch)
    monkeypatch.setenv('OneDriveCommercial',str(choices['candidate_folder']))
    app.settings_page.save_button.invoke();wait_settings(app)
    assert not app.settings_store.path.exists() and app.workspace is None
    assert 'OneDrive' in app.settings_page.indicators['candidate_folder'].cget('text')


def test_folder_save_failure_preserves_previous_configuration_and_active_workspace(app,tmp_path,monkeypatch):
    fill_settings(app,tmp_path,monkeypatch)
    app.settings_page.save_button.invoke();wait_settings(app)
    before=app.settings_store.path.read_bytes();workspace=app.workspace
    def fail(*args):raise PermissionError('SYNTHETIC_PRIVATE_ERROR')
    monkeypatch.setattr('equipment_data_manager.settings.os.replace',fail)
    app.settings_page.save_button.invoke();wait_settings(app)
    assert app.settings_store.path.read_bytes()==before and app.workspace is workspace
    assert 'existing file was kept' in app.settings_page.message.cget('text')
    assert 'SYNTHETIC_PRIVATE' not in app.settings_page.message.cget('text')


def test_guided_mode_and_detail_changes_do_not_invalidate_preview_or_change_outputs(app):
    prepare(app)
    entries=app.previews
    candidate=entries[0].result.cleaned.output_bytes
    app.guided_switch.toggle()
    app.help_level.set('Brief');app.help_preferences_changed();wait_settings(app)
    assert app.previews is entries and app.can_process() and app.month_confirmed.get()
    assert not app.guided.get()
    app.process_button.invoke();pump(app,lambda:not app.worker.busy)
    assert app.results[0].result.cleaned.output_bytes==candidate
    assert app.settings_store.load().preferences.detail=='brief'
    assert app.settings_store.load().preferences.guided is False


def test_disabled_control_hover_focus_and_f1_help_work_without_changing_selection(app):
    assert app.process_button.cget('state')=='disabled'
    app.guidance.schedule(app.process_button,'process')
    pump(app,lambda:app.guidance.popup is not None)
    assert 'confirm' in app.guidance.text('process') or 'Preview' in app.guidance.text('process')
    assert app.previews==() and not app.can_process()
    app.guidance.hide()
    app.process_button.focus_force();app.update()
    assert app.guidance.key=='process'
    app.event_generate('<F1>');app.update()
    assert app.page=='Help' and 'Process Reports' in app.help_text.get('1.0','end')
    assert 'confirm' in app.help_text.get('1.0','end')


def test_guided_off_hides_automatic_tips_but_keeps_keyboard_and_topic_help(app):
    app.guided_switch.toggle();wait_settings(app)
    app.guidance.schedule(app.preview_button,'preview')
    assert app.guidance.pending is None and app.guidance.popup is None
    app.event_generate('<F1>');app.update()
    assert app.page=='Help'
    app.help_topic_picker.set('Legacy CSV');app.refresh_help()
    assert 'introductory rows' in app.help_text.get('1.0','end')
    app.show_employee_guide()
    assert 'Equipment Data Manager' in app.help_text.get('1.0','end')


def test_tooltip_brief_detailed_and_screen_edges(app):
    app.explanation_level.set('Brief')
    brief=app.guidance.text('preview')
    app.explanation_level.set('Detailed')
    detailed=app.guidance.text('preview')
    assert len(detailed)>len(brief) and 'Files and information:' in detailed and 'Next:' in detailed
    app.guidance.schedule(app.output_button,'output');app.guidance.show();app.update()
    popup=app.guidance.popup
    assert popup.winfo_rootx()>=0 and popup.winfo_rooty()>=0
    assert popup.winfo_rootx()+popup.winfo_width()<=app.winfo_screenwidth()
    assert popup.winfo_rooty()+popup.winfo_height()<=app.winfo_screenheight()


def test_context_help_explains_missing_sources_and_current_failure(app,tmp_path):
    from equipment_data_manager.monthly import MonthlySelection
    app.monthly_selection=MonthlySelection('2026-01',(),())
    app.workspace=__import__('equipment_data_manager.monthly',fromlist=['Workspace']).Workspace(tmp_path/'raw',tmp_path/'candidate',tmp_path/'approved')
    context=app.guidance.text('discover')
    assert 'CompuClean Repair Report' in context and 'Tim' in context and 'XLSX' in context
    app.monthly_selection=None
    source=tmp_path/'unsupported.xls';source.write_bytes(b'SYNTHETIC XLS')
    app.report.set(ReportType.TMA_WORK_ORDERS.value)
    app.set_files([str(source)]);app.month.set('January');app.year.set('2026');app.month_confirmed.set(True)
    app.start_preview();pump(app,lambda:not app.worker.busy)
    assert 'Legacy XLS' in app.guidance.text('status') and 'Do not rename' in app.guidance.text('status')


def test_slow_settings_check_keeps_window_responsive(app,tmp_path,monkeypatch):
    from equipment_data_manager.settings import validate_locations
    fill_settings(app,tmp_path,monkeypatch)
    entered,release=Event(),Event()
    def slow(*args,**kwargs):
        entered.set();assert release.wait(5)
        return validate_locations(*args,**kwargs)
    monkeypatch.setattr('equipment_data_manager.ui.preferences.validate_locations',slow)
    app.settings_page.check_button.invoke()
    try:
        assert entered.wait(2)
        ticks=[];app.after(30,lambda:ticks.append(True))
        pump(app,lambda:bool(ticks))
        assert app.settings_worker.busy and app.settings_page.save_button.cget('state')=='disabled'
        assert app.preview_button.cget('state')=='disabled'
        app.guided_switch.toggle()  # Help is usable while a folder check is active.
        assert not app.guided.get()
    finally:
        release.set()
    wait_settings(app)
    assert app.settings_store.load().preferences.guided is False


def test_keyboard_activation_handles_help_toggle_and_respects_disabled_processing(app):
    app.guided_switch.focus_force();app.update()
    app.guided_switch.event_generate('<KeyPress-space>');app.update();wait_settings(app)
    assert not app.guided.get()
    app.process_button.focus_force();app.update()
    app.process_button.event_generate('<KeyPress-space>');app.update()
    assert not app.worker.busy and not app.workflow.output_root.joinpath('manifest.sqlite3').exists()


def test_guided_toggle_does_not_replace_unreadable_configuration(tmp_path):
    path=tmp_path / 'broken.toml';path.write_bytes(b'CORRUPT SYNTHETIC SETTINGS')
    app=EquipmentDataManager(tmp_path / 'defaults',settings_path=path)
    try:
        wait_settings(app)
        app.guided_switch.toggle();wait_settings(app)
        assert not app.guided.get()
        assert path.read_bytes()==b'CORRUPT SYNTHETIC SETTINGS'
        assert 'this session' in app.settings_page.message.cget('text')
    finally:
        wait_settings(app);app._close()


def test_tooltip_stays_visible_when_anchor_is_outside_screen(app,monkeypatch):
    # Windows CI exposed an anchor whose initial window extended past a short
    # display. The popup must clamp independently of the anchor's placement.
    monkeypatch.setattr(app.output_button,'winfo_rooty',lambda:app.winfo_screenheight()+40)
    app.guidance.schedule(app.output_button,'output');app.guidance.show();app.update()
    popup=app.guidance.popup
    assert popup.winfo_rooty()>=0
    assert popup.winfo_rooty()+popup.winfo_height()<=app.winfo_screenheight()


def test_restart_smoke_does_not_close_root_during_windows_startup_pump(tmp_path,monkeypatch):
    """Reproduce CTk's Windows pre-mainloop update using the real Tk window."""
    import customtkinter as ctk
    from equipment_data_manager.settings import FOLDER_KEYS,Preferences,SettingsStore,UserSettings
    from equipment_data_manager.ui.smoke import run_restore_smoke
    choices={key:str(tmp_path/key) for key in FOLDER_KEYS}
    for folder in choices.values():Path(folder).mkdir()
    path=tmp_path/'settings.toml'
    SettingsStore(path).save(UserSettings(choices,Preferences(False,'detailed','powerbi',True)))
    real_after=EquipmentDataManager.after
    real_mainloop=ctk.CTk.mainloop
    def immediate_check(self,delay,func=None,*args):
        return real_after(self,0 if getattr(func,'__name__','')=='check' else delay,func,*args)
    def startup_pump(self,*args,**kwargs):
        if not self._window_exists:
            # CTk's Windows titlebar path pumps events before querying wm state.
            self.tk.call('update')
            self.tk.call('wm','state',self._w)
        return real_mainloop(self,*args,**kwargs)
    monkeypatch.setattr(EquipmentDataManager,'after',immediate_check)
    monkeypatch.setattr(ctk.CTk,'mainloop',startup_pump)
    assert run_restore_smoke(path,tmp_path)==0
    import json
    assert json.loads((tmp_path/'restore-smoke.json').read_text())['passed'] is True


def test_storage_connection_status_is_honest_and_graph_never_activates(app):
    from equipment_data_manager.ui.help_content import HELP
    app.show_page('Settings');app.update()
    page=app.settings_page
    assert 'unverified' in page.connection_status.cget('text')
    assert page.graph_button.cget('state')=='disabled'
    page.busy(True);page.busy(False)
    assert page.graph_button.cget('state')=='disabled'
    text=HELP['storage_connection'].text()
    assert 'offline-tested foundation only' in text and 'No candidate is uploaded' in text


def prepare_business_review(app, tmp_path):
    from test_powerbi_readiness import build
    workspace, _, _, _, _ = build(tmp_path/'synthetic-review')
    app.workspace = workspace
    app.workflow = DesktopWorkflow(workspace.candidate_folder, output_format='powerbi')
    app.month.set('January'); app.year.set('2026')
    app.navigation['Review & Approval'].invoke()
    app.business_review_page.load_button.invoke()
    pump(app, lambda:not app.worker.busy)
    return workspace, app.business_review_page


def test_business_review_real_engine_evidence_and_local_request_stay_unapproved(app, tmp_path):
    workspace, page = prepare_business_review(app,tmp_path)
    assert app.page == 'Review & Approval'
    text = page.evidence.get('1.0','end')
    assert '3 retained / 3 source rows' in text and 'ReportedTotalCost' in text
    assert 'source_sha256' in text and 'summary_sha256' in text and 'Missing values' in text
    assert page.request_button.cget('state') == 'normal'
    page.note.insert(0,'Synthetic independent count checks')
    page.request_button.invoke()
    pump(app,lambda:not app.worker.busy)
    assert 'ReviewRequestedLocallyNotSent' in page.evidence.get('1.0','end')
    assert page.approve_button.cget('state') == page.publish_button.cget('state') == 'disabled'
    assert page.service().history()[0]['approval'] is None
    assert not workspace.approved_folder.exists()
    page.history_button.invoke()
    assert 'unavailable' in page.evidence.get('1.0','end')
    assert 'does not assert' in page.evidence.get('1.0','end')


def test_business_review_handles_missing_month_workspace_and_stale_source(app,tmp_path):
    page=app.business_review_page
    app.show_page('Review & Approval'); page.load_button.invoke()
    assert 'Save folder settings' in page.evidence.get('1.0','end')
    workspace,page=prepare_business_review(app,tmp_path)
    app.month.set('March'); page.load_button.invoke(); pump(app,lambda:not app.worker.busy)
    assert 'repairs, service_orders, tma_work_orders' in page.evidence.get('1.0','end')
    assert page.request_button.cget('state')=='disabled'
    app.month.set('January'); page.load_button.invoke(); pump(app,lambda:not app.worker.busy)
    source=workspace.raw_folder/'2026-01/repairs/raw.csv'
    source.write_bytes(source.read_bytes().replace(b'$10.00',b'$11.00'))
    page.note.insert(0,'Synthetic evidence')
    page.request_button.invoke(); pump(app,lambda:not app.worker.busy)
    assert 'original raw file changed' in app.status.get()
    assert page.request_button.cget('state')=='disabled'
    assert page.publish_button.cget('state')=='disabled' and page.service().history()==[]


def test_business_review_background_operation_remains_responsive_and_fails_safely(app,tmp_path,monkeypatch):
    _,page=prepare_business_review(app,tmp_path)
    from equipment_data_manager.review import ReviewService
    from equipment_data_manager.processing.models import ProcessingError
    entered,release=Event(),Event()
    def blocked(self,period):
        entered.set()
        assert release.wait(5)
        raise ProcessingError('review_candidate_contract_rejected')
    monkeypatch.setattr(ReviewService,'capture',blocked)
    page.load_button.invoke()
    pump(app,entered.is_set)
    ticks=[];app.after(0,lambda:ticks.append(True));app.update()
    assert ticks and app.worker.busy
    assert page.request_button.cget('state')==page.publish_button.cget('state')=='disabled'
    release.set();pump(app,lambda:not app.worker.busy)
    assert 'failed monthly review checks' in page.evidence.get('1.0','end')
    assert page.captured is None and page.load_button.cget('state')=='normal'


def test_business_review_guidance_explains_disabled_approval_and_publication(app):
    from equipment_data_manager.ui.help_content import HELP
    for key in ('business_review','validation_evidence','request_approval','approval_status','publication_readiness','publication_history'):
        assert HELP[key].text('brief') and HELP[key].text('detailed')
    page=app.business_review_page
    app._busy_controls(True);app._busy_controls(False)
    assert page.approve_button.cget('state')==page.publish_button.cget('state')=='disabled'
    assert 'not sent' in HELP['request_approval'].text('brief')
    assert 'Mock approvals' in HELP['publication_readiness'].text()


def review_profile(tmp_path, reporting_period=''):
    from test_powerbi_readiness import build
    from equipment_data_manager.settings import SettingsStore, UserSettings, Preferences
    workspace,_,_,_,_=build(tmp_path/'monthly')
    workspace.approved_folder.mkdir()
    settings_path=tmp_path/'profile/settings.toml'
    SettingsStore(settings_path).save(UserSettings({key:str(getattr(workspace,key)) for key in
        ('raw_folder','candidate_folder','approved_folder')},Preferences(candidate_local_confirmed=True,reporting_period=reporting_period)))
    return workspace,settings_path


def test_reporting_month_preserved_across_navigation_and_restart_in_october(tmp_path,monkeypatch):
    import datetime
    class October:
        @staticmethod
        def today():return datetime.date(2026,10,15)
    monkeypatch.setattr('equipment_data_manager.ui.app.date',October)
    workspace,path=review_profile(tmp_path)
    first=EquipmentDataManager(tmp_path/'defaults',settings_path=path)
    try:
        wait_settings(first)
        assert first.period()=='2026-10'
        first.month.set('January');first.year.set('2026')
        wait_settings(first)
        for page in ('Review & Approval','History','Settings','Help','Process Reports','Review & Approval'):
            first.show_page(page)
            pump(first,lambda:not first.worker.busy and not first.settings_worker.busy)
            assert first.period()=='2026-01'
        assert first.business_review_page.month_picker.get()=='January'
        assert '2026-01' in first.business_review_page.month_caption.cget('text')
        assert first.settings_store.load().preferences.reporting_period=='2026-01'
    finally:
        wait_settings(first);first._close()
    second=EquipmentDataManager(tmp_path/'defaults',settings_path=path)
    try:
        wait_settings(second)
        assert second.period()=='2026-01' and second.workspace.raw_folder==workspace.raw_folder
        assert second.month_confirmed.get() is False and second.previews==()
        second.show_page('Review & Approval');second.business_review_page.load_button.invoke()
        pump(second,lambda:not second.worker.busy)
        assert second.business_review_page.captured['evidence']['period']=='2026-01'
    finally:
        wait_settings(second);second._close()


def test_review_month_selector_invalidates_evidence_and_invalid_year_does_not_replace_saved_month(app,tmp_path):
    _,page=prepare_business_review(app,tmp_path)
    # Explicitly save an existing profile so valid month changes persist.
    app.settings_store.save(app.saved_settings)
    page.month_picker.set('February')
    pump(app,lambda:not app.settings_worker.busy and not app.pending_preferences)
    assert app.period()=='2026-02' and page.captured is None
    assert page.request_button.cget('state')=='disabled'
    assert 'Reporting month changed' in page.counts.get('1.0','end')
    page.year_entry.delete(0,'end');page.year_entry.insert(0,'20')
    assert page.captured is None and 'valid month' in app.status.get()
    assert app.settings_store.load().preferences.reporting_period=='2026-02'
    page.load_button.invoke()
    assert 'valid reporting month' in page.counts.get('1.0','end')
    page.year_entry.delete(0,'end');page.year_entry.insert(0,'2026')
    wait_settings(app)


def test_explicit_month_change_during_settings_load_wins_over_restored_month(tmp_path,monkeypatch):
    from equipment_data_manager.settings import SettingsStore
    _,path=review_profile(tmp_path,'2026-01')
    entered,release=Event(),Event()
    real_load=SettingsStore.load
    def delayed(self):
        entered.set();assert release.wait(5)
        return real_load(self)
    with monkeypatch.context() as patch:
        patch.setattr(SettingsStore,'load',delayed)
        window=EquipmentDataManager(tmp_path/'defaults',settings_path=path)
        try:
            pump(window,entered.is_set)
            window.month.set('May');window.year.set('2027')
            release.set();wait_settings(window)
            assert window.period()=='2027-05'
            assert real_load(window.settings_store).preferences.reporting_period=='2027-05'
        finally:
            release.set();wait_settings(window);window._close()


def test_close_drains_latest_month_save_without_prompting_or_losing_selection(tmp_path,monkeypatch):
    from equipment_data_manager.settings import SettingsStore
    _,path=review_profile(tmp_path,'2026-01')
    window=EquipmentDataManager(tmp_path/'defaults',settings_path=path)
    closed=[];original_close=window._close
    def close():
        closed.append(True);original_close()
    window._close=close
    monkeypatch.setattr('equipment_data_manager.ui.app.messagebox.askyesno',lambda *a,**k:pytest.fail('Preference-only close must not prompt'))
    try:
        wait_settings(window)
        window.month.set('May');window.year.set('2027')
        window.request_close()
        pump(window,lambda:bool(closed))
        assert SettingsStore(path).load().preferences.reporting_period=='2027-05'
    finally:
        if not closed:
            wait_settings(window);window._close()


def test_review_tabs_are_employee_friendly_keep_technical_details_and_all_states_guarded(app,tmp_path):
    _,page=prepare_business_review(app,tmp_path)
    assert page.tabs.get()=='Overview'
    assert 'Repair Reports: 3 retained' in page.counts.get('1.0','end')
    assert 'Reported monthly total: $30.00' in page.financial.get('1.0','end')
    assert 'Missing values' in page.issues.get('1.0','end')
    assert 'Output SHA-256' in page.revisions.get('1.0','end')
    assert 'source_sha256' in page.evidence.get('1.0','end')
    assert '{' not in page.counts.get('1.0','end')+page.financial.get('1.0','end')
    page.note.insert(0,'Synthetic independent checks')
    page.request_button.invoke();pump(app,lambda:not app.worker.busy)
    first=page.service().history()
    page.request_button.invoke();pump(app,lambda:not app.worker.busy)
    assert page.service().history()==first and len(first)==1
    assert 'Review Requested Locally — not sent' in page.review_history.get('1.0','end')
    assert 'Recorded here — not sent' in page.stage_labels[0].cget('text')
    assert 'Not submitted' in page.stage_labels[1].cget('text')
    assert 'No authoritative' in page.stage_labels[2].cget('text')
    assert 'publishing disabled' in page.stage_labels[3].cget('text')
    app._busy_controls(True);app._busy_controls(False)
    for control in (page.sign_in_button,page.approve_button,page.publish_button):
        assert control.cget('state')=='disabled'
    page.tabs.set('Technical details')
    assert 'summary_sha256' in page.evidence.get('1.0','end')


def test_failed_month_save_is_session_only_and_retains_previous_profile(tmp_path,monkeypatch):
    from equipment_data_manager.settings import SettingsStore
    from equipment_data_manager.processing.models import ProcessingError
    _,path=review_profile(tmp_path,'2026-01')
    window=EquipmentDataManager(tmp_path/'defaults',settings_path=path)
    try:
        wait_settings(window);before=path.read_bytes()
        def denied(self,settings):raise ProcessingError('settings_unavailable')
        with monkeypatch.context() as patch:
            patch.setattr(SettingsStore,'save',denied)
            window.month.set('February');wait_settings(window)
            assert window.period()=='2026-02'
            assert 'only to this session' in window.status.get()
            assert path.read_bytes()==before and SettingsStore(path).load().preferences.reporting_period=='2026-01'
        assert window.business_review_page.publish_button.cget('state')=='disabled'
    finally:
        wait_settings(window);window._close()
