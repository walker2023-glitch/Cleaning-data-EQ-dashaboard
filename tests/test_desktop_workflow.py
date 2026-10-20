from dataclasses import replace
from pathlib import Path
from threading import Event, get_ident
from queue import Empty
import time

import pytest

from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import ProcessingRequest, ProcessingStatus as Status, ReportType
from equipment_data_manager.ui.messages import error_message, warning_message
from equipment_data_manager.ui.worker import BackgroundWorker
from equipment_data_manager.ui.workflow import DesktopWorkflow, SourceFile, selected_files

FIXTURES = Path(__file__).parent / "fixtures/synthetic"


@pytest.fixture
def workflow(tmp_path):
    return DesktopWorkflow(tmp_path / "output")


def preview(workflow, paths, kind=ReportType.REPAIRS, period="2026-09"):
    return workflow.preview(selected_files([str(p) for p in paths]), kind, period, lambda *_: None, Event())


def process(workflow, entries, approvals=None):
    return workflow.process(entries, approvals or {}, lambda *_: None, Event())


def test_preview_and_history_are_read_only_for_new_store(workflow):
    entry, = preview(workflow, [FIXTURES / "repairs_input.csv"])
    assert entry.result.code == "ready_to_process"
    assert entry.result.output_rows == 1
    assert entry.result.output_location is None
    assert workflow.coordinator.store.history() == ()
    assert not workflow.output_root.exists()


@pytest.mark.parametrize("kind,name", [(ReportType.REPAIRS, "repairs"), (ReportType.SERVICE_ORDERS, "service")])
def test_workflow_uses_real_M1_and_skips_after_restart(workflow, kind, name):
    path = FIXTURES / f"{name}_input.csv"
    original = path.read_bytes()
    entries = preview(workflow, [path], kind)
    result, = process(workflow, entries)
    assert result.result.status == Status.SUCCESS
    assert result.result.output_location.read_bytes() == entries[0].result.cleaned.output_bytes
    reopened = DesktopWorkflow(workflow.output_root)
    manifest_bytes = (workflow.output_root / "manifest.sqlite3").read_bytes()
    repeated = preview(reopened, [path], kind)
    assert repeated[0].result.status == Status.SKIPPED
    assert (workflow.output_root / "manifest.sqlite3").read_bytes() == manifest_bytes
    assert process(reopened, repeated)[0].result.status == Status.SKIPPED
    assert path.read_bytes() == original


def test_selection_deduplicates_paths_not_filenames(tmp_path):
    paths = [tmp_path / "a/same.csv", tmp_path / "b/same.csv"]
    result = selected_files([str(paths[0]), str(paths[0]), str(paths[1])])
    assert len(result) == 2
    assert result[0].name == result[1].name
    assert result[0].reference != result[1].reference


def test_mixed_versions_of_same_month_block_before_any_output(workflow, tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_bytes((FIXTURES / "repairs_input.csv").read_bytes())
    second.write_bytes(first.read_bytes().replace(b"$10.00", b"$20.00"))
    entries = preview(workflow, [first, second])
    assert {entry.result.code for entry in entries} == {"multiple_files_same_period"}
    assert all(item.result.status == Status.FAILURE for item in process(workflow, entries))
    assert not workflow.output_root.exists()


def test_identical_content_batch_creates_one_output(workflow, tmp_path):
    first, second = tmp_path / "one.csv", tmp_path / "two.csv"
    first.write_bytes((FIXTURES / "repairs_input.csv").read_bytes())
    second.write_bytes(first.read_bytes())
    entries = preview(workflow, [first, second])
    results = process(workflow, entries)
    assert [item.result.status for item in results] == [Status.SUCCESS, Status.SKIPPED]


def test_corrected_file_needs_approval_and_history_retains_previous(workflow, tmp_path):
    path = tmp_path / "report.csv"
    path.write_bytes((FIXTURES / "repairs_input.csv").read_bytes())
    original = process(workflow, preview(workflow, [path]))[0].result
    path.write_bytes(path.read_bytes().replace(b"$10.00", b"$20.00"))
    entries = preview(workflow, [path])
    assert entries[0].result.status == Status.NEEDS_REVIEW
    assert process(workflow, entries)[0].result.code == "correction_not_approved"
    approved = process(workflow, entries, {0: entries[0].result.replacement_token})[0].result
    assert approved.status == Status.SUCCESS
    assert approved.output_location != original.output_location
    assert original.output_location.is_file()
    history = workflow.coordinator.store.history()
    assert len(history) == 2
    assert [item.is_current for item in history] == [True, False]


def test_changed_file_after_preview_never_processes_new_bytes(workflow, tmp_path):
    path = tmp_path / "report.csv"
    path.write_bytes((FIXTURES / "repairs_input.csv").read_bytes())
    entries = preview(workflow, [path])
    path.write_bytes(path.read_bytes().replace(b"$10.00", b"$99.00"))
    result = process(workflow, entries)[0].result
    assert result.code == "input_changed_since_preview"
    assert not workflow.output_root.exists()


def test_stale_manifest_correction_token_is_rejected_by_M1(workflow, tmp_path):
    path = tmp_path / "report.csv"
    path.write_bytes((FIXTURES / "repairs_input.csv").read_bytes())
    process(workflow, preview(workflow, [path]))
    path.write_bytes(path.read_bytes().replace(b"$10.00", b"$20.00"))
    entries = preview(workflow, [path])
    coordinator = workflow.coordinator
    other = ProcessingRequest("repairs", "2026-09", raw_bytes=path.read_bytes().replace(b"$20.00", b"$30.00"))
    review = coordinator.process(other)
    coordinator.process(replace(other, replacement_token=review.replacement_token))
    result = process(workflow, entries, {0: entries[0].result.replacement_token})[0].result
    assert result.status == Status.NEEDS_REVIEW
    assert len(coordinator.store.history()) == 2


@pytest.mark.parametrize("case", ["missing", "empty", "wrong_type", "invalid_period", "unsupported_tma"])
def test_invalid_inputs_report_safe_failures(workflow, tmp_path, case):
    path = FIXTURES / "repairs_input.csv"
    kind, period = ReportType.REPAIRS, "2026-09"
    if case == "missing":
        path = tmp_path / "missing.csv"
    elif case == "empty":
        path = tmp_path / "empty.csv"
        path.write_bytes(b"")
    elif case == "wrong_type":
        kind = ReportType.SERVICE_ORDERS
    elif case == "invalid_period":
        period = "2026-13"
    else:
        kind = ReportType.TMA_WORK_ORDERS
    result = preview(workflow, [path], kind, period)[0].result
    assert result.status == Status.FAILURE
    assert error_message(result.code)
    assert not workflow.output_root.exists()


def test_storage_independence_uses_bytes_from_injected_source(workflow):
    class FixtureSource:
        def read(self, source):
            assert source.reference == "opaque-fixture-reference"
            return (FIXTURES / "repairs_input.csv").read_bytes()

    workflow.source = FixtureSource()
    entries = workflow.preview([SourceFile("opaque-fixture-reference", "report.csv")], ReportType.REPAIRS, "2026-09", lambda *_: None, Event())
    assert process(workflow, entries)[0].result.status == Status.SUCCESS


def test_cancel_stops_between_files_without_new_output(workflow):
    entries = preview(workflow, [FIXTURES / "repairs_input.csv"])
    stop = Event()
    stop.set()
    results = workflow.process(entries, {}, lambda *_: None, stop)
    assert results[0].result.code == "cancelled"
    assert not workflow.output_root.exists()


def test_failed_processing_preserves_original_and_does_not_escape(workflow, monkeypatch):
    path = FIXTURES / "repairs_input.csv"
    original = path.read_bytes()
    entries = preview(workflow, [path])

    def fail(*args):
        raise ValueError("SYNTHETIC_PRIVATE_VALUE")

    monkeypatch.setattr(workflow.coordinator, "process", fail)
    result = process(workflow, entries)[0].result
    assert result.status == Status.FAILURE
    assert "SYNTHETIC_PRIVATE_VALUE" not in str(result)
    assert path.read_bytes() == original
    assert not workflow.output_root.exists()


def test_worker_runs_off_main_thread_rejects_overlapping_jobs_and_reports_errors():
    worker = BackgroundWorker()
    gate, entered = Event(), Event()
    main_thread = get_ident()

    def operation(progress, stop):
        assert get_ident() != main_thread
        entered.set()
        assert gate.wait(3)
        progress(1, 1)
        return "completed"

    try:
        assert worker.start(operation)
        assert entered.wait(2)
        assert worker.busy
        assert not worker.start(operation)
        worker.stop()
        assert worker.cancelled.is_set()
        gate.set()
        assert worker.events.get(timeout=3).kind == "progress"
        assert worker.events.get(timeout=3).payload == "completed"
        worker.busy = False

        def broken(*args):
            raise ValueError("SYNTHETIC_PRIVATE_VALUE")

        worker.start(broken)
        event = worker.events.get(timeout=3)
        assert event.kind == "error"
        assert "SYNTHETIC_PRIVATE_VALUE" not in event.payload
    finally:
        gate.set()
        worker.close()


def test_messages_do_not_echo_unknown_codes_or_values():
    assert "SYNTHETIC_PRIVATE_VALUE" not in error_message("SYNTHETIC_PRIVATE_VALUE")
    assert "SYNTHETIC_PRIVATE_VALUE" not in warning_message("unknown:SYNTHETIC_PRIVATE_VALUE")
    assert "3" in warning_message("invalid_source_dates:3")
