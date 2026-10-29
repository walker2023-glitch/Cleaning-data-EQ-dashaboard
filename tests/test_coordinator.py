from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sqlite3

import pytest

from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import ProcessingRequest, ProcessingStatus as Status, ReportType

FIXTURES = Path(__file__).parent / "fixtures/synthetic"


@pytest.fixture
def raw():
    return (FIXTURES / "repairs_input.csv").read_bytes()


@pytest.fixture
def engine(tmp_path):
    return ProcessingCoordinator(tmp_path / "outputs")


def request(raw, **kwargs):
    return ProcessingRequest(ReportType.REPAIRS, "2026-09", raw_bytes=raw, **kwargs)


def test_path_and_bytes_inputs_produce_identical_candidates_and_preserve_source(engine, raw, tmp_path):
    path = tmp_path / "original.csv"
    path.write_bytes(raw)
    original_stat = path.stat()
    first = engine.process(ProcessingRequest("repairs", "2026-09", input_path=path))
    assert first.status == Status.SUCCESS
    assert first.output_rows == 1 and first.input_rows == 2
    assert first.output_location.read_bytes() == first.cleaned.output_bytes
    assert first.output_location.name == "CompuClean_RepairReports_2026-09.csv"
    second = ProcessingCoordinator(engine.store.root).process(request(raw, source_name="renamed.csv"))
    assert second.status == Status.SKIPPED
    assert second.artifact == first.artifact
    assert second.input_rows == 2 and second.output_rows == 1
    assert second.warnings == first.warnings
    assert len(list(engine.store.root.rglob("*.csv"))) == 1
    assert path.read_bytes() == raw
    assert path.stat().st_mtime_ns == original_stat.st_mtime_ns


@pytest.mark.parametrize("kind,fixture", [("repairs", "repairs"), ("service_orders", "service")])
def test_correct_report_selection(engine, kind, fixture):
    result = engine.process(ProcessingRequest(kind, "2026-09", raw_bytes=(FIXTURES / f"{fixture}_input.csv").read_bytes()))
    assert result.status == Status.SUCCESS
    assert result.output_rows == 1


@pytest.mark.parametrize("kind", ["unknown", "tma_work_orders", "service_orders"])
def test_wrong_or_unverified_report_selection_does_not_write_artifacts(engine, raw, kind):
    result = engine.process(ProcessingRequest(kind, "2026-09", raw_bytes=raw))
    assert result.status == Status.FAILURE
    assert not list(engine.store.root.rglob("*.csv"))


@pytest.mark.parametrize("period", ["", "September", "2026-13", "2026-9", "../2026-09", "0000-01"])
def test_invalid_periods(engine, raw, period):
    result = engine.process(ProcessingRequest("repairs", period, raw_bytes=raw))
    assert result.code == "invalid_reporting_period"
    assert result.status == Status.FAILURE
    assert not engine.store.root.exists()


def test_missing_directory_and_both_input_forms(engine, raw, tmp_path):
    for path in (tmp_path / "missing.csv", tmp_path):
        assert engine.process(ProcessingRequest("repairs", "2026-09", input_path=path)).code == "input_not_a_file"
    assert engine.process(ProcessingRequest("repairs", "2026-09")).code == "exactly_one_input_required"
    both = ProcessingRequest("repairs", "2026-09", input_path=tmp_path, raw_bytes=raw)
    assert engine.process(both).code == "exactly_one_input_required"


@pytest.mark.parametrize("raw,code", [(b"", "empty_input"), (b"a,b\n1,2", "missing_required_columns")])
def test_invalid_files_do_not_create_output(engine, raw, code):
    result = engine.process(request(raw))
    assert result.status == Status.FAILURE
    assert result.code == code
    assert result.output_location is None
    assert not list(engine.store.root.rglob("*.csv"))


def test_format_is_not_guessed(engine, raw):
    result = engine.process(request(raw, source_name="report.xlsx"))
    assert result.status == Status.FAILURE
    assert result.code == "unsupported_file_format"


def test_same_filename_different_months_do_not_overwrite(engine, raw):
    first = engine.process(request(raw, source_name="monthly.csv"))
    second = engine.process(ProcessingRequest("repairs", "2026-10", raw_bytes=raw.replace(b"2026-09-30", b"2026-10-31"), source_name="monthly.csv"))
    assert first.status == second.status == Status.SUCCESS
    assert first.output_location != second.output_location
    assert first.output_location.read_bytes() == first.cleaned.output_bytes


def test_corrected_month_requires_bound_confirmation_and_retains_prior_output(engine, raw):
    first = engine.process(request(raw))
    corrected = request(raw.replace(b"$10.00", b"$20.00"), source_name="same.csv")
    review = engine.process(corrected)
    assert review.status == Status.NEEDS_REVIEW
    assert review.previous == first.artifact
    assert review.output_location is None
    assert review.cleaned.reconciliation_metrics != first.cleaned.reconciliation_metrics
    assert len(list(engine.store.root.rglob("*.csv"))) == 1
    approved = replace(corrected, replacement_token=review.replacement_token)
    second = engine.process(approved)
    assert second.status == Status.SUCCESS
    assert second.previous == first.artifact
    assert second.artifact.revision_id != first.artifact.revision_id
    assert first.output_location.read_bytes() == first.cleaned.output_bytes
    assert second.output_location.read_bytes() == second.cleaned.output_bytes
    assert ProcessingCoordinator(engine.store.root).process(corrected).status == Status.SKIPPED


def test_confirmation_cannot_be_reused_for_different_correction_or_later_revision(engine, raw):
    engine.process(request(raw))
    correction = request(raw.replace(b"$10.00", b"$20.00"))
    review = engine.process(correction)
    different = request(raw.replace(b"$10.00", b"$30.00"), replacement_token=review.replacement_token)
    assert engine.process(different).status == Status.NEEDS_REVIEW
    engine.process(replace(correction, replacement_token=review.replacement_token))
    reverted = request(raw, replacement_token=review.replacement_token)
    assert engine.process(reverted).status == Status.NEEDS_REVIEW


def test_cleaner_version_change_requires_review(engine, raw):
    engine.process(request(raw))
    engine.cleaners[ReportType.REPAIRS].version += ":new-reviewed-test-version"
    result = engine.process(request(raw))
    assert result.status == Status.NEEDS_REVIEW


def test_sequential_batch_continues_after_failure_and_skips_duplicates(engine, raw):
    results = engine.process_many([request(b"invalid"), request(raw), request(raw)])
    assert [r.status for r in results] == [Status.FAILURE, Status.SUCCESS, Status.SKIPPED]
    assert len(list(engine.store.root.rglob("*.csv"))) == 1


def test_failed_correction_keeps_active_output_and_inputs(engine, raw):
    first = engine.process(request(raw))
    invalid = raw.replace(b"2026-09-30", b"invalid")
    result = engine.process(request(invalid, replacement_token="unapproved"))
    assert result.status == Status.FAILURE
    assert result.code == "no_output_rows"
    assert engine.process(request(raw)).artifact == first.artifact
    assert len(list(engine.store.root.rglob("*.csv"))) == 1


def test_interrupted_file_write_preserves_previous_active_revision(engine, raw, monkeypatch):
    first = engine.process(request(raw))
    correction = request(raw.replace(b"$10.00", b"$20.00"))
    review = engine.process(correction)
    import equipment_data_manager.processing.manifest as manifest

    def fail(*args):
        raise OSError("SYNTHETIC-PRIVATE-DETAIL")

    with monkeypatch.context() as patch:
        patch.setattr(manifest.os, "replace", fail)
        result = engine.process(replace(correction, replacement_token=review.replacement_token))
    assert result.status == Status.FAILURE
    assert "SYNTHETIC-PRIVATE-DETAIL" not in str(result)
    assert engine.process(request(raw)).artifact == first.artifact
    assert not list(engine.store.root.rglob("*.tmp"))
    assert len(list(engine.store.root.rglob("*.csv"))) == 1


def test_manifest_failure_rolls_back_selection_and_retains_previous_revision(engine, raw, monkeypatch):
    first = engine.process(request(raw))
    correction = request(raw.replace(b"$10.00", b"$20.00"))
    review = engine.process(correction)
    select = engine.store.select_revision

    def fail_after_insert(*args):
        select(*args)
        raise sqlite3.OperationalError("synthetic commit interruption")

    with monkeypatch.context() as patch:
        patch.setattr(engine.store, "select_revision", fail_after_insert)
        result = engine.process(replace(correction, replacement_token=review.replacement_token))
    assert result.status == Status.FAILURE
    assert engine.process(request(raw)).artifact == first.artifact
    # An immutable orphan may remain; it is never selected or ingested implicitly.
    assert engine.process(correction).previous == first.artifact


@pytest.mark.parametrize("mutation,code", [("delete", "existing_output_missing_or_unreadable"), ("tamper", "existing_output_hash_mismatch")])
def test_missing_or_tampered_output_is_never_silently_skipped_or_overwritten(engine, raw, mutation, code):
    first = engine.process(request(raw))
    if mutation == "delete":
        first.output_location.unlink()
    else:
        first.output_location.write_bytes(b"synthetic tampering")
    result = engine.process(request(raw))
    assert result.status == Status.FAILURE
    assert result.code == code


def test_simultaneous_local_calls_select_only_one_active_revision(engine, raw):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ProcessingCoordinator(engine.store.root).process(request(raw)), range(2)))
    assert sorted(r.status.value for r in results) == ["skipped", "success"]
    assert len(list(engine.store.root.rglob("*.csv"))) == 1


def test_source_name_is_not_used_as_an_output_path(engine, raw):
    result = engine.process(request(raw, source_name="../../synthetic.csv"))
    assert result.status == Status.SUCCESS
    assert result.output_location.is_relative_to(engine.store.root)
    assert result.output_location.name == "CompuClean_RepairReports_2026-09.csv"


def test_corrupt_manifest_is_preserved_and_fails_closed(engine, raw):
    engine.store.root.mkdir()
    database = engine.store.root / "manifest.sqlite3"
    database.write_bytes(b"synthetic invalid sqlite file")
    result = engine.process(request(raw))
    assert result.status == Status.FAILURE
    assert database.read_bytes() == b"synthetic invalid sqlite file"
    assert not list(engine.store.root.rglob("*.csv"))


def test_unexpected_cleaner_failure_does_not_escape_or_publish(engine, raw, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("SYNTHETIC-PRIVATE-RAW-CONTENT")

    monkeypatch.setattr(engine.cleaners[ReportType.REPAIRS], "clean", fail)
    result = engine.process(request(raw))
    assert result.status == Status.FAILURE
    assert result.code == "processing_failed"
    assert "SYNTHETIC-PRIVATE-RAW-CONTENT" not in str(result)
    assert not list(engine.store.root.rglob("*.csv"))


def test_no_replacement_target_and_nonbytes_input(engine, raw):
    assert engine.process(request(raw, replacement_token="stale")).code == "replacement_target_missing"
    assert engine.process(request("not bytes")).code == "input_must_be_bytes"
