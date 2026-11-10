"""Create invented January–June raw reports in BOTH supported layouts.

New destination only. No candidates, database, settings or network operations.
Counts and dollars are invented; never compare them with departmental totals.
"""
import argparse
import calendar
import csv
from importlib.resources import files
from io import BytesIO, StringIO
from pathlib import Path
from openpyxl import Workbook


def csv_data(headers, rows):
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')


def create_demo(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for month in range(1, 7):
        repair = csv_data(['AccountName2','PersonnelId5','PersonnelId1','PersonnelId3','PersonnelId4',
            'CompletedDate1','Textbox38','Description','Details','Textbox16','Textbox10','Textbox11','Textbox12','Textbox13'],
            [['Synthetic Account','Equip. Name: Synthetic Machine','Equipment Id: 000439',
              'Service Vendor: Synthetic Vendor','Location: Synthetic Room',f'{month}/15/2026',
              '$10.00','Synthetic repair','2 hours','$10.00','Total Labor: $5.00',
              'Total Parts: $25.00','Total Cost: $30.00','# of Repairs: 3']] * 3)
        service = csv_data(['AccountName2','EquipmentId1','EquipmentName1','VendorName','ScheduledDate',
            'CompletedDate','Name','Description','Textbox21','Textbox56'],
            [['Synthetic Account','000439','Synthetic Machine','',f'{month}/15/2026',f'{month}/16/2026',
              'Synthetic Room','Synthetic inspection - (PM)','Completed','Total Service Orders: 2']] * 2)
        if month in (5, 6):
            sample = 'tma_legacy_sample.xls' if month == 5 else 'tma_timestamped_sample.xls'
            tma = files('equipment_data_manager').joinpath('resources/samples', sample).read_bytes()
            name = f'CU_Repair_WO_History_-_Previous_Month_(HI-042b){month}12345.xls'
        else:
            book = Workbook()
            sheet = book.active
            for row in [[f'CU Repair WO History — {calendar.month_name[month]} 2026','','','',''],
                ['Work Order #','Request Date','Requestor','Request','Assigned To'],
                *[['000123',f'{month:02d}/15/2026','Synthetic Requestor','Synthetic request','']]*2,
                ['Total: 2 records','','','','']]:
                sheet.append(row)
            stream = BytesIO(); book.save(stream); book.close()
            tma = stream.getvalue()
            name = f'Work Orders {calendar.month_name[month]} 2026.xlsx'
        for layout in ('standard','sharepoint'):
            folder = (output / layout / f'2026-{month:02d}' if layout == 'standard' else
                      output / layout / '2026' / f'2026-{month:02d} ({calendar.month_name[month]})')
            for kind, filename, raw in [('repairs','CompuClean Repair Report.csv',repair),
                ('service_orders','CompuClean Service Orders List.csv',service),('tma_work_orders',name,tma)]:
                target = folder / kind if layout == 'standard' else folder
                target.mkdir(parents=True, exist_ok=True)
                (target / filename).write_bytes(raw)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(create_demo(parser.parse_args().output))
