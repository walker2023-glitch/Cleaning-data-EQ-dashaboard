"""Source-derived examples, not verified departmental data contracts.

Only pure DataFrame transforms are called. Never call legacy main/process_file.
Inventory cannot import until its original dashboard.taxonomy is supplied.
"""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from clean.repairs_row_clean import clean_repairs_raw
from clean.requests_row_clean import clean_requests_raw
from clean.service_row_clean import clean_service_raw

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "synthetic"


def test_uploaded_sources_are_preserved():
    hashes = json.loads((ROOT / "legacy/source_hashes.json").read_text())
    assert len(hashes) == 6
    for name, expected_hash in hashes.items():
        assert hashlib.sha256((ROOT / "legacy/clean" / name).read_bytes()).hexdigest() == expected_hash


@pytest.mark.parametrize("report", ["repairs", "service", "requests"])
def test_source_characterization(report):
    raw_path = FIXTURES / f"{report}_input.csv"
    original = raw_path.read_bytes()
    raw = pd.read_csv(raw_path, dtype=str)
    before = raw.copy(deep=True)
    if report == "repairs":
        actual = clean_repairs_raw(raw)
    elif report == "service":
        actual = clean_service_raw(raw, "2026-09")
    else:
        actual = clean_requests_raw(raw)
    # Compare serialized field values, preserving column order, without pandas
    # inference treating business identifiers as numbers.
    from io import StringIO

    serialized = pd.read_csv(StringIO(actual.to_csv(index=False)), dtype=str).fillna("")
    expected = pd.read_csv(FIXTURES / f"{report}_expected.csv", dtype=str).fillna("")
    pd.testing.assert_frame_equal(serialized, expected)
    pd.testing.assert_frame_equal(raw, before)
    assert raw_path.read_bytes() == original
