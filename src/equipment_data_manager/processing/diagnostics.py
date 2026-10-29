"""Local, in-memory explanations of existing CSV rules; never a new cleaner.

Record numbers are 1-based data records, not physical CSV lines (quoted fields
can span lines). No identity, description or financial cells are collected.
Raw date values are private: excluded from repr and default CLI summaries.
"""

from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

from equipment_data_manager.processing._legacy import repairs_row_clean as repairs
from equipment_data_manager.processing._legacy import service_row_clean as service

REPAIR_REASONS = ('accepted', 'missing_equipment_identity', 'invalid_completed_date', 'outside_reporting_period')
SERVICE_REASONS = ('accepted', 'missing_equipment_id', 'missing_scheduled_date', 'placeholder_description',
                   'no_parseable_service_date', 'outside_reporting_period', 'empty_cleaned_description',
                   'delete_duplicate_description')

@dataclass(frozen=True)
class DateObservation:
    column: str
    raw_value: str = field(repr=False)
    parsed_value: str | None


@dataclass(frozen=True)
class RecordDiagnostic:
    record: int
    reason: str
    retained_by_cleaner: bool
    dates: tuple[DateObservation, ...] = field(repr=False)


@dataclass(frozen=True)
class CleaningDiagnostics:
    report_type: str
    selected_period: str
    source_sha256: str
    cleaner_version: str
    records: tuple[RecordDiagnostic, ...] = field(repr=False)

    @property
    def retained_rows(self):
        return sum(row.retained_by_cleaner for row in self.records)

    def summary(self, *, include_date_values=False):
        counts = Counter(row.reason for row in self.records)
        months = Counter(f'{date.column}:{date.parsed_value[:7]}'
                         for row in self.records for date in row.dates if date.parsed_value)
        result = dict(report_type=self.report_type, selected_period=self.selected_period,
                      source_sha256=self.source_sha256, cleaner_version=self.cleaner_version,
                      input_rows=len(self.records), retained_by_cleaner=self.retained_rows,
                      reason_counts={reason: counts[reason] for reason in
                                     (REPAIR_REASONS if self.report_type == 'repairs' else SERVICE_REASONS)},
                      parsed_month_counts=dict(sorted(months.items())))
        if include_date_values:
            result['records'] = [dict(record=row.record, reason=row.reason, retained_by_cleaner=row.retained_by_cleaner,
                                      dates=[dict(column=date.column, raw=date.raw_value, parsed=date.parsed_value)
                                             for date in row.dates]) for row in self.records]
        return result


def observe_date(row, column, raw_record):
    value = row.get(column)
    parsed = pd.to_datetime(value, errors='coerce')
    return DateObservation(column, raw_record[column],
                           None if pd.isna(parsed) else parsed.strftime('%Y-%m-%d'))


def explain_rows(frame, *, raw_records, report_type, period, source_hash, cleaner_version):
    """Observe first exclusion in the original flat-layout rule order.

    Reuse original predicates; caller checks retained-count parity against the
    actual transform. This observer never filters or changes the source frame.
    """
    records = []
    for number, (_, row) in enumerate(frame.iterrows(), 1):
        raw_record = raw_records[number - 1]
        if report_type == 'repairs':
            dates = (observe_date(row, 'CompletedDate1', raw_record),)
            name = repairs.extract_label(row.get('PersonnelId5'), 'Equip. Name')
            identifier = repairs.extract_label(row.get('PersonnelId1'), 'Equipment Id')
            retained = False
            if not name and not identifier:
                reason = 'missing_equipment_identity'
            elif dates[0].parsed_value is None:
                reason = 'invalid_completed_date'
            else:
                retained = True
                reason = 'accepted' if dates[0].parsed_value[:7] == period else 'outside_reporting_period'
        else:
            # The wrapper only enables flat exports, including the Name alias.
            dates = (observe_date(row, 'ScheduledDate', raw_record), observe_date(row, 'CompletedDate', raw_record))
            identifier, schedule, description = row.get('EquipmentId1'), row.get('ScheduledDate'), row.get('Description')
            retained = False
            if pd.isna(identifier) or not str(identifier).strip():
                reason = 'missing_equipment_id'
            elif pd.isna(schedule) or not str(schedule).strip():
                reason = 'missing_scheduled_date'
            elif service._is_placeholder_description(description):
                reason = 'placeholder_description'
            elif not any(date.parsed_value for date in dates):
                reason = 'no_parseable_service_date'
            elif period not in {date.parsed_value[:7] for date in dates if date.parsed_value}:
                reason = 'outside_reporting_period'
            elif not service._clean_description(description):
                reason = 'empty_cleaned_description'
            elif service._clean_description(description).lower().startswith('delete duplicate'):
                reason = 'delete_duplicate_description'
            else:
                reason, retained = 'accepted', True
        records.append(RecordDiagnostic(number, reason, retained, dates))
    return CleaningDiagnostics(str(report_type), period, source_hash, cleaner_version, tuple(records))
