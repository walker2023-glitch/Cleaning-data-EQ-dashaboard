"""GUI-independent requests/results; no source contents in error messages."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from equipment_data_manager.processing.interfaces import CleanResult


class ReportType(StrEnum):
    REPAIRS = "repairs"
    SERVICE_ORDERS = "service_orders"
    TMA_WORK_ORDERS = "tma_work_orders"


class ProcessingStatus(StrEnum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    NEEDS_REVIEW = "needs_review"
    FAILURE = "failure"


class ProcessingError(ValueError):
    """Category-only failure safe to show in UI/CLI, without raw cell data."""


@dataclass(frozen=True)
class ProcessingRequest:
    report_type: ReportType | str
    period: str
    # Exactly one input representation is required.
    input_path: Path | None = None
    raw_bytes: bytes | None = None
    source_name: str = "report.csv"
    # Confirmation binds the current revision and the proposed content/version.
    replacement_token: str | None = None


@dataclass(frozen=True)
class OutputRevision:
    revision_id: str
    output_path: Path
    source_hash: str
    output_hash: str
    cleaner_version: str
    input_rows: int
    output_rows: int


@dataclass(frozen=True)
class ProcessingResult:
    status: ProcessingStatus
    code: str
    warnings: tuple[str, ...] = ()
    cleaned: CleanResult | None = None
    artifact: OutputRevision | None = None
    previous: OutputRevision | None = None
    replacement_token: str | None = None

    @property
    def output_location(self) -> Path | None:
        return self.artifact.output_path if self.artifact else None

    @property
    def input_rows(self) -> int | None:
        return self.cleaned.input_rows if self.cleaned else self.artifact.input_rows if self.artifact else None

    @property
    def output_rows(self) -> int | None:
        return self.cleaned.output_rows if self.cleaned else self.artifact.output_rows if self.artifact else None
