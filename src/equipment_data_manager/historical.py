"""Read-only historical inventory. No cleaner, candidate store or Graph activation.

Folder and filename matches are routing hints, never source schema/month approval.
Local bytes are read through the existing provider and never retained in this model.
"""
import argparse
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePath
import re

from equipment_data_manager.processing.cleaners import validate_period
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.settings import FOLDER_LAYOUTS, candidate_location_error
from equipment_data_manager.storage.contracts import StorageError, StorageFile
from equipment_data_manager.storage.local import LocalFolderStorage

MONTH_LABELS = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12,
}
LAYOUT_LABELS = {'standard': 'Standard month/report-type layout',
                 'sharepoint_year_month': 'SharePoint year/month layout'}
MAX_MONTHS = 120
MAX_FILE_BYTES = 64 * 1024 * 1024


ISSUE_TEXT = {
    'historical_month_missing': 'Month folder missing. Check the selected layout and root.',
    'historical_duplicate_month_folders': 'Several folders represent this month. No folder was chosen.',
    'historical_invalid_month_folder': 'Folder name is unsupported. Expected YYYY-MM (Jan) or a full English month name.',
    'historical_month_label_mismatch': 'The year, month number and month label disagree. No files from this folder were selected.',
    'historical_duplicate_reports': 'More than one possible report. No report was selected.',
    'historical_unrecognized_filename': 'Filename is unrecognized; it was not assigned a report type.',
    'historical_filename_month_mismatch': 'The Work Orders filename disagrees with the selected month.',
    'historical_temporary_file_ignored': 'Temporary or incomplete-download file ignored. Verify the export/download finished.',
    'historical_unsupported_extension': 'Unsupported format. Repairs and Service Orders require CSV; TMA requires a supported XLSX or genuine legacy XLS workbook.',
    'storage_file_not_downloaded': 'File or folder is cloud-only/offline. Make it available using the approved sync-client procedure.',
    'storage_source_changed': 'Source changed during inventory. Wait for the export/download to finish, then discover again.',
    'storage_source_changed_or_partial': 'Source changed or was only partially read. Discover again after it is stable.',
    'storage_folder_missing': 'Required report folder is missing.',
    'storage_access_denied': 'Access denied. Check permissions and local availability with IT.',
    'storage_link_rejected': 'Linked file/folder detected. Links and junctions are not followed during inventory.',
    'historical_scan_stopped': 'Discovery stopped. This month is incomplete; discover again before use.',
    'historical_file_too_large': 'Report exceeds the 64 MiB inventory limit. Contact the maintainer.',
    'storage_directory_limit': 'Directory exceeds the 4096-entry inventory limit. Contact the maintainer.',
}


def describe_issue(issue):
    return ISSUE_TEXT.get(issue.code, 'Source unavailable. Check local availability and permissions, then discover again.') + (f'\n  {issue.path}' if issue.path else '')


def periods_between(start, end):
    validate_period(start)
    validate_period(end)
    first, last = (int(p[:4]) * 12 + int(p[5:]) - 1 for p in (start, end))
    if last < first or last - first >= MAX_MONTHS:
        raise StorageError('historical_invalid_range')
    return tuple(f'{i // 12:04d}-{i % 12 + 1:02d}' for i in range(first, last + 1))


def month_folder_period(name, year):
    """Require exact numeric year/month plus a known agreeing English label."""
    match = re.fullmatch(r'(\d{4})-(\d{2}) \(([A-Za-z]+)\)', name)
    if not match:
        raise StorageError('historical_invalid_month_folder')
    folder_year, number, label = match.groups()
    if folder_year != year or MONTH_LABELS.get(label.casefold()) != int(number):
        raise StorageError('historical_month_label_mismatch')
    period = f'{folder_year}-{number}'
    validate_period(period)
    return period


def filename_match(name, period):
    """Return kind and a period issue. Only anchored, documented stems accepted."""
    if re.fullmatch(r'CU_Repair_WO_History_-_Previous_Month_\(HI-042b\)[0-9]{1,30}\.xls', name, re.I):
        return ReportType.TMA_WORK_ORDERS, ''
    stem = PurePath(name).stem
    normalized = re.sub(r'[ _-]+', ' ', stem).casefold()
    known = {'compuclean repair report': ReportType.REPAIRS,
             'compuclean service orders list': ReportType.SERVICE_ORDERS}
    if normalized in known:
        return known[normalized], ''
    match = re.fullmatch(r'work orders ([a-z]+) (\d{4})', normalized)
    if match:
        label, year = match.groups()
        month = MONTH_LABELS.get(label)
        if month:
            return ReportType.TMA_WORK_ORDERS, ('' if f'{year}-{month:02d}' == period
                                               else 'historical_filename_month_mismatch')
    return None, 'historical_unrecognized_filename'


@dataclass(frozen=True)
class InventoryIssue:
    code: str
    path: str = ''
    report_type: str = ''


@dataclass(frozen=True, repr=False)
class ReportInventory:
    report_type: ReportType
    status: str
    sources: tuple[StorageFile, ...] = ()
    issues: tuple[InventoryIssue, ...] = ()


@dataclass(frozen=True, repr=False)
class MonthInventory:
    period: str
    folders: tuple[str, ...]
    reports: tuple[ReportInventory, ...]
    issues: tuple[InventoryIssue, ...] = ()

    @property
    def complete(self):
        # Completeness means readable unambiguous filenames, NOT supported schema.
        return not self.issues and all(r.status == 'found' for r in self.reports)


@dataclass(frozen=True, repr=False)
class HistoricalInventory:
    layout: str
    root: str
    start: str
    end: str
    months: tuple[MonthInventory, ...]
    stopped: bool
    created_at: str

    def document(self):
        return dict(version=1, inventory_only=True, processing_performed=False,
                    approval='not_granted', sync_verified=False, **asdict(self))


def _issue(code, path='', kind=None):
    return InventoryIssue(code, path, kind.value if kind else '')


def _month_folders(provider, period, layout):
    if layout == 'standard':
        # Exact root listing detects a genuinely missing month without recursion.
        return tuple(f for f in provider.list_folders('.') if PurePath(f).name == period), ()
    year = period[:4]
    years = provider.list_folders('.')
    if year not in {PurePath(f).name for f in years}:
        return (), ()
    year_id = next(f for f in years if PurePath(f).name == year)
    folders, issues = [], []
    for folder in provider.list_folders(year_id):
        name = PurePath(folder).name
        try:
            if month_folder_period(name, year) == period:
                folders.append(folder)
        except StorageError as error:
            # Invalid entries are never selected. Show them for each inspected year
            # rather than silently hiding a mislabeled folder from an inventory.
            issues.append(_issue(str(error), folder))
    return tuple(folders), tuple(issues)


def is_temporary_filename(name):
    """Existing strict ignore rule, shared by discovery and selected-source checks."""
    return name.startswith(('.', '~')) or name.casefold().endswith(
        ('.tmp', '.part', '.partial', '.crdownload', '.download'))


def _reports(provider, period, folder, layout, cancelled):
    sources = {kind: [] for kind in ReportType}
    problems = {kind: [] for kind in ReportType}
    issues = []
    for kind_hint in (tuple(ReportType) if layout == 'standard' else (None,)):
        if cancelled.is_set():
            break
        target = str(PurePath(folder) / kind_hint.value) if kind_hint else folder
        try:
            entries = provider.inventory_files(target)
        except StorageError as error:
            issue = _issue(str(error), target, kind_hint)
            if kind_hint:
                problems[kind_hint].append(issue)
            else:
                issues.append(issue)
            continue
        for entry in entries:
            if cancelled.is_set():
                break
            # Never ingest Office lock files or partially downloaded/temporary names.
            if is_temporary_filename(entry.name):
                issues.append(_issue('historical_temporary_file_ignored', entry.item_id))
                continue
            kind, mismatch = (kind_hint, '') if kind_hint else filename_match(entry.name, period)
            if kind is None:
                issues.append(_issue(mismatch, entry.item_id))
                continue
            sources[kind].append(entry)
            if mismatch:
                problems[kind].append(_issue(mismatch, entry.item_id, kind))
            allowed = ('.xlsx', '.xls') if kind == ReportType.TMA_WORK_ORDERS else ('.csv',)
            if PurePath(entry.name).suffix.casefold() not in allowed:
                code = 'historical_unsupported_extension'
                problems[kind].append(_issue(code, entry.item_id, kind))
                continue
            if entry.size_bytes > MAX_FILE_BYTES:
                problems[kind].append(_issue('historical_file_too_large', entry.item_id, kind))
                continue
            try:
                read = provider.read(entry)
                # Bind the captured provider identity/version to these exact bytes.
                sources[kind][-1] = replace(entry, sha256=read.sha256)
            except StorageError as error:
                problems[kind].append(_issue(str(error), entry.item_id, kind))
    reports = []
    for kind in ReportType:
        found = sources[kind]
        if len(found) > 1:
            problems[kind].append(_issue('historical_duplicate_reports', folder, kind))
        status = ('ambiguous' if len(found) > 1 else 'blocked' if problems[kind]
                  else 'missing' if not found else 'found')
        reports.append(ReportInventory(kind, status, tuple(found), tuple(problems[kind])))
    return tuple(reports), tuple(issues)


def discover_history(provider, start, end, layout='standard', *, progress=None, cancelled=None):
    """Only root/year/month/direct type folders; no cleaner or write call exists.

    Maximum 120 months, 4096 direct entries/folder (local provider), 64 MiB/file.
    Stop between file reads; partial inventory is explicitly marked and unscanned
    months are retained as not_scanned. No inference of zero-activity months.
    """
    from threading import Event
    periods = periods_between(start, end)
    if layout not in FOLDER_LAYOUTS:
        raise StorageError('historical_invalid_layout')
    cancelled = cancelled if cancelled is not None else Event()
    months = []
    for index, period in enumerate(periods):
        folders, issues = (), ()
        reports = tuple(ReportInventory(kind, 'not_scanned') for kind in ReportType)
        if not cancelled.is_set():
            try:
                folders, issues = _month_folders(provider, period, layout)
                if len(folders) == 1:
                    reports, report_issues = _reports(provider, period, folders[0], layout, cancelled)
                    issues += report_issues
                else:
                    issues += (_issue('historical_duplicate_month_folders' if folders else 'historical_month_missing', period),)
                    reports = tuple(ReportInventory(k, 'ambiguous' if folders else 'missing') for k in ReportType)
            except StorageError as error:
                issues += (_issue(str(error), period),)
                reports = tuple(ReportInventory(k, 'blocked') for k in ReportType)
            if cancelled.is_set():
                issues += (_issue('historical_scan_stopped', period),)
        months.append(MonthInventory(period, folders, reports, issues))
        if progress:
            progress(index + 1, len(periods))
    return HistoricalInventory(layout, str(provider.root), start, end, tuple(months),
                               cancelled.is_set(), datetime.now(timezone.utc).isoformat())


def verify_inventory_source(provider, source):
    """Future preview seam: never trust an exported/imported inventory as authority."""
    if not source.sha256:
        raise StorageError('historical_missing_source_hash')
    return provider.read(source, expected_sha256=source.sha256)


def export_inventory(inventory, path):
    """Private local JSON report, exclusive destination; never inside raw sources."""
    path = Path(path).absolute()
    if path.suffix.casefold() != '.json' or candidate_location_error(path):
        raise StorageError('historical_export_requires_local_json')
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise StorageError('storage_path_rejected')
    if path.resolve().is_relative_to(Path(inventory.root).resolve()):
        raise StorageError('historical_export_overlaps_raw')
    raw = (json.dumps(inventory.document(), indent=2) + '\n').encode('utf-8')
    owned = False
    try:
        with path.open('xb') as stream:
            owned = True
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise StorageError('historical_export_exists') from None
    except BaseException:
        if owned:
            path.unlink(missing_ok=True)
        raise
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only local historical inventory; no processing/sign-in.')
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--layout', choices=FOLDER_LAYOUTS, default='standard')
    parser.add_argument('--output', type=Path, required=True, help='New trusted-local JSON report, outside raw root')
    args = parser.parse_args(argv)
    try:
        inventory = discover_history(LocalFolderStorage(args.root), args.start, args.end, args.layout)
        export_inventory(inventory, args.output)
        print(json.dumps(dict(months=len(inventory.months), complete=sum(m.complete for m in inventory.months),
                              processing_performed=False, sync_verified=False)))
        return 0
    except (ProcessingError, OSError):
        print('Inventory could not be completed or exported. Check the range, local availability, permissions and new report destination.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
