"""Invented layout fixtures; counts come from the user's inventory, not real files.

Run with --output-dir data/monthly-samples to create local GUI samples. No source
report values or employee details are used. Matching expected totals here are
arithmetic regressions, not departmental approval.
"""

import argparse
import csv
from io import BytesIO, StringIO
from pathlib import Path

from openpyxl import Workbook

REPAIR_COUNTS = (29, 5, 17, 33, 55, 69)
SERVICE_COUNTS = (29, 5, 17, 35, 58, 70)
TMA_COUNTS = (38, 67, 69, 59)
REPAIR_HEADERS = ['AccountName2', 'PersonnelId5', 'PersonnelId1', 'PersonnelId3', 'PersonnelId4',
                  'CompletedDate1', 'Textbox38', 'Description', 'Details', 'Textbox16',
                  'Textbox10', 'Textbox11', 'Textbox12', 'Textbox13']
SERVICE_HEADERS = ['AccountName2', 'EquipmentId1', 'EquipmentName1', 'VendorName', 'ScheduledDate',
                   'CompletedDate', 'Name', 'Description', 'Textbox21', 'Textbox56']
TMA_HEADERS = ['Work Order #', 'Request Date', 'Requestor', 'Request', 'Assigned To']


def csv_bytes(headers, rows):
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')


def repair_csv(month=1, count=29):
    row = ['Synthetic Account', 'Equip. Name: Synthetic Machine', 'Equipment Id: 000439',
           'Service Vendor: Synthetic Vendor', 'Location: Synthetic Room', f'{month}/15/2026',
           '$10.00', 'Synthetic inspection, with quotes "only"\nSecond line', '2 hours', '$35.00',
           f'Total Labor: ${count * 25:,.2f}', f'Total Parts: ${count * 10:,.2f}',
           f'Total Cost: ${count * 35:,.2f}', f'# of Repairs: {count}']
    return csv_bytes(REPAIR_HEADERS, [row] * count)


def service_csv(month=1, count=29):
    row = ['Synthetic Account', '000439', 'Synthetic Machine', '', f'{month}/15/2026',
           f'{month}/16/2026', 'Synthetic Room', 'Synthetic inspection, "only"\nSecond line - (PM)',
           'Completed', f'Total Service Orders:     {count}']
    return csv_bytes(SERVICE_HEADERS, [row] * count)


def workbook_bytes(rows, *, second_sheet=False):
    book = Workbook()
    sheet = book.active
    for row in rows:
        sheet.append(row)
    if second_sheet:
        book.create_sheet('Unexpected')
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


def tma_rows(month=1, count=38):
    import calendar
    return [[f'CU Repair WO History — {calendar.month_name[month]} 2026', '', '', '', ''], list(TMA_HEADERS)] + [
        ['000123', f'{month:02d}/15/2026', 'Synthetic Requestor', 'Synthetic request, "only"\nSecond line', '']
        for _ in range(count)
    ] + [[f'Total: {count} records', '', '', '', '']]


def tma_xlsx(month=1, count=38):
    return workbook_bytes(tma_rows(month, count))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for kind, counts, factory, extension in (
        ('repairs', REPAIR_COUNTS, repair_csv, 'csv'),
        ('service_orders', SERVICE_COUNTS, service_csv, 'csv'),
        ('tma_work_orders', TMA_COUNTS, tma_xlsx, 'xlsx'),
    ):
        for month, count in enumerate(counts, 1):
            destination = args.output_dir / f'{kind}_2026-{month:02d}.{extension}'
            if destination.exists():
                raise SystemExit('Refusing to overwrite an existing sample')
            destination.write_bytes(factory(month, count))
