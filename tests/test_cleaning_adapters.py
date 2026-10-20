"""Synthetic/source characterization only; no production accuracy claims."""

from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd
import pytest

from clean import repairs_row_clean as original_repairs
from clean import service_row_clean as original_service
from equipment_data_manager.processing.cleaners import LegacyCsvCleaner
from equipment_data_manager.processing.models import ProcessingError, ReportType

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/synthetic"


@pytest.mark.parametrize("name", ["row_clean_common.py", "repairs_row_clean.py", "service_row_clean.py"])
def test_vendored_logic_differs_only_in_import_location(name):
    original = (ROOT / "legacy/clean" / name).read_bytes()
    packaged = (ROOT / "src/equipment_data_manager/processing/_legacy" / name).read_bytes()
    assert packaged == original.replace(b"from clean.row_clean_common import", b"from .row_clean_common import")


@pytest.mark.parametrize("kind,fixture", [(ReportType.REPAIRS, "repairs"), (ReportType.SERVICE_ORDERS, "service")])
def test_adapter_matches_original_transform_and_writer(kind, fixture):
    raw = (FIXTURES / f"{fixture}_input.csv").read_bytes()
    result = LegacyCsvCleaner(kind).clean(raw, source_name="September 1999.csv", period="2026-09")
    frame = pd.read_csv(BytesIO(raw), encoding_errors="replace")
    output = StringIO(newline="")
    if kind == ReportType.REPAIRS:
        candidate = original_repairs.clean_repairs_raw(frame)
        original_repairs._write_repairs_csv(candidate, output, "BYU–Idaho  |  Equipment Repair Log  |  September 2026")
        assert {m.name: m.value for m in result.reconciliation_metrics}["Est. Total $"] == 35
    else:
        candidate = original_service.clean_service_raw(frame, "2026-09")
        candidate.to_csv(output, index=False)
    assert result.output_bytes == output.getvalue().encode("utf-8")
    assert result.input_rows == 2
    assert result.output_rows == 1
    assert result.source_period == "2026-09"
    assert "rows_excluded_by_legacy:1" in result.warnings
    assert "production_accuracy_unverified" in result.warnings


@pytest.mark.parametrize("kind,fixture,column", [
    (ReportType.REPAIRS, "repairs", "CompletedDate1"),
    (ReportType.REPAIRS, "repairs", "Details"),
    (ReportType.SERVICE_ORDERS, "service", "EquipmentId1"),
    (ReportType.SERVICE_ORDERS, "service", "Cost"),
])
def test_missing_columns_fail_before_any_guessing(kind, fixture, column):
    frame = pd.read_csv(FIXTURES / f"{fixture}_input.csv")
    raw = frame.drop(columns=[column]).to_csv(index=False).encode()
    with pytest.raises(ProcessingError, match="missing_required_columns"):
        LegacyCsvCleaner(kind).clean(raw, source_name="sample.csv", period="2026-09")


@pytest.mark.parametrize("raw,code", [
    (b"", "empty_input"), (b"\n  \n", "empty_input"),
    (b"a,a\n1,2", "duplicate_headers"), (b"a, a\n1,2", "duplicate_headers"),
    (b"a,\n1,2", "blank_headers"), (b"a,b\n1,2,3", "invalid_csv_row_width"),
    (b'a,b\n"unterminated', "invalid_csv_or_encoding"),
    (b"a,b\n\xff,1", "invalid_csv_or_encoding"),
    (b"a,b\n\x00,1", "invalid_csv_or_encoding"),
    (b" a,b\n1,2", "unverified_header_layout"),
])
def test_invalid_layouts_are_explicit(raw, code):
    with pytest.raises(ProcessingError, match=code):
        LegacyCsvCleaner(ReportType.REPAIRS).clean(raw, source_name="sample.csv", period="2026-09")


def test_invalid_date_is_excluded_and_reported_without_changing_legacy_rule():
    raw = (FIXTURES / "repairs_input.csv").read_bytes()
    result = LegacyCsvCleaner(ReportType.REPAIRS).clean(raw, source_name="sample.csv", period="2026-09")
    assert "invalid_source_dates:1" in result.warnings
    assert result.output_rows == 1


def test_invalid_money_keeps_legacy_zero_with_warning():
    raw = (FIXTURES / "repairs_input.csv").read_bytes().replace(b"$10.00", b"SYNTHETIC-BAD-MONEY")
    result = LegacyCsvCleaner(ReportType.REPAIRS).clean(raw, source_name="sample.csv", period="2026-09")
    metrics = {m.name: m.value for m in result.reconciliation_metrics}
    assert metrics["Parts Cost $"] == 0
    assert metrics["Total Labor $"] == 25
    assert "invalid_source_money:1" in result.warnings
    assert b"SYNTHETIC-BAD-MONEY" not in str(result.warnings).encode()


@pytest.mark.parametrize("duration,hours", [("found", 0.5), ("", 1.0), ("1/2 hr", 0.5), ("2 hours", 2.0), ("unrecognized", 1.0)])
def test_duration_defaults_and_labor_calculation_are_unchanged(duration, hours):
    raw = (FIXTURES / "repairs_input.csv").read_bytes().replace(b"2 hours", duration.encode())
    result = LegacyCsvCleaner(ReportType.REPAIRS).clean(raw, source_name="sample.csv", period="2026-09")
    metrics = {m.name: m.value for m in result.reconciliation_metrics}
    assert float(metrics["Repair Person-Hrs"]) == hours
    assert float(metrics["Total Labor $"]) == round(hours * 12.5, 2)
    assert metrics["# of Repairs"] == 1


def test_period_mismatch_rejects_candidate_instead_of_refiltering_repairs():
    raw = (FIXTURES / "repairs_input.csv").read_bytes()
    with pytest.raises(ProcessingError, match="output_period_mismatch"):
        LegacyCsvCleaner(ReportType.REPAIRS).clean(raw, source_name="sample.csv", period="2026-08")


def test_nonfinite_output_rejected():
    raw = (FIXTURES / "repairs_input.csv").read_bytes().replace(b"$10.00", b"inf")
    with pytest.raises(ProcessingError, match="nonfinite_output_number"):
        LegacyCsvCleaner(ReportType.REPAIRS).clean(raw, source_name="sample.csv", period="2026-09")


def test_unknown_columns_are_reported_and_original_values_not_logged():
    frame = pd.read_csv(FIXTURES / "repairs_input.csv")
    frame["SyntheticPrivateField"] = "SYNTHETIC-PRIVATE-VALUE"
    result = LegacyCsvCleaner(ReportType.REPAIRS).clean(frame.to_csv(index=False).encode(), source_name="sample.csv", period="2026-09")
    assert "unmapped_source_columns:1" in result.warnings
    assert "SYNTHETIC-PRIVATE-VALUE" not in str(result.warnings)


def test_tma_is_explicitly_not_mapped_to_requests():
    with pytest.raises(ProcessingError, match="awaiting_verified_fixtures"):
        LegacyCsvCleaner(ReportType.TMA_WORK_ORDERS)


def test_legitimate_identical_business_records_are_not_deduplicated():
    lines = (FIXTURES / "repairs_input.csv").read_bytes().splitlines()
    raw = b"\n".join([lines[0], lines[1], lines[1]]) + b"\n"
    result = LegacyCsvCleaner(ReportType.REPAIRS).clean(raw, source_name="sample.csv", period="2026-09")
    assert result.input_rows == result.output_rows == 2
    assert {m.name: m.value for m in result.reconciliation_metrics}["# of Repairs"] == 2


def test_service_cross_month_rule_and_last_day_are_preserved():
    raw = (FIXTURES / "service_input.csv").read_bytes().replace(b"2026-09-30", b"2026-10-01")
    result = LegacyCsvCleaner(ReportType.SERVICE_ORDERS).clean(raw, source_name="sample.csv", period="2026-09")
    assert result.output_rows == 1
    assert b"2026-10-01" in result.output_bytes
    assert "cross_period_output_dates:1" in result.warnings


def test_utf8_bom_keeps_same_candidate_bytes():
    raw = (FIXTURES / "repairs_input.csv").read_bytes()
    cleaner = LegacyCsvCleaner(ReportType.REPAIRS)
    plain = cleaner.clean(raw, source_name="sample.csv", period="2026-09")
    bom = cleaner.clean(b"\xef\xbb\xbf" + raw, source_name="sample.csv", period="2026-09")
    assert plain.output_bytes == bom.output_bytes
