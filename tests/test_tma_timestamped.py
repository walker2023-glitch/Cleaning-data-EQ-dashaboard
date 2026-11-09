"""Synthetic owner-described timestamped layout; actual owner acceptance is manual."""
import csv
from datetime import datetime
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
from threading import Event

import pytest
import xlrd
from openpyxl import load_workbook

from report_samples import tma_xlsx
from equipment_data_manager.historical import discover_history, filename_match
from equipment_data_manager.monthly import Workspace, discover
from equipment_data_manager.processing._legacy import requests_row_clean as legacy
from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest, ReportType
from equipment_data_manager.processing.powerbi import PowerBiCleaner, schema
from equipment_data_manager.processing.work_orders import TmaXlsxCleaner, generation_timestamp, read_workbook, TIMESTAMPED_SHEET
from equipment_data_manager.powerquery_contract import read_table
from equipment_data_manager.storage.local import LocalFolderStorage
from equipment_data_manager.ui.workflow import DesktopWorkflow

ROOT=Path(__file__).parent/'fixtures/synthetic/tma_timestamped'
NAME='CU_Repair_WO_History_-_Previous_Month_(HI-042b)123456789012345678.xls'


def raw(name='may_small.xls'):
    return (ROOT/name).read_bytes()


def clean(name='may_small.xls', period='2026-05'):
    return TmaXlsxCleaner().clean(raw(name),source_name=NAME,period=period)


def output(result):
    return list(csv.reader(StringIO(result.output_bytes.decode())))[2:]


@pytest.mark.parametrize('name,source_count', [('may_small.xls',3),('may_81.xls',81)])
def test_exact_shape_reads_all_records_including_last_no_assumed_footer(name,source_count):
    book=xlrd.open_workbook(file_contents=raw(name))
    sheet=book.sheet_by_index(0)
    assert sheet.nrows==source_count+4 and sheet.ncols==4 and sheet.name==TIMESTAMPED_SHEET
    result=clean(name)
    assert result.input_rows==result.output_rows==source_count
    assert len(output(result))==source_count
    assert output(result)[-1][0]=='000439'  # Last-row zero-format normalization must not be skipped as a footer.
    assert all(row[4]=='' for row in output(result))
    assert f'tma_physical_worksheet_rows:{source_count+4}' in result.warnings
    assert f'tma_parseable_source_request_dates:{source_count}' in result.warnings
    assert f'tma_assigned_to_source_column_missing_retained:{source_count}' in result.warnings
    metrics={m.name:m.value for m in result.reconciliation_metrics}
    assert metrics['Source work orders']==source_count
    assert metrics['Physical worksheet rows']==source_count+4
    assert metrics['Parseable source request dates']==source_count
    assert metrics['Source request dates outside selected month']==0


def test_numeric_owner_timestamp_and_workbook_datemode_are_used_without_text_guessing():
    _,_,metadata=read_workbook(raw('may_81.xls'),'.xls',include_metadata=True)
    assert metadata['timestamp_value']==46174.31306712963
    stamp=generation_timestamp(metadata)
    assert stamp==datetime(2026,6,1,7,30,49)
    assert clean('may_1904.xls').output_rows==3


@pytest.mark.parametrize('name,period', [('june.xls','2026-06'),('december_rollover.xls','2025-12')])
def test_generation_following_month_and_year_rollover(name,period):
    result=clean(name,period)
    assert result.source_period==period and result.output_rows==3
    assert all(row[1][-4:]=='2025' if period=='2025-12' else row[1].startswith('06/') for row in output(result))


@pytest.mark.parametrize('name', ['may_text_timestamp.xls','may_iso_text_timestamp.xls','may_missing_timestamp.xls',
    'may_negative_timestamp.xls','may_huge_timestamp.xls','may_boolean_timestamp.xls','may_fictional_timestamp.xls',
    'may_extra_timestamp_cell.xls'])
def test_unsupported_or_ambiguous_timestamp_types_and_values_are_rejected(name):
    with pytest.raises(ProcessingError,match='^tma_generation_timestamp_invalid$'):
        clean(name)


@pytest.mark.parametrize('value', [float('nan'),float('inf'),float('-inf'),True,0,-1,1e100])
def test_nonfinite_nondate_serials_fail_safely(value):
    with pytest.raises(ProcessingError,match='tma_generation_timestamp_invalid'):
        generation_timestamp(dict(timestamp_kind=2,timestamp_value=value,timestamp_datemode=0))


@pytest.mark.parametrize('period', ['2026-04','2026-06','2025-05'])
def test_generation_previous_month_must_agree_with_selected_month(period):
    with pytest.raises(ProcessingError,match='^tma_generation_period_mismatch$'):
        clean(period=period)


@pytest.mark.parametrize('name,code', [('may_wrong_title.xls','tma_timestamped_title_invalid'),
    ('may_wrong_sheet.xls','tma_timestamped_sheet_mismatch'),('may_extra_sheet.xls','unsupported_work_order_layout'),
    ('may_separator.xls','tma_timestamped_separator_invalid'),('may_headers.xls','tma_timestamped_headers_invalid'),
    ('may_missing_header.xls','tma_timestamped_headers_invalid'),('may_footer.xls','tma_timestamped_unexpected_footer'),
    ('may_extra_column.xls','tma_timestamped_columns_mismatch'),('may_extra_title_cell.xls','tma_timestamped_title_invalid'),
    ('may_wrong_date.xls','output_period_mismatch')])
def test_malformed_structures_or_cross_month_dates_fail_before_writes(tmp_path,name,code):
    result=ProcessingCoordinator(tmp_path/'out').preview(ProcessingRequest('tma_work_orders','2026-05',raw_bytes=raw(name),source_name=NAME))
    assert result.status=='failure' and result.code==code
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('name,warning', [('may_invalid_date.xls','invalid_source_dates:1'),('may_blank_id.xls','rows_excluded_by_legacy:1')])
def test_existing_exclusions_are_preserved_not_replaced_with_invented_values(name,warning):
    result=clean(name)
    assert result.input_rows==3 and result.output_rows==2
    assert warning in result.warnings and 'rows_excluded_by_legacy:1' in result.warnings
    assert 'tma_assigned_to_source_column_missing_records:3' in result.warnings
    assert 'tma_assigned_to_source_column_missing_retained:2' in result.warnings


def test_legitimate_repeated_work_orders_are_retained_and_writer_stays_identical():
    frame,_,_=read_workbook(raw('june.xls'),'.xls',include_metadata=True)
    body=frame.iloc[4:].copy();body.columns=legacy.REQUEST_COLUMNS[:-1]
    expected=legacy.clean_requests_raw(body)
    buffer=StringIO(newline='');legacy._write_requests_csv(expected,buffer,'2026-06')
    result=clean('june.xls','2026-06')
    assert result.output_bytes==buffer.getvalue().encode()
    assert [row[0] for row in output(result)]==['000123']*3


@pytest.mark.parametrize('month',[1,2,3,4,5,6])
def test_standard_xlsx_with_same_sheet_name_still_requires_and_uses_its_footer(month):
    source=tma_xlsx(month,3)
    book=load_workbook(BytesIO(source));book.active.title=TIMESTAMPED_SHEET
    stream=BytesIO();book.save(stream);book.close()
    result=TmaXlsxCleaner().clean(stream.getvalue(),source_name='standard.xlsx',period=f'2026-{month:02d}')
    assert result.output_rows==3 and 'tma_timestamped_previous_month_layout' not in result.warnings
    book=load_workbook(BytesIO(source));book.active.delete_rows(book.active.max_row)
    stream=BytesIO();book.save(stream);book.close()
    with pytest.raises(ProcessingError,match='invalid_work_order_summary'):
        TmaXlsxCleaner().clean(stream.getvalue(),source_name='standard.xlsx',period=f'2026-{month:02d}')


def test_normalized_output_schema_ids_dates_missing_values_and_provenance():
    source=raw('may_81.xls')
    result=PowerBiCleaner(ReportType.TMA_WORK_ORDERS,TmaXlsxCleaner()).clean(source,source_name=NAME,period='2026-05')
    rows=list(csv.DictReader(StringIO(result.output_bytes.decode())))
    assert list(rows[0])==[c.name for c in schema(ReportType.TMA_WORK_ORDERS)]
    assert len(rows)==81 and rows[-1]['WorkOrderId']=='000439'
    assert all(r['AssignedTo']=='' and r['SourceFileName']==NAME and r['SourceFileSHA256']==sha256(source).hexdigest() for r in rows)
    assert all(r['ValidationStatus']=='CandidateUnverified' and r['RequestDate'].startswith('2026-05-') for r in rows)
    assert len(read_table(result.output_bytes,ReportType.TMA_WORK_ORDERS,allow_candidates=True))==81


@pytest.mark.parametrize('layout',['standard','sharepoint_year_month'])
def test_discovery_preview_process_source_changes_and_immutable_corrections(tmp_path,layout):
    workspace=Workspace(tmp_path/'raw',tmp_path/'local-candidates',tmp_path/'reserved')
    folder=workspace.raw_folder/('2026-05/tma_work_orders' if layout=='standard' else '2026/2026-05 (May)')
    folder.mkdir(parents=True);source=folder/NAME;source.write_bytes(raw())
    assert filename_match(NAME,'2026-05')==(ReportType.TMA_WORK_ORDERS,'')
    inventory=discover_history(LocalFolderStorage(workspace.raw_folder),'2026-05','2026-05',layout)
    assert inventory.months[0].reports[2].status=='found'
    selection=discover(workspace,'2026-05',folder_layout=layout)
    workflow=DesktopWorkflow(workspace.candidate_folder,output_format='powerbi')
    preview=workflow.preview_month(selection,lambda *a:None,Event())
    assert preview[0].result.status=='success' and not workspace.candidate_folder.exists()
    first=workflow.process(preview,{},lambda *a:None,Event())[0].result.artifact
    assert first and first.source_hash==sha256(raw()).hexdigest()
    again=workflow.preview_month(selection,lambda *a:None,Event())
    assert again[0].result.status=='skipped'
    source.write_bytes(raw('may_81.xls'))
    failed=workflow.process(again,{},lambda *a:None,Event())[0].result
    assert failed.status=='failure'
    selection=discover(workspace,'2026-05',folder_layout=layout)
    correction=workflow.preview_month(selection,lambda *a:None,Event())
    assert correction[0].result.status=='needs_review'
    result=workflow.coordinator.process(ProcessingRequest('tma_work_orders','2026-05',input_path=source,
        replacement_token=correction[0].result.replacement_token))
    assert result.status=='success' and result.output_rows==81
    assert first.output_path.exists() and first.output_hash==sha256(first.output_path.read_bytes()).hexdigest()
    assert len(workflow.coordinator.store.history())==2 and source.read_bytes()==raw('may_81.xls')
    assert not workspace.approved_folder.exists()


def test_bundled_timestamped_sample_is_synthetic_june_fixture():
    sample=Path(__file__).resolve().parents[1]/'src/equipment_data_manager/resources/samples/tma_timestamped_sample.xls'
    assert sample.read_bytes()==raw('formatting_june.xls')
