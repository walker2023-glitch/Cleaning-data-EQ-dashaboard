"""Synthetic shape regression derived from the supplied February export.

Expected values are source-derived assertions, not a trusted departmental golden.
The actual uploaded report must not be committed or used by CI.
"""

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from equipment_data_manager.processing.cleaners import LegacyCsvCleaner
from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest, ProcessingStatus as Status, ReportType

FIXTURES = Path(__file__).parent / "fixtures/synthetic"
INPUT = FIXTURES / "service_orders_february_2026.csv"


def clean(raw):
    return LegacyCsvCleaner(ReportType.SERVICE_ORDERS).clean(raw, source_name="report.csv", period="2026-02")


@pytest.mark.parametrize("bom", [True, False])
def test_observed_layout_retains_all_five_records_and_expected_fields(bom):
    raw = INPUT.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    if not bom:
        raw = raw[3:]
    result = clean(raw)
    actual = pd.read_csv(BytesIO(result.output_bytes), dtype=str, keep_default_na=False)
    expected = pd.read_csv(FIXTURES / "service_orders_february_2026_expected.csv", dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(actual, expected)
    assert result.input_rows == result.output_rows == 5
    assert actual["Equipment Id"].tolist()[1:3] == ["000439", "000007"]
    assert actual["Estimated Price"].eq("").all()
    assert "Textbox56" not in actual.columns
    assert not actual.astype(str).apply(lambda col: col.str.contains("Total Service Orders")).any().any()
    assert {m.name: m.value for m in result.reconciliation_metrics} == {
        "Source service orders": 5, "Retained service orders": 5,
    }
    assert "estimated_price_unavailable" in result.warnings
    assert "production_accuracy_unverified" in result.warnings


@pytest.mark.parametrize("change", ["missing_header", "extra_header", "duplicate_header", "bad_summary", "mixed_summary", "wrong_count"])
def test_only_the_specific_layout_is_enabled(change):
    frame = pd.read_csv(INPUT, dtype=str, keep_default_na=False)
    if change == "missing_header":
        frame = frame.drop(columns=["Textbox56"])
    elif change == "extra_header":
        frame["Unknown"] = "Synthetic value"
    elif change == "duplicate_header":
        frame.columns = ["EquipmentId1" if name == "AccountName2" else name for name in frame.columns]
    elif change == "bad_summary":
        frame["Textbox56"] = "unrecognized metadata"
    elif change == "mixed_summary":
        frame.loc[0, "Textbox56"] = "Total Service Orders: 6"
    else:
        frame["Textbox56"] = "Total Service Orders: 6"
    with pytest.raises(ProcessingError):
        clean(frame.to_csv(index=False).encode("utf-8-sig"))


def test_summary_only_row_is_not_silently_treated_as_a_service_record():
    frame = pd.read_csv(INPUT, dtype=str, keep_default_na=False)
    frame.loc[len(frame)] = ["" for _ in frame.columns]
    frame.loc[len(frame) - 1, "Textbox56"] = "Total Service Orders: 5"
    with pytest.raises(ProcessingError, match="service_order_summary_mismatch"):
        clean(frame.to_csv(index=False).encode())


def test_reordered_headers_are_still_the_same_specific_layout():
    frame = pd.read_csv(INPUT, dtype=str, keep_default_na=False)
    reordered = clean(frame[frame.columns[::-1]].to_csv(index=False).encode())
    assert reordered.output_bytes == clean(INPUT.read_bytes()).output_bytes


def test_new_layout_still_uses_original_service_exclusions_and_status_rules():
    frame = pd.read_csv(INPUT, dtype=str, keep_default_na=False)
    frame.loc[0, "Description"] = "- (PM)"  # Existing exclusion, not a new rule.
    frame.loc[1, "Description"] = "Synthetic inspection - (PM)"
    frame.loc[2, "Textbox21"] = "Scheduled"
    result = clean(frame.to_csv(index=False).encode())
    out = pd.read_csv(BytesIO(result.output_bytes), dtype=str, keep_default_na=False)
    assert result.input_rows == 5 and result.output_rows == 4
    assert "rows_excluded_by_legacy:1" in result.warnings
    assert out.loc[out["Equipment Id"].eq("000439"), "Description"].iloc[0] == "Synthetic inspection"
    assert out.loc[out["Equipment Id"].eq("000007"), "Status"].iloc[0] == "Scheduled"


def test_coordinator_preview_process_and_repeat(tmp_path):
    coordinator = ProcessingCoordinator(tmp_path / "candidate")
    request = ProcessingRequest("service_orders", "2026-02", input_path=INPUT)
    preview = coordinator.preview(request)
    assert preview.code == "ready_to_process"
    assert preview.output_rows == 5
    assert not coordinator.store.root.exists()
    saved = coordinator.process(request)
    assert saved.status == Status.SUCCESS and saved.output_rows == 5
    assert saved.output_location.read_bytes() == preview.cleaned.output_bytes
    assert coordinator.process(request).status == Status.SKIPPED
