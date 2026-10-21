"""Testable presentation workflow. All cleaning decisions stay in M1."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from threading import Event
from typing import Protocol

from equipment_data_manager.processing.coordinator import ProcessingCoordinator
from equipment_data_manager.processing.models import (
    ProcessingError, ProcessingRequest, ProcessingResult, ProcessingStatus, ReportType,
)

SUPPORTED_REPORTS = {
    ReportType.REPAIRS: "Repair Reports",
    ReportType.SERVICE_ORDERS: "Service Orders List",
    ReportType.TMA_WORK_ORDERS: "TMA Work Orders",
}


@dataclass(frozen=True)
class SourceFile:
    reference: str
    name: str


class FileSource(Protocol):
    """A future approved remote source can supply bytes through this boundary."""

    def read(self, source: SourceFile) -> bytes: ...


class LocalFileSource:
    def read(self, source: SourceFile) -> bytes:
        path = Path(source.reference)
        if not path.is_file():
            raise ProcessingError("input_not_a_file")
        return path.read_bytes()


def selected_files(paths: Sequence[str]) -> tuple[SourceFile, ...]:
    """Deduplicate identical selections, never business records or basenames."""
    seen = set()
    files = []
    for value in paths:
        path = Path(value).resolve()
        if path not in seen:
            seen.add(path)
            files.append(SourceFile(str(path), path.name))
    return tuple(files)


@dataclass(frozen=True, repr=False)
class PreviewEntry:
    source: SourceFile
    report_type: ReportType
    period: str
    source_hash: str
    result: ProcessingResult


@dataclass(frozen=True, repr=False)
class RunEntry:
    preview: PreviewEntry
    result: ProcessingResult


def failure(code: str) -> ProcessingResult:
    return ProcessingResult(ProcessingStatus.FAILURE, code)


class DesktopWorkflow:
    def __init__(self, output_root: Path, *, source: FileSource | None = None,
                 coordinator: ProcessingCoordinator | None = None, output_format: str = "legacy"):
        if output_format not in ("legacy", "powerbi"):
            raise ValueError("unknown output format")
        self.source = source or LocalFileSource()
        self.base_output_root = Path(output_root).resolve()
        self.output_format = output_format
        if coordinator is None and output_format == "powerbi":
            from equipment_data_manager.processing.powerbi import powerbi_coordinator
            coordinator = powerbi_coordinator(output_root)
        self.coordinator = coordinator or ProcessingCoordinator(output_root)
        self.output_root = self.coordinator.store.root

    def preview(self, sources: Sequence[SourceFile], report_type: ReportType, period: str,
                progress: Callable[[int, int], None], cancelled: Event) -> tuple[PreviewEntry, ...]:
        entries = []
        for index, source in enumerate(sources):
            digest = ""
            try:
                if cancelled.is_set():
                    result = failure("cancelled")
                elif report_type not in SUPPORTED_REPORTS:
                    result = failure("report_type_awaiting_verified_fixtures")
                else:
                    raw = self.source.read(source)
                    digest = sha256(raw).hexdigest()
                    result = self.coordinator.preview(ProcessingRequest(
                        report_type, period, raw_bytes=raw, source_name=source.name,
                    ))
            except ProcessingError as exc:
                result = failure(str(exc))
            except OSError:
                result = failure("file_or_storage_unavailable")
            except Exception:
                result = failure("processing_failed")
            entries.append(PreviewEntry(source, report_type, period, digest, result))
            progress(index + 1, len(sources))
        # Two different proposed files for one month cannot both be the new month.
        # Require the operator to choose one; identical content will safely skip.
        hashes = {entry.source_hash for entry in entries if entry.source_hash and
                  entry.result.status != ProcessingStatus.FAILURE}
        if len(hashes) > 1:
            entries = [replace(entry, result=failure("multiple_files_same_period"))
                       if entry.result.status != ProcessingStatus.FAILURE else entry
                       for entry in entries]
        return tuple(entries)

    def process(self, entries: Sequence[PreviewEntry], approvals: Mapping[int, str],
                progress: Callable[[int, int], None], cancelled: Event) -> tuple[RunEntry, ...]:
        results = []
        for index, entry in enumerate(entries):
            result = entry.result
            try:
                if cancelled.is_set():
                    result = failure("cancelled")
                elif entry.report_type not in SUPPORTED_REPORTS:
                    result = failure("report_type_awaiting_verified_fixtures")
                elif result.status == ProcessingStatus.FAILURE:
                    pass
                elif (result.status == ProcessingStatus.NEEDS_REVIEW and
                      approvals.get(index) != result.replacement_token):
                    # Preview tokens are never applied without an explicit action.
                    result = replace(result, code="correction_not_approved")
                else:
                    raw = self.source.read(entry.source)
                    if sha256(raw).hexdigest() != entry.source_hash:
                        result = failure("input_changed_since_preview")
                    else:
                        # M1 rechecks live manifest state and validates the token.
                        result = self.coordinator.process(ProcessingRequest(
                            entry.report_type, entry.period, raw_bytes=raw,
                            source_name=entry.source.name, replacement_token=approvals.get(index),
                        ))
            except ProcessingError as exc:
                result = failure(str(exc))
            except OSError:
                result = failure("file_or_storage_unavailable")
            except Exception:
                result = failure("processing_failed")
            results.append(RunEntry(entry, result))
            progress(index + 1, len(entries))
        return tuple(results)
