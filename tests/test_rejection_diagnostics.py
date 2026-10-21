"""Invented January inputs: explain rejection without changing cleaning rules."""

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from threading import Event

import pandas as pd
import pytest

from equipment_data_manager.__main__ import main
from equipment_data_manager.processing.cleaners import LegacyCsvCleaner
from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import ProcessingRequest, ProcessingStatus as Status, ReportType
from equipment_data_manager.ui.messages import diagnostic_lines, error_message
from equipment_data_manager.ui.workflow import DesktopWorkflow, selected_files
from report_samples import repair_csv, service_csv


def request(kind, raw, period='2026-01'):
    return ProcessingRequest(kind, period, raw_bytes=raw, source_name='synthetic.csv')


def test_repair_failure_retains_exact_record_raw_and_cleaned_date_diagnostics(tmp_path):
    frame = pd.read_csv(BytesIO(repair_csv(1, 3)), dtype=str, keep_default_na=False)
    frame['CompletedDate1'] = ['1/8/2026', '2/3/2026', 'not-a-date']
    raw = frame.to_csv(index=False).encode('utf-8-sig')
    engine = ProcessingCoordinator(tmp_path / 'out')
    result = engine.preview(request('repairs', raw))
    assert result.status == Status.FAILURE and result.code == 'output_period_mismatch'
    assert not engine.store.root.exists()
    diag = result.diagnostics
    assert diag.selected_period == '2026-01' and diag.retained_rows == 2
    assert diag.summary()['reason_counts'] == dict(accepted=1, missing_equipment_identity=0,
                                                  invalid_completed_date=1, outside_reporting_period=1)
    assert [(r.record, r.reason, r.dates[0].raw_value, r.dates[0].parsed_value) for r in diag.records] == [
        (1, 'accepted', '1/8/2026', '2026-01-08'),
        (2, 'outside_reporting_period', '2/3/2026', '2026-02-03'),
        (3, 'invalid_completed_date', 'not-a-date', None),
    ]
    assert 'not-a-date' not in repr(result) and 'not-a-date' not in repr(diag)
    detail = '\n'.join(diagnostic_lines(diag))
    assert "Record 2:" in detail and "'2/3/2026' -> 2026-02-03" in detail
    assert 'Engine reporting month: 2026-01' in detail
    assert engine.process(request('repairs', raw)).code == 'output_period_mismatch'
    assert not list(engine.store.root.rglob('*.csv'))


def service_exclusion_frame():
    frame = pd.read_csv(BytesIO(service_csv(1, 8)), dtype=str, keep_default_na=False)
    frame.loc[1, 'EquipmentId1'] = ''
    frame.loc[2, 'ScheduledDate'] = ''
    frame.loc[3, 'Description'] = '- (PM)'
    frame.loc[4, ['ScheduledDate', 'CompletedDate']] = 'not-a-date'
    frame.loc[5, ['ScheduledDate', 'CompletedDate']] = '2/3/2026'
    frame.loc[6, 'Description'] = '-    (PM)'
    frame.loc[7, 'Description'] = 'Delete duplicate synthetic record'
    return frame


def test_service_first_exclusion_reasons_account_for_every_record(tmp_path):
    frame = service_exclusion_frame()
    engine = ProcessingCoordinator(tmp_path / 'out')
    result = engine.preview(request('service_orders', frame.to_csv(index=False).encode()))
    assert result.status == Status.SUCCESS and result.output_rows == 1
    diag = result.diagnostics
    assert set(diag.summary()['reason_counts'].values()) == {1}
    assert sum(diag.summary()['reason_counts'].values()) == 8
    assert [r.retained_by_cleaner for r in diag.records] == [True] + [False] * 7
    assert diag.records[5].record == 6 and diag.records[5].reason == 'outside_reporting_period'
    assert diag.records[5].dates[0].parsed_value == '2026-02-03'
    # An actual exclusion takes precedence over later conditions.
    frame.loc[1, ['ScheduledDate', 'CompletedDate']] = 'not-a-date'
    assert engine.preview(request('service_orders', frame.to_csv(index=False).encode())).diagnostics.records[1].reason == 'missing_equipment_id'


def test_all_service_records_excluded_still_return_reasons_and_never_write(tmp_path):
    frame = service_exclusion_frame().iloc[1:].copy()
    frame['Textbox56'] = 'Total Service Orders: 7'
    engine = ProcessingCoordinator(tmp_path / 'out')
    raw = frame.to_csv(index=False).encode()
    result = engine.preview(request('service_orders', raw))
    assert result.status == Status.FAILURE and result.code == 'no_output_rows'
    assert result.diagnostics.retained_rows == 0
    reasons = result.diagnostics.summary()['reason_counts']
    assert reasons['accepted'] == 0 and sum(reasons.values()) == 7
    assert engine.process(request('service_orders', raw)).code == 'no_output_rows'
    assert not list(engine.store.root.rglob('*.csv'))


@pytest.mark.parametrize('kind,factory', [('repairs', repair_csv), ('service_orders', service_csv)])
def test_satisfying_january_inputs_process_unchanged_and_trace_same_period(tmp_path, kind, factory):
    path = tmp_path / 'raw.csv'
    raw = factory(1, 3)
    path.write_bytes(raw)
    workflow = DesktopWorkflow(tmp_path / 'out')
    entries = workflow.preview(selected_files([str(path)]), ReportType(kind), '2026-01', lambda *_: None, Event())
    assert entries[0].result.code == 'ready_to_process'
    assert entries[0].result.diagnostics.summary()['reason_counts']['accepted'] == 3
    result = workflow.process(entries, {}, lambda *_: None, Event())[0].result
    assert result.status == Status.SUCCESS and result.input_rows == result.output_rows == 3
    assert path.read_bytes() == raw
    assert workflow.coordinator.process(ProcessingRequest(kind, '2026-01', input_path=path)).status == Status.SKIPPED
    failed = workflow.coordinator.preview(request(kind, raw, '2026-02'))
    assert failed.code == ('output_period_mismatch' if kind == 'repairs' else 'no_output_rows')
    assert failed.diagnostics.summary()['reason_counts']['outside_reporting_period'] == 3


def test_failed_correction_keeps_previous_selected_month(tmp_path):
    engine = ProcessingCoordinator(tmp_path / 'out')
    original = request('repairs', repair_csv(1, 3))
    saved = engine.process(original)
    bad = request('repairs', repair_csv(2, 3))
    result = engine.process(bad)
    assert result.diagnostics is not None and result.code == 'output_period_mismatch'
    assert engine.process(original).artifact == saved.artifact
    assert saved.output_location.read_bytes() == saved.cleaned.output_bytes


def test_diagnostic_observer_cannot_silently_disagree_with_transform(tmp_path, monkeypatch):
    from equipment_data_manager.processing import cleaners
    from equipment_data_manager.processing.diagnostics import CleaningDiagnostics
    monkeypatch.setattr(cleaners, 'explain_rows', lambda *a, **k: CleaningDiagnostics('repairs', '2026-01', 'test', 'test', ()))
    result = ProcessingCoordinator(tmp_path / 'out').preview(request('repairs', repair_csv(1, 3)))
    assert result.code == 'diagnostic_contract_mismatch'
    assert result.status == Status.FAILURE


def test_cli_preview_keeps_date_values_private_by_default_and_writes_nothing(tmp_path, capsys):
    path = tmp_path / 'raw.csv'
    frame = pd.read_csv(BytesIO(repair_csv(1, 3)), dtype=str, keep_default_na=False)
    frame['CompletedDate1'] = ['1/8/2026', '2/3/2026', 'SYNTHETIC_PRIVATE_DATE_CELL']
    path.write_bytes(frame.to_csv(index=False).encode())
    args = ['process', str(path), '--report-type', 'repairs', '--period', '2026-01', '--output-dir', str(tmp_path / 'out'), '--preview']
    assert main(args) == 1
    safe = capsys.readouterr().out
    assert 'SYNTHETIC_PRIVATE_DATE_CELL' not in safe and '1/8/2026' not in safe
    assert json.loads(safe)[0]['diagnostics']['reason_counts']['outside_reporting_period'] == 1
    assert not (tmp_path / 'out').exists()
    assert main(args + ['--include-date-values']) == 1
    detailed = json.loads(capsys.readouterr().out)[0]['diagnostics']['records']
    assert detailed[2]['dates'][0]['raw'] == 'SYNTHETIC_PRIVATE_DATE_CELL'
    assert not (tmp_path / 'out').exists()


@pytest.mark.parametrize('token', ['NA', 'NULL', 'nan', ''])
def test_trace_preserves_literal_csv_date_even_when_original_reader_treats_it_as_missing(tmp_path, token):
    frame = pd.read_csv(BytesIO(repair_csv(1, 3)), dtype=str, keep_default_na=False)
    frame.loc[0, 'CompletedDate1'] = token
    result = ProcessingCoordinator(tmp_path / 'out').preview(request('repairs', frame.to_csv(index=False).encode('utf-8-sig')))
    assert result.status == Status.SUCCESS and result.output_rows == 2
    row = result.diagnostics.records[0]
    assert row.reason == 'invalid_completed_date'
    assert row.dates[0].raw_value == token and row.dates[0].parsed_value is None
