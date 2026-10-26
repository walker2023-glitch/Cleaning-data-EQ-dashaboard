"""Create January/February SYNTHETIC reports through the real engine.

Run from the repository: uv run python examples/create_powerbi_pilot.py --output data/powerbi-pilot
Refuses existing output. Does not read departmental reports or connect to Power BI.
"""
import argparse
import csv
from io import BytesIO, StringIO
from pathlib import Path

from openpyxl import Workbook

from equipment_data_manager.monthly import Workspace, export_review_packet
from equipment_data_manager.powerbi_pilot import assemble, baseline_template, reconcile, write_report
from equipment_data_manager.processing.models import ProcessingRequest, ReportType
from equipment_data_manager.processing.powerbi import powerbi_coordinator


def csv_bytes(headers, rows):
    stream = StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')


def create_demo(root: Path, *, financial_v2=False):
    root.mkdir(parents=True, exist_ok=False)
    workspace = Workspace(root / 'raw', root / 'candidates', root / 'reserved-approved')
    if financial_v2:
        from equipment_data_manager.processing.repair_financial import powerbi_coordinator as financial_coordinator
        engine = financial_coordinator(workspace.candidate_folder)
    else:
        engine = powerbi_coordinator(workspace.candidate_folder)
    packets = []
    for month in (1, 2):
        period = f'2026-{month:02d}'
        # Intentionally distinct report-level and calculated parts/labor values.
        # Repeated summaries count ONCE; they are not transaction amounts.
        repairs = csv_bytes(['AccountName2', 'PersonnelId5', 'PersonnelId1', 'PersonnelId3', 'PersonnelId4',
            'CompletedDate1', 'Textbox38', 'Description', 'Details', 'Textbox16',
            'Textbox10', 'Textbox11', 'Textbox12', 'Textbox13'], [
            ['Synthetic Account', 'Equip. Name: Synthetic Machine', f'Equipment Id: 00043{i}',
             'Service Vendor: Synthetic Vendor', 'Location: Synthetic Room', f'{month}/15/2026',
             '' if month == 2 and i == 9 else '$10.00', 'Synthetic repair', '2 hours',
             ('' if month == 2 and i == 9 else '$10.00') if financial_v2 else '$35.00',
             'Total Labor: $15.00' if financial_v2 else 'Total Labor: $40.00',
             'Total Parts: $5.00' if financial_v2 else 'Total Parts: $30.00',
             'Total Cost: $20.00' if financial_v2 else 'Total Cost: $70.00', '# of Repairs: 2']
            for i in (8, 9)])
        services = csv_bytes(['AccountName2', 'EquipmentId1', 'EquipmentName1', 'VendorName', 'ScheduledDate',
            'CompletedDate', 'Name', 'Description', 'Textbox21', 'Textbox56'], [
            ['Synthetic Account', f'00043{i}', 'Synthetic Machine', '', f'{month}/15/2026', f'{month}/16/2026',
             'Synthetic Room', 'Synthetic inspection - (PM)', 'Completed', 'Total Service Orders: 2']
            for i in (8, 9)])
        book = Workbook()
        sheet = book.active
        sheet.append([f'CU Repair WO History — {"January" if month == 1 else "February"} 2026'])
        sheet.append(['Work Order #', 'Request Date', 'Requestor', 'Request', 'Assigned To'])
        for i in (8, 9):
            sheet.append([f'00012{i}', f'{month:02d}/15/2026', 'Synthetic Requestor', 'Synthetic request', ''])
        sheet.append(['Total: 2 records'])
        buffer = BytesIO()
        book.save(buffer)
        book.close()
        for kind, raw, extension in ((ReportType.REPAIRS, repairs, 'csv'),
                (ReportType.SERVICE_ORDERS, services, 'csv'), (ReportType.TMA_WORK_ORDERS, buffer.getvalue(), 'xlsx')):
            path = workspace.raw_folder / period / kind.value / f'synthetic.{extension}'
            path.parent.mkdir(parents=True)
            path.write_bytes(raw)
            result = engine.process(ProcessingRequest(kind, period, input_path=path))
            if result.status != 'success':
                raise RuntimeError(f'Synthetic {kind} {period}: {result.code}')
        packets.append(export_review_packet(workspace, engine, period))
    snapshot = assemble(packets, ['2026-01', '2026-02'], root / 'pilot')
    baseline = root / 'synthetic-baselines.csv'
    baseline_template(snapshot, baseline)
    with baseline.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        names, rows = reader.fieldnames, list(reader)
    for row in rows:
        metric = row['metric']
        if metric in ('rows', 'repair_count'):
            row.update(source_total='2', powerbi_total='2', comparable='true')
        elif metric == 'reported_total_cost':
            row.update(source_total='20', powerbi_total='20', comparable='true')
        elif metric == 'hours':
            row['powerbi_total'] = '4'
            row['comparable'] = 'true'
        elif metric in ('parts_cost', 'labor_cost', 'estimated_total'):
            row['source_total'] = {'parts_cost': '30', 'labor_cost': '40', 'estimated_total': '70'}[metric]
            row['powerbi_total'] = row['source_total']
        row['powerbi_measure'] = f'SYNTHETIC {metric} (not a dashboard export)'
        row['evidence'] = 'Invented demonstration only; report summaries counted once; no actual Power BI baseline'
    with baseline.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)
    write_report(reconcile(snapshot, baseline), root / 'reconciliation.csv')
    return snapshot


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repair-financial-v2', action='store_true', help='Separate reported repair totals from estimates/legacy; include monthly financial summaries')
    args = parser.parse_args()
    snapshot = create_demo(args.output, financial_v2=args.repair_financial_v2)
    print(f'SYNTHETIC candidate snapshot: {snapshot}')
    print('Comparison report uses INVENTED baselines, not existing dashboard measures. No approval or publication.')
