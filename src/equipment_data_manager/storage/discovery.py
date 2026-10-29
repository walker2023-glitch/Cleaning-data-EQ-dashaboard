"""Explicit folder mappings for any read provider; never recurse into history."""
from dataclasses import dataclass
from pathlib import PurePath
from equipment_data_manager.processing.cleaners import validate_period
from equipment_data_manager.processing.models import ReportType
from equipment_data_manager.storage.contracts import StorageError


@dataclass(frozen=True, repr=False)
class StorageDiscovery:
    files: tuple
    missing: tuple
    issues: tuple


def discover_reports(provider, period, folders):
    validate_period(period)
    if set(folders) != set(ReportType) or any(not isinstance(v,str) or not v for v in folders.values()):
        raise StorageError('storage_report_mapping_incomplete')
    files, issues = [], []
    for kind in ReportType:
        try:
            for entry in provider.list_files(folders[kind]):
                suffix = PurePath(entry.name).suffix.lower()
                if suffix in (('.xlsx','.xls') if kind == ReportType.TMA_WORK_ORDERS else ('.csv',)):
                    files.append((kind, entry))
        except StorageError as error:
            issues.append((kind, str(error)))
    present = {kind for kind,_ in files}
    return StorageDiscovery(tuple(files), tuple(k for k in ReportType if k not in present), tuple(issues))
