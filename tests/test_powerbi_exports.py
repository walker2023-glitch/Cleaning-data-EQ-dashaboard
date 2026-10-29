"""Invented export contracts; these are not trusted departmental golden outputs."""

import csv
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from io import BytesIO, StringIO
import json
from pathlib import Path

import pandas as pd
import pytest

from equipment_data_manager.__main__ import main
from equipment_data_manager.processing.cleaners import LegacyCsvCleaner
from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest, ProcessingStatus as Status, ReportType
from equipment_data_manager.processing.powerbi import PowerBiCleaner, powerbi_coordinator, schema
from equipment_data_manager.processing.work_orders import TmaXlsxCleaner
from report_samples import (REPAIR_COUNTS, SERVICE_COUNTS, TMA_COUNTS, repair_csv, service_csv, tma_xlsx,
                            tma_rows, workbook_bytes)

CASES = [(kind, month, count, factory, extension)
         for kind, counts, factory, extension in (
             ('repairs', REPAIR_COUNTS, repair_csv, 'csv'),
             ('service_orders', SERVICE_COUNTS, service_csv, 'csv'),
             ('tma_work_orders', TMA_COUNTS, tma_xlsx, 'xlsx'))
         for month, count in enumerate(counts, 1)]


def cleaner(kind):
    kind = ReportType(kind)
    base = TmaXlsxCleaner() if kind == ReportType.TMA_WORK_ORDERS else LegacyCsvCleaner(kind)
    return PowerBiCleaner(kind, base)


def parse(result):
    return list(csv.DictReader(StringIO(result.output_bytes.decode('utf-8'), newline='')))


@pytest.mark.parametrize('kind,month,count,factory,extension', CASES)
def test_monthly_contract_counts_numeric_and_date_format(kind, month, count, factory, extension):
    adapter = cleaner(kind)
    raw = factory(month, count)
    candidate = adapter.clean(raw, source_name=f'monthly.{extension}', period=f'2026-{month:02d}')
    records = parse(candidate)
    header, *body = list(csv.reader(StringIO(candidate.output_bytes.decode('utf-8'), newline='')))
    assert header == [field.name for field in schema(ReportType(kind))]
    assert len(set(header)) == len(header) and '' not in header
    assert len(body) == len(records) == candidate.output_rows == candidate.input_rows == count
    assert all(len(row) == len(header) for row in body)
    assert not any('Unnamed' in column for column in header)
    assert not candidate.output_bytes.startswith(b'\xef\xbb\xbf')
    assert len({record['RecordId'] for record in records}) == count  # Repeated transactions stay separate.
    assert {record['ReportMonth'] for record in records} == {f'2026-{month:02d}'}
    assert {record['ValidationStatus'] for record in records} == {'CandidateUnverified'}
    assert {record['SchemaVersion'] for record in records} == {'1'}
    assert {record['SourceFileSHA256'] for record in records} == {sha256(raw).hexdigest()}
    assert 'production_publication_blocked' in candidate.warnings
    assert 'production_accuracy_unverified' in candidate.warnings
    for record in records:
        assert record['EquipmentId' if kind != 'tma_work_orders' else 'WorkOrderId'] == ('000439' if kind != 'tma_work_orders' else '000123')
        assert len(record['LegacyCandidateSHA256']) == 64
        for field in candidate.schema:
            value = record[field.name]
            if field.data_type in ('decimal', 'integer') and value:
                assert Decimal(value).is_finite() and '$' not in value and ',' not in value
            if field.data_type == 'date' and value:
                assert value.startswith(f'2026-{month:02d}-') and len(value) == 10
    if kind == 'repairs':
        assert records[0]['RepairCount'] == '1'
        assert Decimal(records[0]['RepairPersonHours']) == 2
        assert Decimal(records[0]['LaborCost']) == 25
        assert Decimal(records[0]['PartsCost']) == 10
        assert Decimal(records[0]['EstimatedTotalCost']) == 35
        assert records[0]['Description'].startswith('Synthetic inspection')
        assert records[0]['Details'] == '2 hours'
    elif kind == 'service_orders':
        assert records[0]['EstimatedPrice'] == ''
        assert records[0]['SourceMaintenanceTag'] == 'PM'
        assert records[0]['RawDescription'].endswith(' - (PM)')
        assert not records[0]['Description'].endswith('(PM)')
    else:
        assert records[0]['RequestDate'] == f'2026-{month:02d}-15'
        assert records[0]['AssignedTo'] == ''
    baseline = adapter.base.clean(raw, source_name=f'monthly.{extension}', period=f'2026-{month:02d}')
    assert records[0]['LegacyCandidateSHA256'] == sha256(baseline.output_bytes).hexdigest()
    assert candidate.reconciliation_metrics[0].value == baseline.reconciliation_metrics[0].value
    assert candidate.reconciliation_metrics[0].name.startswith('Legacy ')


@pytest.mark.parametrize('raw_parts,available', [('', False), ('not-money', False), ('NULL', False), ('$0.00', True), ('$10.00', True), ('-$1.50', True)])
def test_missing_financial_values_are_null_and_legacy_formula_is_preserved(raw_parts, available):
    frame = pd.read_csv(BytesIO(repair_csv(1, 3)), dtype=str, keep_default_na=False)
    frame['Textbox38'] = raw_parts
    raw = frame.to_csv(index=False).encode()
    adapter = cleaner('repairs')
    base = adapter.base.clean(raw, source_name='raw.csv', period='2026-01')
    old = list(csv.DictReader(StringIO(base.output_bytes.decode().split('\n', 3)[3])))
    rows = parse(adapter.clean(raw, source_name='raw.csv', period='2026-01'))
    for row, legacy in zip(rows, old):
        assert Decimal(row['LegacyPartsCost']) == Decimal(legacy['Parts Cost $'])
        assert Decimal(row['LegacyEstimatedTotalCost']) == Decimal(legacy['Est. Total $'])
        assert Decimal(row['LaborCost']) == Decimal(legacy['Total Labor $'])
        assert row['RawPartsCost'] == raw_parts
        assert (row['PartsCost'] != '') == available
        assert (row['EstimatedTotalCost'] != '') == available
        if available:
            assert Decimal(row['PartsCost']) == Decimal(legacy['Parts Cost $'])
            assert Decimal(row['EstimatedTotalCost']) == Decimal(legacy['Est. Total $'])


def test_source_occurrence_mapping_survives_exclusions_and_preserves_raw_text_and_tags():
    frame = pd.read_csv(BytesIO(service_csv(1, 4)), dtype=str, keep_default_na=False)
    frame.loc[0, 'Description'] = '- (PM)'  # Existing exclusion, not restored into the export.
    frame.loc[1, 'Description'] = 'Synthetic café, "équipement" — 🛠\nSecond line - (Repair)'
    frame.loc[2, 'Description'] = 'Synthetic untagged event'
    frame.loc[3, 'Description'] = 'Synthetic check - (PM)'
    raw = frame.to_csv(index=False).encode('utf-8-sig')
    result = cleaner('service_orders').clean(raw, source_name='synthetic.csv', period='2026-01')
    rows = parse(result)
    assert result.input_rows == 4 and result.output_rows == 3
    assert [r['SourceRecordNumber'] for r in rows] == ['2', '3', '4']
    assert [r['CandidateRecordNumber'] for r in rows] == ['1', '2', '3']
    assert [r['SourceMaintenanceTag'] for r in rows] == ['Repair', '', 'PM']
    assert rows[0]['RawDescription'] == frame.loc[1, 'Description']
    assert rows[0]['Description'] == 'Synthetic café, "équipement" — 🛠\nSecond line'
    assert not any('Classification' in field.name or field.name == 'MaintenanceType' for field in result.schema)


def test_priced_layout_can_retain_literal_zeros_but_never_invents_them():
    frame = pd.read_csv(BytesIO(service_csv(1, 3)), dtype=str, keep_default_na=False)
    frame = frame.drop(columns='Textbox56')
    frame['Cost'] = '$12.50'
    frame['EquipmentId1'] = ['000439', '000439', '000439']
    raw = frame.to_csv(index=False).encode()
    adapter = cleaner('service_orders')
    legacy = adapter.base.clean(raw, source_name='raw.csv', period='2026-01')
    assert list(csv.DictReader(StringIO(legacy.output_bytes.decode())))[0]['Equipment Id'] == '439'
    assert {r['EquipmentId'] for r in parse(adapter.clean(raw, source_name='raw.csv', period='2026-01'))} == {'000439'}
    frame['EquipmentId1'] = '439'
    assert {r['EquipmentId'] for r in parse(adapter.clean(frame.to_csv(index=False).encode(), source_name='raw.csv', period='2026-01'))} == {'439'}


def test_tma_filtered_records_do_not_get_guessed_source_row_numbers():
    rows = tma_rows(1, 3)
    rows[2][1] = 'invalid-date'
    result = cleaner('tma_work_orders').clean(workbook_bytes(rows), source_name='raw.xlsx', period='2026-01')
    assert result.output_rows == 2
    assert {r['SourceRecordNumber'] for r in parse(result)} == {''}
    assert 'source_record_numbers_unavailable' in result.warnings


def test_broken_candidates_or_wrong_source_trace_fail_closed():
    adapter = cleaner('repairs')
    raw = repair_csv(1, 3)
    candidate = adapter.base.clean(raw, source_name='raw.csv', period='2026-01')

    class Broken:
        version = adapter.base.version
        def clean(self, *args, **kwargs):
            return replace(candidate, output_bytes=candidate.output_bytes.replace(b'Equipment ID,', b'Equipment ID,,'))

    with pytest.raises(ProcessingError, match='invalid_legacy_export_schema'):
        PowerBiCleaner('repairs', Broken()).clean(raw, source_name='raw.csv', period='2026-01')

    class Misaligned:
        version = adapter.base.version
        def clean(self, *args, **kwargs):
            return replace(candidate, diagnostics=None)

    with pytest.raises(ProcessingError, match='normalization_source_alignment_failed'):
        PowerBiCleaner('repairs', Misaligned()).clean(raw, source_name='raw.csv', period='2026-01')


def test_legacy_artifact_retained_and_normalized_corrections_use_bound_review(tmp_path):
    legacy, normalized = ProcessingCoordinator(tmp_path / 'outputs'), powerbi_coordinator(tmp_path / 'outputs')
    req = ProcessingRequest('repairs', '2026-01', raw_bytes=repair_csv(1, 3), source_name='report.csv')
    original = legacy.process(req)
    first = normalized.process(req)
    assert original.status == first.status == Status.SUCCESS
    assert original.output_location != first.output_location
    assert original.output_location.read_bytes() == original.cleaned.output_bytes
    assert legacy.process(req).status == normalized.process(req).status == Status.SKIPPED
    correction = replace(req, raw_bytes=repair_csv(1, 4))
    review = normalized.preview(correction)
    assert review.status == Status.NEEDS_REVIEW
    assert normalized.process(correction).status == Status.NEEDS_REVIEW
    assert normalized.process(replace(correction, raw_bytes=b'invalid')).status == Status.FAILURE
    assert normalized.process(req).artifact == first.artifact
    replacement = normalized.process(replace(correction, replacement_token=review.replacement_token))
    assert replacement.status == Status.SUCCESS and replacement.output_rows == 4
    assert first.output_location.read_bytes() == first.cleaned.output_bytes
    assert original.output_location.read_bytes() == original.cleaned.output_bytes
    assert legacy.process(req).status == Status.SKIPPED
    assert len(normalized.store.history()) == 2
    assert not (tmp_path / 'outputs' / 'approved_current').exists()


def test_flat_folder_combination_of_synthetic_selected_months_has_one_header_and_no_history(tmp_path):
    # Simulation only: the application does not publish into an approved folder.
    folder = tmp_path / 'synthetic-folder-ingestion'
    folder.mkdir()
    engine = powerbi_coordinator(tmp_path / 'candidate-store')
    for month in (1, 2):
        req = ProcessingRequest('service_orders', f'2026-{month:02d}', raw_bytes=service_csv(month, 3), source_name='same.csv')
        saved = engine.process(req)
        (folder / saved.output_location.name).write_bytes(saved.cleaned.output_bytes)
    files = list(folder.glob('*.csv'))
    tables = [pd.read_csv(path, encoding='utf-8', dtype=str, keep_default_na=False) for path in files]
    assert len(files) == 2 and tables[0].columns.tolist() == tables[1].columns.tolist()
    combined = pd.concat(tables, ignore_index=True)
    assert len(combined) == 6 and combined.RecordId.nunique() == 6
    assert combined.EquipmentId.eq('000439').all()
    assert set(combined.ReportMonth) == {'2026-01', '2026-02'}
    assert not any(name.startswith('Unnamed') for name in combined.columns)


def test_cli_powerbi_preview_and_candidate_store_are_separate(tmp_path, capsys):
    source = tmp_path / 'raw.csv'
    source.write_bytes(repair_csv(1, 3))
    args = ['process', str(source), '--report-type', 'repairs', '--period', '2026-01', '--output-dir', str(tmp_path / 'out'), '--output-format', 'powerbi']
    assert main(args + ['--preview']) == 0
    preview = json.loads(capsys.readouterr().out)[0]
    assert preview['code'] == 'ready_to_process'
    assert not (tmp_path / 'out').exists()
    assert main(args) == 0
    saved = json.loads(capsys.readouterr().out)[0]
    assert Path(saved['output_location']).is_relative_to(tmp_path / 'out/powerbi_candidates')
    assert 'production_publication_blocked' in saved['warnings']
    assert source.read_bytes() == repair_csv(1, 3)


def test_unknown_source_metadata_is_explicitly_warned_not_silently_added_to_schema():
    frame = pd.read_csv(BytesIO(repair_csv(1, 3)), dtype=str, keep_default_na=False)
    frame['AdditionalPrivateColumn'] = 'SYNTHETIC_PRIVATE_METADATA'
    result = cleaner('repairs').clean(frame.to_csv(index=False).encode(), source_name='raw.csv', period='2026-01')
    assert 'normalized_unmapped_source_columns:1' in result.warnings
    assert 'SYNTHETIC_PRIVATE_METADATA' not in result.output_bytes.decode()
    assert 'SYNTHETIC_PRIVATE_METADATA' not in repr(result.warnings)


@pytest.mark.parametrize('old,new,code', [
    (b'25.0', b'inf', 'invalid_normalized_number'),
    (b'2026-01-15', b'01/15/2026', 'invalid_normalized_date'),
])
def test_malformed_candidate_values_fail_before_selecting_normalized_output(old, new, code):
    adapter = cleaner('repairs')
    raw = repair_csv(1, 3)
    candidate = adapter.base.clean(raw, source_name='raw.csv', period='2026-01')

    class Broken:
        version = adapter.base.version
        def clean(self, *args, **kwargs):
            return replace(candidate, output_bytes=candidate.output_bytes.replace(old, new))

    with pytest.raises(ProcessingError, match=code):
        PowerBiCleaner('repairs', Broken()).clean(raw, source_name='raw.csv', period='2026-01')


@pytest.mark.parametrize('status', ['', 'unrecognized-status'])
def test_raw_status_survives_existing_date_based_status_fallback(status):
    frame = pd.read_csv(BytesIO(service_csv(1, 3)), dtype=str, keep_default_na=False)
    frame['Textbox21'] = status
    result = cleaner('service_orders').clean(frame.to_csv(index=False).encode(), source_name='raw.csv', period='2026-01')
    assert {row['RawStatus'] for row in parse(result)} == {status}
    assert {row['Status'] for row in parse(result)} == {'Completed'}
    assert 'service_status_inferred:3' in result.warnings
