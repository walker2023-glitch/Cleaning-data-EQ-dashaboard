"""Generate invented BIFF8 timestamp/header/body files; no departmental content.

uv run --with xlwt==1.3.0 python tests/fixtures/synthetic/tma_timestamped/generate.py
Fixtures only: xlwt is not an application dependency. No source workbook is read.
"""
from datetime import datetime
from pathlib import Path
from io import BytesIO
import xlwt

SHEET='CU_Repair_WO_History_-_Previous'
TITLE='CU Repair WO History - Previous Month (HI-042b)'
HEADERS=['Work Order #','Request Date','Requestor','Request']


def workbook(*, count=3, period='2026-05', generation=datetime(2026,6,1,7,30),
             timestamp='date', datemode=0, sheet=SHEET, title=TITLE, separator='',
             headings=None, footer=False, extra_column=False, wrong_date=False,
             invalid_date=False, blank_id=False, formatted_last_id=False, extra_sheet=False,
             extra_timestamp_cell=False, extra_title_cell=False, repeated=True):
    book=xlwt.Workbook();book.set_dates_1904(bool(datemode))
    page=book.add_sheet(sheet)
    if timestamp=='date':
        page.write(0,0,generation,xlwt.easyxf(num_format_str='MM/DD/YYYY HH:MM:SS'))
    elif timestamp=='number':
        page.write(0,0,46174.31306712963)  # Owner-reported timestamp, never private report data.
    elif timestamp=='text':
        page.write(0,0,'06/01/2026 7:30 AM')
    elif timestamp=='iso_text':
        page.write(0,0,'2026-06-01 07:30:00')
    elif timestamp=='negative':
        page.write(0,0,-1)
    elif timestamp=='huge':
        page.write(0,0,1e10)
    elif timestamp=='boolean':
        page.write(0,0,True)
    elif timestamp=='fictional_day':
        page.write(0,0,60.25)
    if extra_timestamp_cell:page.write(0,1,'Unexpected')
    page.write(1,0,title)
    if extra_title_cell:page.write(1,1,'Unexpected')
    if separator:page.write(2,0,separator)
    for col,name in enumerate(HEADERS if headings is None else headings):page.write(3,col,name)
    year,month=map(int,period.split('-'))
    for ordinal in range(count):
        row=4+ordinal
        identifier='000123' if repeated or ordinal==0 else f'WO-{ordinal:06d}'
        if blank_id and ordinal==1:identifier=''
        if formatted_last_id and ordinal==count-1:
            page.write(row,0,439,xlwt.easyxf(num_format_str='000000'))
        else:page.write(row,0,identifier)
        value = datetime(year,month,1+ordinal%28,5+ordinal%12,1+ordinal%50)
        if wrong_date and ordinal==0:value=datetime(2026,4,30,23,59)
        if invalid_date and ordinal==1:page.write(row,1,'Invalid synthetic date')
        else:page.write(row,1,value,xlwt.easyxf(num_format_str='MM/DD/YYYY HH:MM'))
        page.write(row,2,'Synthetic Requestor')
        page.write(row,3,'Synthetic task, "only"\nSecond line')
        if extra_column:page.write(row,4,'Unexpected')
    if footer:page.write(4+count,0,f'Total: {count} records')
    if extra_sheet:book.add_sheet('Unexpected')
    stream=BytesIO();book.save(stream)
    return stream.getvalue()


if __name__=='__main__':
    root=Path(__file__).parent
    cases={
        'may_81.xls':dict(count=81,timestamp='number',formatted_last_id=True),
        'may_small.xls':dict(formatted_last_id=True),
        'may_text_timestamp.xls':dict(timestamp='text'),
        'may_missing_timestamp.xls':dict(timestamp='missing'),
        'december_rollover.xls':dict(period='2025-12',generation=datetime(2026,1,1,8,0)),
        'june.xls':dict(period='2026-06',generation=datetime(2026,7,1,9,30)),
        'may_1904.xls':dict(datemode=1),
        'may_wrong_title.xls':dict(title='Unconfirmed Previous Month'),
        'may_wrong_sheet.xls':dict(sheet='Unconfirmed'),
        'may_separator.xls':dict(separator='Unexpected'),
        'may_headers.xls':dict(headings=['Work Order #','Request Date','Requestor','Unconfirmed']),
        'may_missing_header.xls':dict(headings=HEADERS[:-1]),
        'may_footer.xls':dict(footer=True),
        'may_extra_column.xls':dict(extra_column=True),
        'may_wrong_date.xls':dict(wrong_date=True),
        'may_invalid_date.xls':dict(invalid_date=True),
        'may_blank_id.xls':dict(blank_id=True),
        'may_extra_sheet.xls':dict(extra_sheet=True),
        'may_extra_timestamp_cell.xls':dict(extra_timestamp_cell=True),
        'may_extra_title_cell.xls':dict(extra_title_cell=True),
        'may_negative_timestamp.xls':dict(timestamp='negative'),
        'may_huge_timestamp.xls':dict(timestamp='huge'),
        'may_boolean_timestamp.xls':dict(timestamp='boolean'),
        'may_iso_text_timestamp.xls':dict(timestamp='iso_text'),
        'may_fictional_timestamp.xls':dict(timestamp='fictional_day'),
    }
    for name,options in cases.items():(root/name).write_bytes(workbook(**options))
