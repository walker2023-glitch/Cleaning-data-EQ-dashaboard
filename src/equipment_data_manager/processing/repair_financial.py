"""Repair schema v2: source totals, estimates and legacy values stay separate.

The supplied January CSV has equal Textbox38/Textbox16 cells. Differing grouped
values are unverified until the formatted workbook is supplied; never allocate.
"""
import csv
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import StringIO
import os
from pathlib import Path
import re

from equipment_data_manager.processing.interfaces import ColumnSchema, ReconciliationMetric
from equipment_data_manager.processing.manifest import LocalOutputStore
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.processing.powerbi import COMMON, PowerBiCleaner, schema as legacy_schema
from equipment_data_manager.processing.repair_layouts import SummaryRepairsLayout

EXPORT_VERSION = 'powerbi-v2'
BUSINESS = ('LegacyRowNumber', 'CompletedDate', 'EquipmentName', 'EquipmentId', 'Location', 'ServiceVendor',
    'RepairCount', 'RepairPersonHours', 'ReportedTotalCost', 'ReportedTotalCostStatus', 'EstimatedLaborCost',
    'LegacyPartsCost', 'LegacyLaborCost', 'LegacyEstimatedTotalCost', 'RawTextbox38', 'RawTextbox16',
    'Description', 'Details', 'AccountName', 'RawEquipmentId', 'FinancialSummarySHA256')
SUMMARY_COLUMNS = ('ReportMonth', 'ReportedLaborCost', 'ReportedPartsCost', 'ReportedTotalCost',
    'ReportedRepairCount', 'SourceRecordCount', 'RetainedRepairCount', 'KnownRepairTotalCost',
    'UnavailableRepairCostCount', 'RepairTotalDifference', 'SummaryComponentsDifference', 'ReconciliationStatus',
    'SourceSystem', 'ReportType', 'SourceFileName', 'SourceFileSHA256', 'LegacyCandidateSHA256',
    'CleanerVersion', 'ExportVersion', 'SchemaVersion', 'ValidationStatus')
DECIMALS = {'ReportedTotalCost', 'EstimatedLaborCost', 'LegacyPartsCost', 'LegacyLaborCost',
            'LegacyEstimatedTotalCost', 'RepairPersonHours'}


def schema():
    old = {c.name: c.data_type for c in legacy_schema(ReportType.REPAIRS)}
    return tuple(ColumnSchema(name, 'decimal' if name in DECIMALS else old.get(name, 'text'))
                 for name in BUSINESS + COMMON)


def encode(rows, columns):
    stream = StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def money(value):
    """Strict observed source dollars; blank/malformed/nonfinite never become zero."""
    if not re.fullmatch(r'-?\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?', value.strip()):
        return None
    try:
        result = Decimal(value.strip().replace('$', '').replace(',', ''))
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def summary_name(period):
    return f'CompuClean_RepairFinancialSummary_{period}.csv'


class RepairFinancialCleaner:
    def __init__(self, base):
        self.base = base
        self.version = f'{EXPORT_VERSION}:{base.version}'

    def clean(self, raw_bytes, *, source_name, period):
        # Existing cleaner/writer and trace remain the authority for exclusions/dates/hours.
        original = PowerBiCleaner(ReportType.REPAIRS, self.base).clean(
            raw_bytes, source_name=source_name, period=period)
        raw = list(csv.DictReader(StringIO(raw_bytes.decode('utf-8-sig'), newline='')))
        confirmed_layout = set(raw[0]) == SummaryRepairsLayout.HEADERS
        old_rows = list(csv.DictReader(StringIO(original.output_bytes.decode(), newline='')))
        rows, unavailable = [], 0
        for old in old_rows:
            source = raw[int(old['SourceRecordNumber']) - 1]
            first, second = money(source.get('Textbox38', '')), money(source.get('Textbox16', ''))
            status = ('layout_unverified' if not confirmed_layout else
                      'missing_or_malformed' if first is None or second is None else
                      'field_relationship_unverified' if first != second else 'source_fields_agree')
            reported = first if status == 'source_fields_agree' else None
            unavailable += reported is None
            row = {name: old[name] for name in ('LegacyRowNumber', 'CompletedDate', 'EquipmentName', 'EquipmentId',
                'Location', 'ServiceVendor', 'RepairCount', 'RepairPersonHours', 'LegacyPartsCost',
                'LegacyEstimatedTotalCost', 'RawTextbox16', 'Description', 'Details', 'AccountName', 'RawEquipmentId')}
            row.update(ReportedTotalCost='' if reported is None else str(reported), ReportedTotalCostStatus=status,
                EstimatedLaborCost=old['LaborCost'], LegacyLaborCost=old['LaborCost'], RawTextbox38=old['RawPartsCost'])
            row.update({name: old[name] for name in COMMON})
            row.update(ExportVersion=EXPORT_VERSION, SchemaVersion='2')
            rows.append(row)
        metrics = {m.name: m.value for m in original.reconciliation_metrics}
        totals = {name: metrics.get('Legacy Source reported ' + label) for name, label in
                  [('ReportedLaborCost', 'labor'), ('ReportedPartsCost', 'parts'), ('ReportedTotalCost', 'cost')]}
        count = metrics.get('Legacy Source repair records')
        known = sum((Decimal(r['ReportedTotalCost']) for r in rows if r['ReportedTotalCost']), Decimal(0))
        complete = unavailable == 0 and len(rows) == len(raw)
        difference = known - totals['ReportedTotalCost'] if complete and totals['ReportedTotalCost'] is not None else None
        components = (totals['ReportedLaborCost'] + totals['ReportedPartsCost'] - totals['ReportedTotalCost']
                      if all(v is not None for v in totals.values()) else None)
        state = ('source_summary_unavailable' if count is None else
                 'incomplete_repair_costs_or_excluded_records' if not complete else
                 'difference' if difference != 0 or components != 0 else 'arithmetic_match')
        provenance = {name: rows[0][name] for name in ('ReportMonth', 'SourceSystem', 'SourceFileName',
            'SourceFileSHA256', 'LegacyCandidateSHA256', 'CleanerVersion', 'ExportVersion', 'SchemaVersion', 'ValidationStatus')}
        summary = dict(provenance, ReportType='repair_financial_summary',
            **{k: '' if v is None else str(v) for k, v in totals.items()},
            ReportedRepairCount='' if count is None else str(count), SourceRecordCount=len(raw),
            RetainedRepairCount=len(rows), KnownRepairTotalCost=str(known) if unavailable < len(rows) else '',
            UnavailableRepairCostCount=unavailable, RepairTotalDifference='' if difference is None else str(difference),
            SummaryComponentsDifference='' if components is None else str(components), ReconciliationStatus=state)
        summary_bytes = encode([summary], SUMMARY_COLUMNS)
        for row in rows:
            row['FinancialSummarySHA256'] = sha256(summary_bytes).hexdigest()
        notes = tuple(n for n in original.warnings if not n.startswith('normalized_financial_values_unavailable:'))
        notes += ('repair_financial_schema_v2', f'repair_reported_cost_reconciliation:{state}')
        if unavailable:
            notes += (f'repair_reported_cost_unavailable:{unavailable}',)
        extra = (ReconciliationMetric('Known reported repair total', known, 'source_dollars'),)
        return replace(original, output_bytes=encode(rows, BUSINESS + COMMON), schema=schema(),
            cleaner_version=self.version, warnings=notes, reconciliation_metrics=original.reconciliation_metrics + extra,
            supplemental_outputs=((summary_name(period), summary_bytes),))


def read_summary(raw):
    from equipment_data_manager.powerquery_contract import read_table
    return read_table(raw, ReportType.REPAIRS, allow_candidates=True, financial_summary=True)[0]


def verify_summary(artifact):
    """Digest is bound into the hashed main artifact; no new SQLite schema needed."""
    if not artifact.cleaner_version.startswith(EXPORT_VERSION + ':'):
        return None
    rows = list(csv.DictReader(StringIO(artifact.output_path.read_text(encoding='utf-8'), newline='')))
    expected = {r.get('FinancialSummarySHA256') for r in rows}
    if len(expected) != 1 or None in expected:
        raise ProcessingError('financial_summary_reference_rejected')
    period = rows[0]['ReportMonth']
    path = artifact.output_path.parent / summary_name(period)
    if path.is_symlink() or not path.resolve().is_relative_to(artifact.output_path.parent.resolve()):
        raise ProcessingError('unsafe_financial_summary')
    try:
        raw = path.read_bytes()
    except OSError:
        raise ProcessingError('financial_summary_missing_or_unreadable') from None
    if sha256(raw).hexdigest() != next(iter(expected)):
        raise ProcessingError('financial_summary_hash_mismatch')
    summary = read_summary(raw)
    if summary['ReportMonth'] != period or summary['SourceFileSHA256'] != rows[0]['SourceFileSHA256']:
        raise ProcessingError('financial_summary_provenance_mismatch')
    return path, raw


class FinancialOutputStore(LocalOutputStore):
    def current(self, *args):
        artifact, warnings = super().current(*args)
        if artifact:
            verify_summary(artifact)
        return artifact, warnings

    def write_revision(self, report_type, period, source_hash, cleaned):
        artifact = super().write_revision(report_type, period, source_hash, cleaned)
        for name, raw in cleaned.supplemental_outputs:
            if name != summary_name(period) or report_type != ReportType.REPAIRS:
                raise ProcessingError('invalid_financial_summary_artifact')
            target = artifact.output_path.parent / name
            staged = target.with_suffix('.csv.part')
            try:
                with staged.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(staged, target)
            finally:
                staged.unlink(missing_ok=True)
        verify_summary(artifact)
        return artifact


def powerbi_coordinator(output_root):
    from equipment_data_manager.processing.powerbi import powerbi_coordinator as v1
    coordinator = v1(output_root)
    coordinator.cleaners[ReportType.REPAIRS] = RepairFinancialCleaner(coordinator.cleaners[ReportType.REPAIRS].base)
    coordinator.store = FinancialOutputStore(coordinator.store.root)
    return coordinator
