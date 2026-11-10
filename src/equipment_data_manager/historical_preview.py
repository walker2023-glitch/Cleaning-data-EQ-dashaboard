"""Read-only, sequential preview orchestration. Stores aggregates, never report cells.

Discovery identities are live session objects, not importable authorization. Cleaning,
financial arithmetic and month validation belong exclusively to existing adapters.
"""
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import csv
from io import StringIO
import json
import os
from pathlib import Path
from threading import Event

from equipment_data_manager.historical import is_temporary_filename, periods_between, verify_inventory_source
from equipment_data_manager.powerquery_contract import read_table
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest, ReportType
from equipment_data_manager.processing.repair_financial import powerbi_coordinator, read_summary
from equipment_data_manager.settings import candidate_location_error
from equipment_data_manager.storage.contracts import StorageError

LABELS = {
    'previewed': 'Previewed — no blocking issues',
    'warnings': 'Previewed — warnings require review',
    'missing': 'Missing reports', 'unsupported': 'Unsupported report format',
    'stale': 'Source changed — rediscovery required', 'failed': 'Preview failed',
    'not_previewed': 'Not previewed',
}


@dataclass(frozen=True)
class ReportPreview:
    month: str
    report_type: str
    source_filename: str = ''
    status: str = 'not_previewed'
    code: str = ''
    source_records: int | None = None
    retained_records: int | None = None
    excluded_records: int | None = None
    exclusions: tuple = ()
    missing_values: tuple = ()
    date_observations: tuple = ()
    financial: tuple = ()
    warnings: tuple = ()
    integrity: str = 'not_read'
    source_sha256: str = ''
    source_version: str = ''
    cleaner_version: str = ''
    candidate_status: str = 'not_assessed'
    failure_scope: str = ''

    def document(self):
        return asdict(self)


# Only this known ignored-extra notice is nonblocking. New/unknown issues fail closed.
IGNORED_EXTRA_NOTICE = 'historical_temporary_file_ignored'


@dataclass(frozen=True)
class InventoryNotice:
    month: str
    code: str
    count: int
    scope: str = 'ignored_extra_files'


@dataclass(frozen=True)
class BatchPreview:
    start: str
    end: str
    layout: str
    created_at: str
    reports: tuple[ReportPreview, ...]
    stopped: bool
    inventory_notices: tuple[InventoryNotice, ...] = ()

    def document(self):
        return dict(version=1, purpose='NonproductionDiagnosticPreview',
                    business_accuracy='not_independently_verified', sync_verified=False,
                    candidates_written=False, **asdict(self))


def month_status(reports):
    states = {r.status for r in reports}
    for state in ('stale', 'failed', 'unsupported', 'missing', 'not_previewed', 'warnings', 'previewed'):
        if state in states:
            return LABELS[state]
    return LABELS['not_previewed']


def _diagnostics(diagnostics):
    if diagnostics is None:
        return None, None, (), ()
    reasons = Counter(r.reason for r in diagnostics.records if not r.retained_by_cleaner)
    dates = Counter()
    for row in diagnostics.records:
        for date in row.dates:
            issue = ('missing' if not date.raw_value.strip() else 'invalid' if date.parsed_value is None
                     else 'outside_period' if date.parsed_value[:7] != diagnostics.selected_period else 'in_period')
            dates[f'{date.column}:{issue}'] += 1
    return len(diagnostics.records), diagnostics.retained_rows, tuple(sorted(reasons.items())), tuple(sorted(dates.items()))


def _summarize(result, period, kind, source, integrity):
    source_count, retained, exclusions, dates = _diagnostics(result.diagnostics)
    missing, financial = (), ()
    cleaned = result.cleaned
    if cleaned:
        source_count, retained = cleaned.input_rows, cleaned.output_rows
        rows = read_table(cleaned.output_bytes, kind, allow_candidates=True)
        important = {
            ReportType.REPAIRS: ('EquipmentId', 'EquipmentName', 'Location', 'CompletedDate', 'ReportedTotalCost'),
            ReportType.SERVICE_ORDERS: ('EquipmentId', 'EquipmentName', 'Location', 'ScheduledDate', 'CompletedDate', 'Status'),
            ReportType.TMA_WORK_ORDERS: ('WorkOrderId', 'RequestDate', 'AssignedTo'),
        }[kind]
        missing = tuple((key, sum(row.get(key) in ('', None) for row in rows)) for key in important)
        if kind == ReportType.REPAIRS:
            summary = read_summary(cleaned.supplemental_outputs[0][1])
            keys = ('ReportedLaborCost', 'ReportedPartsCost', 'ReportedTotalCost', 'ReportedRepairCount',
                    'KnownRepairTotalCost', 'UnavailableRepairCostCount', 'RepairTotalDifference',
                    'SummaryComponentsDifference', 'ReconciliationStatus')
            values = {key: None if summary[key] is None else str(summary[key]) for key in keys}
            # Known sums are explicitly incomplete if any retained value is null.
            for key in ('EstimatedLaborCost', 'LegacyPartsCost', 'LegacyLaborCost', 'LegacyEstimatedTotalCost'):
                available = [r[key] for r in rows if r[key] is not None]
                values[key + 'KnownSum'] = str(sum(available)) if available else None
                values[key + 'MissingCount'] = str(len(rows) - len(available))
            financial = tuple(values.items())
        # TMA emits its existing parser counters rather than CSV diagnostics.
        if kind == ReportType.TMA_WORK_ORDERS:
            dates = tuple((w.split(':', 1)[0], int(w.split(':', 1)[1])) for w in cleaned.warnings
                          if w.split(':', 1)[0] in ('tma_parseable_source_request_dates', 'invalid_source_dates',
                                                   'tma_cross_period_source_dates'))
            exclusions = (('rows_excluded_by_existing_cleaner', source_count - retained),)
    failure = result.status == 'failure'
    unsupported = any(word in result.code for word in ('unsupported', 'layout', 'headers', 'schema', 'missing_required_columns'))
    status = ('unsupported' if unsupported else 'failed') if failure else ('warnings' if result.warnings or result.status == 'needs_review' else 'previewed')
    return ReportPreview(period, kind.value, source.name, status, result.code,
        source_count, retained, source_count - retained if source_count is not None and retained is not None else None,
        exclusions, missing, dates, financial, result.warnings, integrity, source.sha256 or '', source.version,
        cleaned.cleaner_version if cleaned else '', result.status.value,
        failure_scope='report_validation' if failure else '')


def preview_history(provider, inventory, output_root, *, progress=None, on_result=None, on_start=None, cancelled=None):
    """One verified read and one real preview per unambiguous report; no write API.

    Existing candidates are consulted read-only. Detailed unchanged previews rerun
    the same cleaner so excluded/missing values are not lost through fast skipping.
    Completed aggregates are delivered incrementally; cancellation preserves every
    expected slot, with remaining slots explicitly not previewed.
    """
    periods = periods_between(inventory.start, inventory.end)
    if tuple(m.period for m in inventory.months) != periods or str(provider.root) != inventory.root:
        raise StorageError('historical_inventory_selection_changed')
    problem = candidate_location_error(Path(output_root))
    if problem:
        raise StorageError('historical_preview_requires_trusted_local_candidates')
    coordinator = powerbi_coordinator(output_root)
    stop = cancelled if cancelled is not None else Event()
    results = []
    notices = []
    for month in inventory.months:
        if tuple(r.report_type for r in month.reports) != tuple(ReportType):
            raise StorageError('historical_inventory_selection_changed')
        ignored_count = sum(i.code == IGNORED_EXTRA_NOTICE for i in month.issues)
        if ignored_count:
            notices.append(InventoryNotice(month.period, IGNORED_EXTRA_NOTICE, ignored_count))
        blocking_month = tuple(i for i in month.issues if i.code != IGNORED_EXTRA_NOTICE)
        for report in month.reports:
            kind = report.report_type
            item = ReportPreview(month.period, kind.value,
                '; '.join(s.name for s in report.sources), code='not_previewed')
            if not stop.is_set():
                if on_start:
                    on_start(month.period, kind.value)
                issues = tuple(i.code for i in (*report.issues, *blocking_month))
                if blocking_month or report.status != 'found' or len(report.sources) != 1:
                    status = ('unsupported' if 'historical_unsupported_extension' in issues else
                              'missing' if report.status == 'missing' else
                              'not_previewed' if report.status == 'not_scanned' else 'failed')
                    item = ReportPreview(month.period, kind.value, item.source_filename, status,
                                         issues[0] if issues else 'historical_report_' + report.status, warnings=issues,
                        failure_scope='discovery_month' if blocking_month and not report.issues else 'discovery_report')
                else:
                    source = report.sources[0]
                    try:
                        if is_temporary_filename(source.name):
                            raise StorageError('historical_selected_source_temporary')
                        read = verify_inventory_source(provider, source)
                        result = coordinator.preview(ProcessingRequest(kind, month.period,
                            raw_bytes=read.content, source_name=source.name), include_details=True)
                        item = _summarize(result, month.period, kind, source, read.integrity)
                    except ProcessingError as error:
                        code = str(error)
                        stale = code in ('storage_source_changed', 'storage_source_changed_or_partial',
                                         'storage_source_hash_mismatch', 'input_not_a_file')
                        item = ReportPreview(month.period, kind.value, source.name, 'stale' if stale else 'failed',
                            code, integrity=('not_read' if code == 'historical_selected_source_temporary' else
                                       'changed_rediscovery_required' if stale else 'read_failed'),
                            source_sha256=source.sha256 or '', source_version=source.version, failure_scope='selected_source')
                    except OSError:
                        item = ReportPreview(month.period, kind.value, source.name, 'failed', 'storage_file_unavailable', integrity='read_failed', failure_scope='selected_source')
                    except Exception:
                        # Do not expose exception text or allow one adapter failure to hide other months.
                        item = ReportPreview(month.period, kind.value, source.name, 'failed', 'preview_failed', failure_scope='preview')
                    finally:
                        # Do not carry a prior file's bytes into the next read.
                        read = result = None
            results.append(item)
            if on_result:
                on_result(item)
            if progress:
                progress(len(results), len(periods) * len(ReportType))
    return BatchPreview(inventory.start, inventory.end, inventory.layout,
                        datetime.now(timezone.utc).isoformat(), tuple(results), stop.is_set(), tuple(notices))


EXPORT_COLUMNS = ('Purpose', 'ReportingMonth', 'ReportType', 'SourceFilename', 'SourceRecordCount',
    'RetainedRecordCount', 'ExcludedRecordCount', 'ExclusionCounts', 'MissingRetainedValueCounts',
    'DateObservationCounts', 'FinancialStatus', 'ReportedLaborCost', 'ReportedPartsCost', 'ReportedTotalCost',
    'MissingReportedCostCount', 'FinancialSummary', 'WarningCodes', 'PreviewStatus', 'ReasonCode', 'SourceIntegrity',
    'FailureScope', 'IgnoredExtraFilesInMonth')


def _check_export_path(path, *, windows=None):
    windows = os.name == 'nt' if windows is None else windows
    if windows and (len(str(path).encode('utf-16-le')) // 2 >= 260 or
                    len(str(path.parent).encode('utf-16-le')) // 2 >= 248):
        raise StorageError('historical_export_path_too_long')


def export_preview(batch, target, *, protected_roots):
    """Exclusive, fsynced local diagnostic export outside all workspace roots.

    Nothing in this report can authorize processing, approval or publication.
    """
    path = Path(target).absolute()
    # Deterministic precedence on every OS: links, extension, location policy.
    # Windows' location policy also rejects links; run the specific guard first.
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise StorageError('storage_path_rejected')
    if path.suffix.lower() not in ('.csv', '.json') or candidate_location_error(path):
        raise StorageError('historical_export_requires_local_csv_or_json')
    if any(path.resolve().is_relative_to(Path(root).resolve()) for root in protected_roots):
        raise StorageError('historical_export_overlaps_workspace')
    # Fail clearly on classic Windows path limits before creating anything.
    _check_export_path(path)
    if path.suffix.lower() == '.json':
        raw = json.dumps(batch.document(), indent=2) + '\n'
    else:
        stream = StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(EXPORT_COLUMNS)
        for r in batch.reports:
            name = r.source_filename
            # Excel formula protection for untrusted local filenames only.
            if name.startswith(('=', '+', '-', '@', '\t', '\r')):
                name = "'" + name
            financial = dict(r.financial)
            writer.writerow(('NonproductionDiagnosticPreview', r.month, r.report_type, name,
                r.source_records, r.retained_records, r.excluded_records,
                json.dumps(dict(r.exclusions)), json.dumps(dict(r.missing_values)),
                json.dumps(dict(r.date_observations)), financial.get('ReconciliationStatus'),
                financial.get('ReportedLaborCost'), financial.get('ReportedPartsCost'), financial.get('ReportedTotalCost'),
                financial.get('UnavailableRepairCostCount'), json.dumps(financial),
                '; '.join(r.warnings), LABELS[r.status], r.code, r.integrity, r.failure_scope,
                sum(n.count for n in batch.inventory_notices if n.month == r.month)))
        raw = stream.getvalue()
    owned = False
    try:
        with path.open('xb') as output:
            owned = True
            output.write(raw.encode('utf-8-sig'))
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError:
        raise StorageError('historical_export_exists') from None
    except BaseException:
        if owned:
            path.unlink(missing_ok=True)
        raise
    return path
