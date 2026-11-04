"""Synthetic BIFF8 only; no claim that the actual May report has this layout."""
import csv
from dataclasses import replace
from datetime import date
from hashlib import sha256
from io import StringIO
from pathlib import Path
from threading import Event

import pandas as pd
import pytest
import xlrd

from report_samples import tma_rows, tma_xlsx, workbook_bytes
from equipment_data_manager.historical import discover_history, filename_match
from equipment_data_manager.monthly import Workspace, discover
from equipment_data_manager.processing._legacy import requests_row_clean as legacy
from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest, ReportType
from equipment_data_manager.processing.powerbi import PowerBiCleaner, schema
from equipment_data_manager.processing.repair_financial import powerbi_coordinator
from equipment_data_manager.processing.work_orders import TmaXlsxCleaner
from equipment_data_manager.powerquery_contract import read_table
from equipment_data_manager.storage.local import LocalFolderStorage
from equipment_data_manager.ui.workflow import DesktopWorkflow

FIXTURES = Path(__file__).parent / 'fixtures/synthetic/legacy_tma'
NAME = 'CU_Repair_WO_History_-_Previous_Month_(HI-042b)123456789012345678.xls'


def raw(name='may_four_columns.xls'):
    return (FIXTURES / name).read_bytes()


def clean(name='may_four_columns.xls'):
    return TmaXlsxCleaner().clean(raw(name), source_name=NAME, period='2026-05')


def records(result):
    return list(csv.DictReader(StringIO(result.output_bytes.decode())))


@pytest.mark.parametrize('name', [NAME, NAME.upper(), NAME.replace('123456789012345678','1'), NAME.replace('123456789012345678','9876543210')])
def test_strict_legacy_filename_family_does_not_infer_previous_month(name):
    assert filename_match(name,'2026-05') == (ReportType.TMA_WORK_ORDERS,'')
    assert filename_match(name,'2025-01') == (ReportType.TMA_WORK_ORDERS,'')


@pytest.mark.parametrize('name', ['random.xls','CU_Repair_WO_History.xls', NAME.replace('HI-042b','HI-042c'),
    NAME.replace('123456789012345678',''),NAME.replace('123456789012345678','123-copy'),NAME.replace('.xls','.xlsx'),
    NAME+'.bak',NAME.replace('123456789012345678','1'*31)])
def test_near_misses_are_not_classified_as_tma(name):
    assert filename_match(name,'2026-05')[0] is None


@pytest.mark.parametrize('assigned', [False,True])
def test_xls_uses_original_transform_and_writer_without_schema_changes(assigned):
    name = 'may_five_columns.xls' if assigned else 'may_four_columns.xls'
    frame = pd.read_excel(FIXTURES/name, header=1, dtype=str, keep_default_na=False,engine='xlrd')
    expected = legacy.clean_requests_raw(frame)
    output=StringIO(newline='');legacy._write_requests_csv(expected,output,'2026-05')
    result=clean(name)
    assert result.output_bytes == output.getvalue().encode()
    assert result.input_rows == result.output_rows == 2
    rows = list(csv.reader(StringIO(result.output_bytes.decode())))
    assert rows[1] == legacy.REQUEST_COLUMNS and len(rows)==4
    assert rows[2][0]=='000123' and rows[3][0]=='WO-A0007'
    assert rows[2][1]=='05/15/2026'
    assert 'tma_assigned_to_source_column_missing' in result.warnings if not assigned else 'tma_assigned_to_source_column_missing' not in result.warnings


def test_four_columns_emit_missing_source_and_retained_counts_with_blank_csv_nulls():
    result=PowerBiCleaner(ReportType.TMA_WORK_ORDERS,TmaXlsxCleaner()).clean(raw(),source_name=NAME,period='2026-05')
    rows=records(result)
    assert list(rows[0])==[column.name for column in schema(ReportType.TMA_WORK_ORDERS)]
    assert [r['AssignedTo'] for r in rows]==['','']  # CSV's absent-value representation, never a fake employee.
    assert rows[0]['WorkOrderId']=='000123' and rows[1]['WorkOrderId']=='WO-A0007'
    assert all(r['RequestDate']=='2026-05-15' and r['SourceFileName']==NAME for r in rows)
    assert all(r['SourceFileSHA256']==sha256(raw()).hexdigest() and r['ValidationStatus']=='CandidateUnverified' for r in rows)
    assert 'tma_assigned_to_source_column_missing_records:2' in result.warnings
    assert 'tma_assigned_to_source_column_missing_retained:2' in result.warnings
    contract = read_table(result.output_bytes,ReportType.TMA_WORK_ORDERS,allow_candidates=True)
    assert contract[0]['RequestDate']==date(2026,5,15)


def test_present_but_blank_assignment_stays_missing_without_missing_column_warning():
    result = PowerBiCleaner(ReportType.TMA_WORK_ORDERS,TmaXlsxCleaner()).clean(raw('may_five_columns.xls'),source_name=NAME,period='2026-05')
    assert [r['AssignedTo'] for r in records(result)] == ['', 'Synthetic Technician']
    assert 'tma_assigned_to_source_column_missing' not in result.warnings


@pytest.mark.parametrize('name', ['may_formatted_identifier.xls','may_native_dates.xls'])
def test_zero_formatted_integer_identifiers_and_excel_date_cells_are_preserved(name):
    result=PowerBiCleaner(ReportType.TMA_WORK_ORDERS,TmaXlsxCleaner()).clean(raw(name),source_name=NAME,period='2026-05')
    assert records(result)[0]['WorkOrderId']=='000123'
    assert records(result)[0]['RequestDate']=='2026-05-15'


@pytest.mark.parametrize('name,code', [('may_multiple_sheets.xls','unsupported_work_order_layout'),
    ('may_missing_required_header.xls','unsupported_work_order_layout'),('may_wrong_dates.xls','output_period_mismatch'),
    ('may_ambiguous_identifier.xls','ambiguous_work_order_identifier'),('encrypted_marker.xls','invalid_xls_file')])
def test_invalid_ambiguous_encrypted_and_cross_period_workbooks_fail_before_output(tmp_path,name,code):
    engine = ProcessingCoordinator(tmp_path/'candidates')
    result=engine.preview(ProcessingRequest('tma_work_orders','2026-05',raw_bytes=raw(name),source_name=NAME))
    assert result.status=='failure' and result.code==code
    assert not engine.store.root.exists()


def test_encrypted_fixture_has_real_biff_filepass_rejection():
    with pytest.raises(xlrd.XLRDError,match='encrypt'):
        xlrd.open_workbook(file_contents=raw('encrypted_marker.xls'))


@pytest.mark.parametrize('bad', [b'not Excel',b'<html>synthetic</html>',b'PK\x03\x04SYNTHETIC ZIP', raw()[:128]])
def test_xls_suffix_never_allows_arbitrary_csv_html_xml_or_corruption(bad):
    with pytest.raises(ProcessingError,match='invalid_xls_file'):
        TmaXlsxCleaner().clean(bad,source_name=NAME,period='2026-05')


def test_actual_xlsx_renamed_xls_is_not_accepted():
    with pytest.raises(ProcessingError,match='invalid_xls_file'):
        TmaXlsxCleaner().clean(tma_xlsx(5,2),source_name=NAME,period='2026-05')


@pytest.mark.parametrize('month', [1,2,3,4])
def test_existing_xlsx_january_through_april_still_matches_original(month):
    source=tma_xlsx(month,3)
    expected=legacy.clean_requests_raw(pd.DataFrame(tma_rows(month,3)[2:-1],columns=legacy.REQUEST_COLUMNS))
    output=StringIO(newline='');legacy._write_requests_csv(expected,output,f'2026-{month:02d}')
    result=TmaXlsxCleaner().clean(source,source_name='monthly.xlsx',period=f'2026-{month:02d}')
    assert result.output_bytes==output.getvalue().encode() and result.output_rows==3


def test_four_column_xlsx_uses_same_missing_assignment_behavior():
    rows=[row[:4] for row in tma_rows(5,2)]
    result=TmaXlsxCleaner().clean(workbook_bytes(rows),source_name='reviewed-copy.xlsx',period='2026-05')
    assert result.output_rows==2 and 'tma_assigned_to_source_column_missing' in result.warnings


def test_legacy_exclusions_and_repeated_business_records_remain_unchanged():
    rows=[row[:4] for row in tma_rows(5,3)]
    rows[3][0]=''  # Existing missing-ID exclusion, not a new deduplication rule.
    result=TmaXlsxCleaner().clean(workbook_bytes(rows),source_name='synthetic.xlsx',period='2026-05')
    assert result.output_rows==2 and 'rows_excluded_by_legacy:1' in result.warnings
    assert 'tma_assigned_to_source_column_missing_records:3' in result.warnings
    assert 'tma_assigned_to_source_column_missing_retained:2' in result.warnings
    output=list(csv.reader(StringIO(result.output_bytes.decode())))
    assert output[2][0]==output[3][0]=='000123'


@pytest.mark.parametrize('layout', ['standard','sharepoint_year_month'])
def test_discovery_preview_process_skip_correction_and_immutable_revisions(tmp_path,layout):
    workspace=Workspace(tmp_path/'raw',tmp_path/'candidates',tmp_path/'approved')
    folder=workspace.raw_folder/('2026-05/tma_work_orders' if layout=='standard' else '2026/2026-05 (May)')
    folder.mkdir(parents=True)
    source=folder/NAME;source.write_bytes(raw())
    inventory=discover_history(LocalFolderStorage(workspace.raw_folder),'2026-05','2026-05',layout)
    report=inventory.months[0].reports[2]
    assert report.status=='found' and report.sources[0].sha256==sha256(raw()).hexdigest()
    selection=discover(workspace,'2026-05',folder_layout=layout)
    workflow=DesktopWorkflow(workspace.candidate_folder,output_format='powerbi')
    preview=workflow.preview_month(selection,lambda *a:None,Event())
    assert len(preview)==1 and preview[0].result.status=='success' and not workspace.candidate_folder.exists()
    result=workflow.process(preview,{},lambda *a:None,Event())[0].result
    first=result.artifact
    assert result.status=='success' and result.output_rows==2
    again=workflow.preview_month(selection,lambda *a:None,Event())
    assert again[0].result.status=='skipped'
    source.write_bytes(raw('may_five_columns.xls'))
    if layout=='sharepoint_year_month':
        stale=workflow.preview_month(selection,lambda *a:None,Event())
        assert stale[0].result.code=='storage_source_changed'
    selection=discover(workspace,'2026-05',folder_layout=layout)
    proposed=workflow.preview_month(selection,lambda *a:None,Event())
    assert proposed[0].result.status=='needs_review' and proposed[0].result.previous.revision_id==first.revision_id
    # Existing coordinator token mechanism; no business approval is established.
    request=ProcessingRequest('tma_work_orders','2026-05',input_path=source,replacement_token=proposed[0].result.replacement_token)
    corrected=workflow.coordinator.process(request)
    assert corrected.status=='success' and corrected.artifact.revision_id!=first.revision_id
    assert first.output_path.exists() and sha256(first.output_path.read_bytes()).hexdigest()==first.output_hash
    assert source.read_bytes()==raw('may_five_columns.xls') and not workspace.approved_folder.exists()


def test_two_xls_xlsx_tma_matches_are_ambiguous_no_preference(tmp_path):
    folder=tmp_path/'2026/2026-05 (May)';folder.mkdir(parents=True)
    (folder/NAME).write_bytes(raw())
    (folder/'Work Orders May 2026.xlsx').write_bytes(tma_xlsx(5,2))
    report=discover_history(LocalFolderStorage(tmp_path),'2026-05','2026-05','sharepoint_year_month').months[0].reports[2]
    assert report.status=='ambiguous' and len(report.sources)==2
    selected=discover(Workspace(tmp_path,tmp_path.parent/'candidates',tmp_path.parent/'approved'),'2026-05',folder_layout='sharepoint_year_month')
    assert ReportType.TMA_WORK_ORDERS in selected.missing


def test_previous_month_filename_cannot_override_title_or_request_dates(tmp_path):
    engine=ProcessingCoordinator(tmp_path/'candidates')
    for period,source,expected in [('2026-04',raw(),'work_order_title_period_mismatch'),
                                    ('2026-05',raw('may_wrong_dates.xls'),'output_period_mismatch')]:
        result=engine.preview(ProcessingRequest('tma_work_orders',period,source_name=NAME,raw_bytes=source))
        assert result.status=='failure' and result.code==expected
    assert not engine.store.root.exists()


def test_bundled_legacy_sample_is_only_the_synthetic_fixture():
    bundled=Path(__file__).resolve().parents[1]/'src/equipment_data_manager/resources/samples/tma_legacy_sample.xls'
    assert bundled.read_bytes()==raw()
