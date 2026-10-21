"""Sequential offline coordination, independent of Graph and any GUI toolkit."""

from collections.abc import Iterable, Mapping
from hashlib import sha256
from pathlib import Path
import sqlite3

from equipment_data_manager.processing.cleaners import LegacyCsvCleaner, validate_period
from equipment_data_manager.processing.interfaces import Cleaner
from equipment_data_manager.processing.work_orders import TmaXlsxCleaner
from equipment_data_manager.processing.manifest import LocalOutputStore
from equipment_data_manager.processing.models import (
    ProcessingError, ProcessingRequest, ProcessingResult, ProcessingStatus, ReportType,
)


class ProcessingCoordinator:
    def __init__(self, output_root: Path, *, cleaners: Mapping[ReportType, Cleaner] | None = None):
        self.store = LocalOutputStore(output_root)
        self.cleaners = dict(cleaners) if cleaners is not None else {
            kind: LegacyCsvCleaner(kind)
            for kind in (ReportType.REPAIRS, ReportType.SERVICE_ORDERS)
        }
        if cleaners is None:
            self.cleaners[ReportType.TMA_WORK_ORDERS] = TmaXlsxCleaner()

    def process_many(self, requests: Iterable[ProcessingRequest]) -> tuple[ProcessingResult, ...]:
        """Keep request order and continue after individual file failures."""
        return tuple(self.process(request) for request in requests)

    def process(self, request: ProcessingRequest) -> ProcessingResult:
        return self._run(request, preview=False)

    def preview(self, request: ProcessingRequest) -> ProcessingResult:
        """Use the same decisions/transformations without writing any outputs."""
        return self._run(request, preview=True)

    def _run(self, request: ProcessingRequest, *, preview: bool) -> ProcessingResult:
        try:
            return self._process(request, preview=preview)
        except ProcessingError as exc:
            return ProcessingResult(ProcessingStatus.FAILURE, str(exc))
        except OSError:
            return ProcessingResult(ProcessingStatus.FAILURE, "file_or_storage_unavailable")
        except sqlite3.Error:
            return ProcessingResult(ProcessingStatus.FAILURE, "manifest_unavailable")
        except Exception:
            # Legacy/pandas/SQLite errors may contain input values. Expose only a
            # category; never log raw exceptions or cell contents to the GUI.
            return ProcessingResult(ProcessingStatus.FAILURE, "processing_failed")

    def _process(self, request: ProcessingRequest, *, preview: bool = False) -> ProcessingResult:
        try:
            report_type = ReportType(request.report_type)
        except ValueError:
            raise ProcessingError("unknown_report_type") from None
        validate_period(request.period)
        if report_type not in self.cleaners:
            raise ProcessingError("report_type_awaiting_verified_fixtures")
        if (request.input_path is None) == (request.raw_bytes is None):
            raise ProcessingError("exactly_one_input_required")
        if request.input_path is not None:
            path = Path(request.input_path)
            if not path.is_file():
                raise ProcessingError("input_not_a_file")
            source_name, raw = path.name, path.read_bytes()
        else:
            source_name, raw = request.source_name, request.raw_bytes
            if not isinstance(raw, bytes):
                raise ProcessingError("input_must_be_bytes")
        extension = Path(source_name).suffix.lower()
        if report_type == ReportType.TMA_WORK_ORDERS and extension == ".xls":
            raise ProcessingError("legacy_xls_awaiting_sample")
        expected = ".xlsx" if report_type == ReportType.TMA_WORK_ORDERS else ".csv"
        if extension != expected:
            raise ProcessingError("unsupported_file_format")
        cleaner = self.cleaners[report_type]
        source_hash = sha256(raw).hexdigest()
        # Serialize decisions on this machine. This is not a SharePoint lease.
        transaction = self.store.read_transaction if preview else self.store.transaction
        with transaction() as connection:
            current, prior_warnings = self.store.current(connection, report_type, request.period)
            if current and current.source_hash == source_hash and current.cleaner_version == cleaner.version:
                return ProcessingResult(
                    ProcessingStatus.SKIPPED, "already_processed", prior_warnings, artifact=current,
                )
            cleaned = cleaner.clean(raw, source_name=source_name, period=request.period)
            if cleaned.cleaner_version != cleaner.version or cleaned.source_period != request.period:
                raise ProcessingError("cleaner_contract_mismatch")
            if not cleaned.output_bytes or cleaned.output_rows <= 0:
                raise ProcessingError("no_output_rows")
            if current:
                proposed_hash = sha256(cleaned.output_bytes).hexdigest()
                token = sha256(
                    f"{current.revision_id}:{source_hash}:{cleaner.version}:{proposed_hash}".encode()
                ).hexdigest()
                if request.replacement_token != token:
                    return ProcessingResult(
                        ProcessingStatus.NEEDS_REVIEW, "replacement_confirmation_required",
                        cleaned.warnings, cleaned=cleaned, previous=current, replacement_token=token,
                    )
            if not current and request.replacement_token is not None:
                raise ProcessingError("replacement_target_missing")
            if preview:
                return ProcessingResult(
                    ProcessingStatus.SUCCESS, "ready_to_process", cleaned.warnings, cleaned=cleaned,
                )
            artifact = self.store.write_revision(report_type, request.period, source_hash, cleaned)
            self.store.select_revision(connection, report_type, request.period, artifact, cleaned.warnings)
            result = ProcessingResult(
                ProcessingStatus.SUCCESS, "candidate_created", cleaned.warnings,
                cleaned=cleaned, artifact=artifact, previous=current,
            )
        # Success is returned only after the manifest transaction has committed.
        return result
