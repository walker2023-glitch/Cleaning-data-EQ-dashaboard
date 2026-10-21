import json
from pathlib import Path

import pytest

from equipment_data_manager.__main__ import main

FIXTURE = Path(__file__).parent / "fixtures/synthetic/repairs_input.csv"


def test_cli_success_repeat_and_failure_exit_codes(tmp_path, capsys):
    arguments = ["process", str(FIXTURE), "--report-type", "repairs", "--period", "2026-09", "--output-dir", str(tmp_path / "outputs")]
    assert main(arguments) == 0
    created = json.loads(capsys.readouterr().out)[0]
    assert created["status"] == "success"
    assert created["output_rows"] == 1
    assert Path(created["output_location"]).is_file()
    assert main(arguments) == 0
    assert json.loads(capsys.readouterr().out)[0]["status"] == "skipped"
    arguments[arguments.index("repairs")] = "tma_work_orders"
    assert main(arguments) == 1
    assert json.loads(capsys.readouterr().out)[0]["code"] == "unsupported_file_format"


def test_cli_correction_review_then_acknowledgement(tmp_path, capsys):
    path = tmp_path / "sample.csv"
    path.write_bytes(FIXTURE.read_bytes())
    args = ["process", str(path), "--report-type", "repairs", "--period", "2026-09", "--output-dir", str(tmp_path / "outputs")]
    assert main(args) == 0
    capsys.readouterr()
    path.write_bytes(path.read_bytes().replace(b"$10.00", b"$20.00"))
    assert main(args) == 1
    review = json.loads(capsys.readouterr().out)[0]
    assert review["status"] == "needs_review"
    assert review["previous_output_rows"] == 1
    assert Path(review["previous_output_location"]).is_file()
    assert {m["name"]: m["value"] for m in review["candidate_metrics"]}["Est. Total $"] == "45.0"
    assert main(args + ["--replacement-token", review["replacement_token"]]) == 0
    assert json.loads(capsys.readouterr().out)[0]["status"] == "success"


def test_cli_replacement_cannot_apply_to_a_batch(tmp_path):
    args = ["process", str(FIXTURE), str(FIXTURE), "--report-type", "repairs", "--period", "2026-09", "--output-dir", str(tmp_path), "--replacement-token", "synthetic-token"]
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
