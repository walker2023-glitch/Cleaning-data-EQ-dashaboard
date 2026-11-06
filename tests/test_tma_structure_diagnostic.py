"""Formatting-only extents, strict structural predicates and safe diagnostics."""
import csv
from hashlib import sha256
from io import BytesIO, StringIO
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import xlrd

from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest
from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.work_orders import (
    TmaXlsxCleaner, read_workbook, timestamped_body, TIMESTAMPED_SHEET,
)
from equipment_data_manager.tma_structure_diagnostic import inspect_structure, main, runtime_info
from equipment_data_manager.ui.messages import error_message

ROOT=Path(__file__).parent/'fixtures/synthetic/tma_timestamped'


@pytest.mark.parametrize('fixture', ['native85.xls','formatting_column.xls','formatting_rows.xls','formatting_edges.xls'])
def test_owner_verified_default_dimensions_and_native_date_with_style_only_edges(fixture):
    data=(ROOT/fixture).read_bytes()
    with xlrd.open_workbook(file_contents=data) as book:
        sheet=book.sheet_by_index(0)
        assert book.biff_version==80 and book.nsheets==1
        assert sheet.nrows==85 and sheet.ncols==4
        assert sheet.cell_type(0,0)==3 and sheet.cell_value(0,0)==46174.31306712963
        assert all(sheet.cell_type(0,col)==0 for col in (1,2,3))
    raw,_,meta=read_workbook(data,'.xls',include_metadata=True)
    assert raw.shape==(85,4) and meta['physical_rows']==85 and meta['physical_columns']==4
    result=TmaXlsxCleaner().clean(data,source_name='synthetic.xls',period='2026-05')
    assert result.input_rows==result.output_rows==81
    rows=list(csv.reader(StringIO(result.output_bytes.decode())))[2:]
    assert len(rows)==81 and rows[-1][0]=='000439'
    assert all(row[-1]=='' for row in rows)
    assert ('tma_formatting_only_edges_ignored' in result.warnings)==(fixture!='native85.xls')


def test_reproduces_prior_exact_rejection_predicate_without_private_workbook():
    data=(ROOT/'formatting_column.xls').read_bytes()
    with pd.ExcelFile(BytesIO(data),engine='xlrd',engine_kwargs={'formatting_info':True,'on_demand':True}) as book:
        sheet=book.book.sheet_by_index(0)
        before=pd.read_excel(book,header=None,dtype=str,keep_default_na=False)
        assert sheet.nrows==85 and sheet.ncols==5 and before.shape==(85,5)
        # These were precisely the old compound guard's two failing conditions.
        assert sheet.ncols!=4 and before.shape[1]!=4
    report=inspect_structure(data,extension='.xls',period='2026-05')
    assert report['formatting_dimensions']==[85,5]
    assert report['content_dimensions']==report['parsed_dimensions']==[85,4]
    assert report['preview_status']=='success' and report['retained_records']==81
    assert all(condition['passed'] for condition in report['structure_checks'])


@pytest.mark.parametrize('fixture', ['may_extra_column.xls','extra_whitespace.xls','extra_zero.xls','extra_boolean.xls'])
def test_fifth_data_column_still_rejected_including_whitespace_zero_false(fixture,tmp_path):
    data=(ROOT/fixture).read_bytes()
    result=ProcessingCoordinator(tmp_path/'out').preview(ProcessingRequest('tma_work_orders','2026-05',raw_bytes=data,source_name='synthetic.xls'))
    assert result.status=='failure' and result.code=='tma_timestamped_columns_mismatch'
    assert not (tmp_path/'out').exists()
    report=inspect_structure(data,extension='.xls',period='2026-05')
    failed=[check['failure_code'] for check in report['structure_checks'] if not check['passed']]
    assert failed==['tma_timestamped_columns_mismatch','tma_timestamped_parsed_columns_mismatch']


@pytest.mark.parametrize('change,code', [
    ('extension','tma_timestamped_extension_mismatch'),('sheet','tma_timestamped_sheet_mismatch'),
    ('content_columns','tma_timestamped_columns_mismatch'),('parsed_columns','tma_timestamped_parsed_columns_mismatch'),
    ('minimum_rows','tma_timestamped_insufficient_rows'),('row_alignment','tma_timestamped_row_count_mismatch')])
def test_each_original_structural_guard_has_an_exact_safe_failure_code(change,code):
    raw,_,meta=read_workbook((ROOT/'native85.xls').read_bytes(),'.xls',include_metadata=True)
    extension='.xls'
    if change=='extension':extension='.xlsx'
    if change=='sheet':meta['sheet_name']='SYNTHETIC_PRIVATE_WORKSHEET'
    if change=='content_columns':meta['physical_columns']=5
    if change=='parsed_columns':raw['SYNTHETIC_PRIVATE_HEADER']='private'
    if change=='minimum_rows':raw=raw.iloc[:4];meta['physical_rows']=4
    if change=='row_alignment':meta['physical_rows']=86
    with pytest.raises(ProcessingError,match='^'+code+'$') as caught:
        timestamped_body(raw,meta,extension,'2026-05')
    assert 'PRIVATE' not in str(caught.value)
    assert error_message(code)!='This report could not be processed safely. Preview again or contact your maintainer.'


@pytest.mark.parametrize('fixture,code,flag', [
    ('may_wrong_sheet.xls','tma_timestamped_sheet_mismatch',None),
    ('may_text_timestamp.xls','tma_generation_timestamp_invalid','numeric_generation_timestamp_valid'),
    ('may_wrong_title.xls','tma_timestamped_title_invalid','exact_title_matches'),
    ('may_separator.xls','tma_timestamped_separator_invalid','separator_is_blank'),
    ('may_headers.xls','tma_timestamped_headers_invalid','exact_headers_match'),
    ('may_wrong_date.xls','output_period_mismatch',None)])
def test_privacy_safe_report_identifies_failed_gate_without_cell_contents(fixture,code,flag):
    report=inspect_structure((ROOT/fixture).read_bytes(),extension='.xls',period='2026-05')
    encoded=json.dumps(report)
    assert report['preview_status']=='failure' and report['failure_code']==code
    if flag:assert report['checks'][flag] is False
    assert all(value not in encoded for value in ('Synthetic Requestor','Synthetic task','Unconfirmed','05/15/2026','46174.313067'))
    assert report['candidate_files_written'] is report['source_modified'] is False


def test_cli_is_read_only_does_not_create_candidate_state_or_disclose_source_path(tmp_path,capsys):
    source=tmp_path/'PRIVATE-SOURCE.xls';data=(ROOT/'formatting_edges.xls').read_bytes();source.write_bytes(data)
    before=sha256(data).hexdigest()
    assert main(['--input',str(source),'--period','2026-05'])==0
    text=capsys.readouterr().out;report=json.loads(text)
    assert report['input_records']==report['retained_records']==81
    assert str(source) not in text and source.name not in text
    assert list(tmp_path.iterdir())==[source] and sha256(source.read_bytes()).hexdigest()==before
    assert main(['--input',str(source),'--period','2026-06'])==1
    assert json.loads(capsys.readouterr().out)['failure_code']=='tma_generation_period_mismatch'


def test_runtime_identifies_actual_module_instead_of_claiming_git_commit(capsys):
    assert main(['--runtime'])==0
    report=json.loads(capsys.readouterr().out)
    assert report['diagnostic_build']=='tma-structure-v1-content-bounds'
    assert Path(report['module_path']).name=='work_orders.py' and report['xlrd_version']=='2.0.2'
    assert report['module_sha256']==sha256(Path(report['module_path']).read_bytes()).hexdigest()
    assert 'v3.1:' in report['cleaner_version'] and 'git_commit' not in report
