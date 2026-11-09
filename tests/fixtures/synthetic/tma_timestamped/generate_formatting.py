"""Invented 85x4 BIFF8 data + formatting-only edge regression fixtures.

uv run --with xlwt==1.3.0 python tests/fixtures/synthetic/tma_timestamped/generate_formatting.py
No original report is read. Generator-only xlwt is not packaged.
"""
from datetime import datetime
from pathlib import Path
from io import BytesIO
import xlwt


def workbook(*, style_row=None, style_column=None, extra_value=None, count=81, month=5):
    book=xlwt.Workbook();sheet=book.add_sheet('CU_Repair_WO_History_-_Previous')
    if month==5:
        sheet.write(0,0,46174.31306712963,xlwt.easyxf(num_format_str='MM/DD/YYYY HH:MM:SS'))
    else:
        sheet.write(0,0,datetime(2026,7,1,9,30),xlwt.easyxf(num_format_str='MM/DD/YYYY HH:MM:SS'))
    sheet.write(1,0,'CU Repair WO History - Previous Month (HI-042b)')
    for col,value in enumerate(['Work Order #','Request Date','Requestor','Request']):sheet.write(3,col,value)
    for row in range(4,4+count):
        sheet.write(row,0,439,xlwt.easyxf(num_format_str='000000'))
        sheet.write(row,1,datetime(2026,month,1+row%28,8,0),xlwt.easyxf(num_format_str='MM/DD/YYYY HH:MM'))
        sheet.write(row,2,'Synthetic Requestor');sheet.write(row,3,'Synthetic request')
    style=xlwt.easyxf('pattern: pattern solid, fore_colour yellow;')
    if style_row is not None:sheet.write(style_row,0,None,style)
    if style_column is not None:sheet.write(3,style_column,None,style)
    if extra_value is not None:sheet.write(4,4,extra_value)
    out=BytesIO();book.save(out)
    return out.getvalue()


if __name__=='__main__':
    root=Path(__file__).parent
    for name,kwargs in {
        'native85.xls':{},
        'formatting_column.xls':dict(style_column=4),
        'formatting_rows.xls':dict(style_row=100),
        'formatting_edges.xls':dict(style_column=10,style_row=100),
        'formatting_june.xls':dict(style_column=4,style_row=12,count=3,month=6),
        'extra_whitespace.xls':dict(extra_value=' '),
        'extra_zero.xls':dict(extra_value=0),
        'extra_boolean.xls':dict(extra_value=False),
    }.items():(root/name).write_bytes(workbook(**kwargs))
