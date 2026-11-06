"""Invented BIFF8 fixtures. No actual report; no runtime Excel-writing dependency.

Rebuild explicitly: uv run --with xlwt==1.3.0 --with olefile==0.47 python
 tests/fixtures/synthetic/legacy_tma/generate.py
xlwt/olefile are fixture generators only, neither packaged nor runtime dependencies.
"""
from pathlib import Path
from io import BytesIO
import struct
from datetime import datetime
import xlwt
import olefile

ROOT = Path(__file__).parent


def create(name, *, assigned=False, wrong_month=False, numeric=False, extra_sheet=False, missing_header=False, native_dates=False, ambiguous_id=False):
    book = xlwt.Workbook()
    sheet = book.add_sheet('Synthetic')
    sheet.write(0,0,'CU Repair WO History — May 2026')
    columns = ['Work Order #','Request Date','Requestor','Request'] + (['Assigned To'] if assigned else [])
    if missing_header:
        columns[2] = 'Unconfirmed field'
    for col,value in enumerate(columns):
        sheet.write(1,col,value)
    for row,identifier in enumerate(['000123','WO-A0007'],2):
        if ambiguous_id and row == 2:
            sheet.write(row,0,123,xlwt.easyxf(num_format_str='000-000'))
        elif numeric and row == 2:
            sheet.write(row,0,123,xlwt.easyxf(num_format_str='000000'))
        else:
            sheet.write(row,0,identifier)
        if native_dates:
            sheet.write(row,1,datetime(2026,5,15),xlwt.easyxf(num_format_str='MM/DD/YYYY'))
        else:
            sheet.write(row,1,'04/15/2026' if wrong_month else '05/15/2026')
        sheet.write(row,2,'Synthetic Requestor')
        sheet.write(row,3,'Synthetic inspection, "only"\nSecond line')
        if assigned:
            sheet.write(row,4,'' if row == 2 else 'Synthetic Technician')
    sheet.write(4,0,'Total: 2 records')
    if extra_sheet:
        book.add_sheet('Unexpected')
    output = BytesIO();book.save(output)
    (ROOT / name).write_bytes(output.getvalue())


if __name__ == '__main__':
    create('may_four_columns.xls')
    create('may_five_columns.xls',assigned=True)
    create('may_wrong_dates.xls',wrong_month=True)
    create('may_formatted_identifier.xls',numeric=True)
    create('may_native_dates.xls',native_dates=True)
    create('may_ambiguous_identifier.xls',ambiguous_id=True)
    create('may_multiple_sheets.xls',extra_sheet=True)
    create('may_missing_required_header.xls',missing_header=True)
    # Synthetic BIFF FILEPASS marker: parser must reject before any cell processing.
    target = ROOT / 'encrypted_marker.xls'
    target.write_bytes((ROOT / 'may_four_columns.xls').read_bytes())
    with olefile.OleFileIO(target,write_mode=True) as book:
        stream = book.openstream('Workbook').read()
        end_bof = 4 + struct.unpack('<H',stream[2:4])[0]
        marker = struct.pack('<HHHH',0x2f,4,0,0)
        changed = (stream[:end_bof]+marker+stream[end_bof:])[:len(stream)]
        book.write_stream('Workbook',changed)
