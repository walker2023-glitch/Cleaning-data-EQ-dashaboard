"""Read-only employee presentation. Local requests never imply remote approval."""
from decimal import Decimal
from equipment_data_manager.ui.messages import warning_message

REPORT_LABELS = {'repairs':'Repair Reports', 'service_orders':'Service Orders', 'tma_work_orders':'TMA Work Orders'}
FINANCIAL_LABELS = {
    'ReportedLaborCost':'Reported monthly labor', 'ReportedPartsCost':'Reported monthly parts',
    'ReportedTotalCost':'Reported monthly total', 'ReportedRepairCount':'Reported repairs',
    'KnownRepairTotalCost':'Known individual repair totals (may be partial)',
    'UnavailableRepairCostCount':'Repairs with missing or unresolved cost',
    'RepairTotalDifference':'Individual totals minus reported monthly total',
    'SummaryComponentsDifference':'Reported labor + parts minus reported total',
}
COUNT_FIELDS = {'ReportedRepairCount','UnavailableRepairCostCount'}


def request_label(status):
    return {'ReviewRequestedLocallyNotSent':'Review Requested Locally — not sent',
        'StaleSelectionChanged':'Stale — selected revisions or evidence changed',
        'StaleOrUnavailable':'Stale or unavailable — refresh source and candidate evidence'}.get(status,
        'Unrecognized local request status — not approval evidence')


def review_sections(payload):
    evidence, history = payload['captured']['evidence'], payload['history']
    counts, financial, issues, revisions, requests = [], [], [], [], []
    for kind, label in REPORT_LABELS.items():
        report = evidence['reports'].get(kind)
        if report is None:
            counts.append(f'{label}: MISSING — no current candidate for this month')
            continue
        counts.append(f"{label}: {report['retained_rows']} retained / {report['input_rows']} source rows")
        issues.append(label)
        issues += ['  '+warning_message(code) for code in report['warnings']] or []
        missing = report['missing_values']
        issues += [f'  Missing values — {column}: {count}' for column,count in missing.items()]
        if not report['warnings'] and not missing:
            issues.append('  No warnings or missing values recorded.')
        if 'financial_summary' in report:
            for key,value in report['financial_summary'].items():
                rendered = 'Not supplied / unresolved' if value is None else (
                    str(value) if key in COUNT_FIELDS else '$'+format(Decimal(value),',.2f'))
                financial.append(FINANCIAL_LABELS[key]+': '+rendered)
            state = report['financial_reconciliation']
            financial += ['','Arithmetic check: '+{
                'arithmetic_match':'Source-reported totals reconcile. This is not approval.',
                'difference':'A difference requires review. No values were corrected.',
                'source_summary_unavailable':'Source summary is unavailable.',
                'incomplete_repair_costs_or_excluded_records':'Incomplete costs or excluded records require review.'
            }.get(state,'Unrecognized reconciliation result — review technical details.')]
    if not financial:
        financial = ['Monthly repair financial summary is unavailable. Process repairs in Power BI schema v2.']
    for selected in evidence['selected']:
        revisions += [REPORT_LABELS[selected['report_type']], '  Revision: '+selected['revision'],
            '  Source SHA-256: '+selected['source_sha256'], '  Output SHA-256: '+selected['output_sha256'],
            '  Schema: '+selected['schema_version'], '  Cleaner: '+selected['cleaner_version'],
            '  Original-byte check: '+selected['source_check']]
        if 'summary_sha256' in selected:
            revisions.append('  Financial summary SHA-256: '+selected['summary_sha256'])
        revisions.append('')
    for record in history:
        requests += [request_label(record['status']), 'Requested (local clock, UTC): '+record['requested_at'],
            'Request ID: '+record['request_id'], 'Evidence note (unverified): '+record['evidence_note'], '']
    active = any(r['status']=='ReviewRequestedLocallyNotSent' for r in history)
    return dict(counts='\n'.join(counts), financial='\n'.join(financial), issues='\n'.join(issues) or 'No report evidence loaded.',
        revisions='\n'.join(revisions) or 'No current candidate revisions.',
        history='\n'.join(requests) or 'No local request recorded for this month. Nothing has been sent.',
        stages=(('Review Requested Locally','Recorded here — not sent' if active else 'Not recorded for current evidence'),
                ('Approval Pending','Not submitted to an approval service'),
                ('Approved','No authoritative approval evidence'),
                ('Published','Unavailable — publishing disabled')))
