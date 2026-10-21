"""Real Tk widgets and M1 integration. Linux requires DISPLAY (xvfb-run in CI)."""

from pathlib import Path
from threading import Event
from time import monotonic

import pytest

from equipment_data_manager.processing.models import ProcessingStatus as Status, ReportType
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
    window = EquipmentDataManager(tmp_path / "outputs")
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
