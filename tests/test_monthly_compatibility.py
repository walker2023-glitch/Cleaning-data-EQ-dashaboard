"""Synthetic multi-month regressions; never a trusted departmental baseline."""

from dataclasses import replace
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from threading import Event

import pandas as pd
import pytest

from clean import requests_row_clean as original_requests
from equipment_data_manager.processing.cleaners import LegacyCsvCleaner
from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest, ProcessingStatus as Status, ReportType
from equipment_data_manager.processing.work_orders import TmaXlsxCleaner
from equipment_data_manager.ui.workflow import DesktopWorkflow, selected_files
from report_samples import (REPAIR_COUNTS, SERVICE_COUNTS, TMA_COUNTS, repair_csv, service_csv,
                            tma_rows, tma_xlsx, workbook_bytes)

CASES = [(kind, month, count, factory, extension)
         for kind, counts, factory, extension in (
             ('repairs', REPAIR_COUNTS, repair_csv, 'csv'),
             ('service_orders', SERVICE_COUNTS, service_csv, 'csv'),
             ('tma_work_orders', TMA_COUNTS, tma_xlsx, 'xlsx'))
         for month, count in enumerate(counts, 1)]


def output_frame(result, kind):
    return pd.read_csv(BytesIO(result.cleaned.output_bytes), skiprows=3 if kind == 'repairs' else 1 if kind == 'tma_work_orders' else 0,
                       dtype=str, keep_default_na=False)


@pytest.mark.parametrize('kind,month,count,factory,extension', CASES)
def test_synthetic_month_inventory_preview_process_counts_and_duplicates(tmp_path, kind, month, count, factory, extension):
    raw = factory(month, count)
    source = tmp_path / f'monthly.{extension}'
    source.write_bytes(raw)
    engine = ProcessingCoordinator(tmp_path / 'outputs')
    request = ProcessingRequest(kind, f'2026-{month:02d}', input_path=source)
    preview = engine.preview(request)
    assert preview.status == Status.SUCCESS, preview.code
    assert preview.input_rows == preview.output_rows == count
    assert not engine.store.root.exists()
    saved = engine.process(request)
    assert saved.status == Status.SUCCESS
    assert saved.cleaned.output_bytes == preview.cleaned.output_bytes
    frame = output_frame(saved, kind)
    assert len(frame) == count  # All rows intentionally identical: retain genuine repeated events.
    identifier = 'Equipment ID' if kind == 'repairs' else 'Equipment Id' if kind == 'service_orders' else 'Work Order #'
    assert frame[identifier].eq('000123' if kind == 'tma_work_orders' else '000439').all()
    metrics = {m.name: m.value for m in saved.cleaned.reconciliation_metrics}
    if kind == 'repairs':
        assert frame['Completed Date'].eq(f'2026-{month:02d}-15').all()
        assert metrics['Source repair records'] == metrics['# of Repairs'] == count
        assert metrics['Source reported parts'] == metrics['Parts Cost $'] == count * 10
        assert metrics['Source reported labor'] == metrics['Total Labor $'] == count * 25
        assert metrics['Repair Person-Hrs'] == count * 2
        assert metrics['Source reported cost'] == metrics['Est. Total $'] == count * 35
        assert 'repair_source_totals_differ' not in saved.warnings
        assert frame['Location'].eq('Synthetic Room').all()
        assert frame['Service Vendor'].eq('Synthetic Vendor').all()
    elif kind == 'service_orders':
        assert frame['Sched. Date'].eq(f'2026-{month:02d}-15').all()
        assert frame['Completed Date'].eq(f'2026-{month:02d}-16').all()
        assert frame['Estimated Price'].eq('').all()
        assert frame['Description'].str.contains('\n').all()
        assert metrics['Source service orders'] == count
    else:
        assert frame['Request Date'].eq(f'{month:02d}/15/2026').all()
        assert frame['Assigned To'].eq('').all()
        assert frame['Request'].str.contains('\n').all()
        assert metrics['Source work orders'] == metrics['Retained work orders'] == count
    assert 'production_accuracy_unverified' in saved.warnings
    renamed = replace(request, input_path=None, raw_bytes=raw, source_name=f'renamed.{extension}')
    assert ProcessingCoordinator(engine.store.root).process(renamed).status == Status.SKIPPED
    assert source.read_bytes() == raw


def test_tma_matches_original_transform_and_csv_writer():
    raw = tma_xlsx(1, 3)
    result = TmaXlsxCleaner().clean(raw, source_name='input.xlsx', period='2026-01')
    frame = pd.read_excel(BytesIO(raw), header=1, dtype=str, keep_default_na=False)
    # Original transform discards its total footer itself; adapter validates first.
    cleaned = original_requests.clean_requests_raw(frame)
    output = StringIO(newline='')
    original_requests._write_requests_csv(cleaned, output, '2026-01')
    assert result.output_bytes == output.getvalue().encode()
    assert result.input_rows == result.output_rows == 3
    assert 'Total: 3 records' not in result.output_bytes.decode()


@pytest.mark.parametrize('change,code', [
    ('missing_header', 'unsupported_work_order_layout'),
    ('duplicate_header', 'unsupported_work_order_layout'),
    ('wrong_title', 'work_order_title_period_mismatch'),
    ('wrong_month', 'work_order_title_period_mismatch'),
    ('missing_footer', 'invalid_work_order_summary'),
    ('wrong_count', 'work_order_summary_count_mismatch'),
    ('extra_footer_cell', 'invalid_work_order_summary'),
    ('second_sheet', 'unsupported_work_order_layout'),
    ('extra_column', 'unsupported_work_order_layout'),
    ('cross_month', 'output_period_mismatch'),
])
def test_tma_rejects_unconfirmed_layouts_and_periods(change, code):
    rows = tma_rows(1, 3)
    if change == 'missing_header': rows[1] = ['Wrong'] * 5
    if change == 'duplicate_header': rows[1] = ['Work Order #'] * 5
    if change == 'wrong_title': rows[0][0] = 'Unrecognized export'
    if change == 'wrong_month': rows[0][0] = 'CU Repair WO History — February 2026'
    if change == 'missing_footer': rows = rows[:-1]
    if change == 'wrong_count': rows[-1][0] = 'Total: 4 records'
    if change == 'extra_footer_cell': rows[-1][1] = 'unexpected'
    if change == 'extra_column': rows[1].append('Extra')
    if change == 'cross_month': rows[2][1] = '02/15/2026'
    raw = workbook_bytes(rows, second_sheet=change == 'second_sheet')
    with pytest.raises(ProcessingError, match=code):
        TmaXlsxCleaner().clean(raw, source_name='input.xlsx', period='2026-01')


@pytest.mark.parametrize('raw,extension,code', [
    (b'', 'xlsx', 'empty_input'), (b'not an Excel file', 'xlsx', 'invalid_xlsx_file'),
    (b'Work Order #,Request Date', 'xls', 'legacy_xls_awaiting_sample'),
    (b'Work Order #,Request Date', 'csv', 'unsupported_file_format'),
])
def test_tma_extensions_are_not_guessed_and_failures_do_not_write(tmp_path, raw, extension, code):
    engine = ProcessingCoordinator(tmp_path / 'out')
    result = engine.preview(ProcessingRequest('tma_work_orders', '2026-01', raw_bytes=raw, source_name=f'input.{extension}'))
    assert result.status == Status.FAILURE and result.code == code
    assert not engine.store.root.exists()


@pytest.mark.parametrize('invalid', ['date', 'id'])
def test_tma_original_exclusions_are_reported(invalid):
    rows = tma_rows(1, 3)
    rows[2][1 if invalid == 'date' else 0] = 'invalid' if invalid == 'date' else ''
    result = TmaXlsxCleaner().clean(workbook_bytes(rows), source_name='input.xlsx', period='2026-01')
    assert result.input_rows == 3 and result.output_rows == 2
    assert 'rows_excluded_by_legacy:1' in result.warnings
    if invalid == 'date': assert 'invalid_source_dates:1' in result.warnings


@pytest.mark.parametrize('column,value,code', [
    ('Textbox13', '# of Repairs: 4', 'repair_summary_count_mismatch'),
    ('Textbox11', 'Total Parts: invalid', 'invalid_repair_summary'),
    ('Textbox10', 'Total Labor: $99.00', 'inconsistent_repair_summary'),
])
def test_repair_summaries_are_checked_once_not_summed(column, value, code):
    frame = pd.read_csv(BytesIO(repair_csv(1, 3)), dtype=str, keep_default_na=False)
    frame.loc[0 if column == 'Textbox10' else slice(None), column] = value
    with pytest.raises(ProcessingError, match=code):
        LegacyCsvCleaner(ReportType.REPAIRS).clean(frame.to_csv(index=False).encode(), source_name='raw.csv', period='2026-01')


def test_repair_financial_disagreement_warns_without_changing_calculations():
    raw = repair_csv(1, 3).replace(b'Total Labor: $75.00', b'Total Labor: $90.00')
    result = LegacyCsvCleaner(ReportType.REPAIRS).clean(raw, source_name='raw.csv', period='2026-01')
    metrics = {m.name: m.value for m in result.reconciliation_metrics}
    assert metrics['Source reported labor'] == 90  # Not 3 * 90.
    assert metrics['Total Labor $'] == 75
    assert 'repair_source_totals_differ' in result.warnings


@pytest.mark.parametrize('details,hours', [('', 1), ('found', .5), ('1/2 hr', .5), ('malformed', 1), ('1 5', 1.5)])
def test_observed_repair_layout_keeps_duration_rules(details, hours):
    raw = repair_csv(1, 3).replace(b'2 hours', details.encode())
    result = LegacyCsvCleaner(ReportType.REPAIRS).clean(raw, source_name='raw.csv', period='2026-01')
    metrics = {m.name: m.value for m in result.reconciliation_metrics}
    assert metrics['Repair Person-Hrs'] == Decimal(str(hours)) * 3
    assert metrics['Total Labor $'] == Decimal(str(round(hours * 12.5, 2))) * 3


@pytest.mark.parametrize('status', ['', 'unexpected'])
def test_service_status_fallback_is_visible_without_changing_rule(status):
    frame = pd.read_csv(BytesIO(service_csv(1, 3)), dtype=str, keep_default_na=False)
    frame['Textbox21'] = status
    result = LegacyCsvCleaner(ReportType.SERVICE_ORDERS).clean(frame.to_csv(index=False).encode(), source_name='raw.csv', period='2026-01')
    out = pd.read_csv(BytesIO(result.output_bytes))
    assert out.Status.eq('Completed').all()
    assert 'service_status_inferred:3' in result.warnings


def test_service_cross_month_and_last_day_time_remain_included():
    frame = pd.read_csv(BytesIO(service_csv(1, 3)), dtype=str, keep_default_na=False)
    frame['ScheduledDate'] = '1/31/2026 23:59:59'
    frame['CompletedDate'] = '2/1/2026'
    result = LegacyCsvCleaner(ReportType.SERVICE_ORDERS).clean(frame.to_csv(index=False).encode(), source_name='raw.csv', period='2026-01')
    assert result.input_rows == result.output_rows == 3
    assert 'cross_period_output_dates:3' in result.warnings
    assert b'2026-01-31' in result.output_bytes


@pytest.mark.parametrize('kind,factory,ext', [('repairs', repair_csv, 'csv'), ('service_orders', service_csv, 'csv'), ('tma_work_orders', tma_xlsx, 'xlsx')])
def test_new_layout_correction_duplicate_month_and_failure_safety(tmp_path, kind, factory, ext):
    engine = ProcessingCoordinator(tmp_path / 'out')
    req = ProcessingRequest(kind, '2026-01', raw_bytes=factory(1, 3), source_name=f'monthly.{ext}')
    first = engine.process(req)
    assert first.status == Status.SUCCESS
    corrected = replace(req, raw_bytes=factory(1, 4))
    review = engine.preview(corrected)
    assert review.status == Status.NEEDS_REVIEW
    assert engine.process(corrected).status == Status.NEEDS_REVIEW
    assert engine.process(replace(corrected, raw_bytes=b'invalid')).status == Status.FAILURE
    assert engine.process(req).artifact == first.artifact
    replacement = engine.process(replace(corrected, replacement_token=review.replacement_token))
    assert replacement.status == Status.SUCCESS and replacement.output_rows == 4
    assert replacement.output_location != first.output_location and first.output_location.is_file()
    assert engine.process(corrected).status == Status.SKIPPED
    other_month = engine.process(replace(req, period='2026-02', raw_bytes=factory(2, 3)))
    assert other_month.status == Status.SUCCESS and other_month.output_location != replacement.output_location


def test_tma_gui_workflow_uses_real_engine_and_preserves_source(tmp_path):
    source = tmp_path / 'raw.xlsx'
    source.write_bytes(tma_xlsx(1, 3))
    workflow = DesktopWorkflow(tmp_path / 'out')
    preview = workflow.preview(selected_files([str(source)]), ReportType.TMA_WORK_ORDERS, '2026-01', lambda *_: None, Event())
    assert preview[0].result.code == 'ready_to_process'
    result = workflow.process(preview, {}, lambda *_: None, Event())[0].result
    assert result.status == Status.SUCCESS and result.output_rows == 3


def test_observed_repair_bare_numeric_id_retains_zeros():
    frame = pd.read_csv(BytesIO(repair_csv(1, 3)), dtype=str, keep_default_na=False)
    frame['PersonnelId1'] = '000439'
    result = LegacyCsvCleaner(ReportType.REPAIRS).clean(frame.to_csv(index=False).encode(), source_name='raw.csv', period='2026-01')
    out = pd.read_csv(BytesIO(result.output_bytes), skiprows=3, dtype=str)
    assert out['Equipment ID'].eq('000439').all()


def test_summary_service_invalid_dates_retain_original_exclusion_counts():
    frame = pd.read_csv(BytesIO(service_csv(1, 3)), dtype=str, keep_default_na=False)
    frame.loc[0, ['ScheduledDate', 'CompletedDate']] = 'invalid'
    result = LegacyCsvCleaner(ReportType.SERVICE_ORDERS).clean(frame.to_csv(index=False).encode(), source_name='raw.csv', period='2026-01')
    assert result.input_rows == 3 and result.output_rows == 2
    assert 'invalid_source_dates:2' in result.warnings
    assert 'rows_excluded_by_legacy:1' in result.warnings
    assert {m.name: m.value for m in result.reconciliation_metrics} == {'Source service orders': 3, 'Retained service orders': 2}


def test_tma_excel_date_values_and_empty_assignees():
    from datetime import datetime
    rows = tma_rows(1, 3)
    for row in rows[2:-1]:
        row[1] = datetime(2026, 1, 31, 23, 59)
    result = TmaXlsxCleaner().clean(workbook_bytes(rows), source_name='raw.xlsx', period='2026-01')
    out = pd.read_csv(BytesIO(result.output_bytes), skiprows=1, dtype=str, keep_default_na=False)
    assert out['Request Date'].eq('01/31/2026').all()
    assert out['Assigned To'].eq('').all()


def test_bundled_tma_sample_is_the_reviewed_synthetic_fixture():
    root = Path(__file__).resolve().parents[1]
    assert (root / 'src/equipment_data_manager/resources/samples/tma_sample.xlsx').read_bytes() == (
        root / 'tests/fixtures/synthetic/tma_title_header_footer.xlsx').read_bytes()
