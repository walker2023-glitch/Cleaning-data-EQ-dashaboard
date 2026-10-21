"""Contracts independent of pandas, the desktop UI, and Microsoft Graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from equipment_data_manager.processing.diagnostics import CleaningDiagnostics


@dataclass(frozen=True)
class ColumnSchema:
    name: str
    data_type: str


@dataclass(frozen=True)
class ReconciliationMetric:
    name: str
    value: Decimal
    unit: str


@dataclass(frozen=True)
class CleanResult:
    """Candidate output, not approval to publish.

    Adapters must account for row exclusions and return safe warning categories.
    Business rules and validation tolerances await approved fixtures in M1.
    """

    output_bytes: bytes
    input_rows: int
    output_rows: int
    schema: tuple[ColumnSchema, ...]
    warnings: tuple[str, ...]
    source_period: str
    cleaner_version: str
    reconciliation_metrics: tuple[ReconciliationMetric, ...]
    diagnostics: CleaningDiagnostics | None = field(default=None, repr=False)


class Cleaner(Protocol):
    version: str

    def clean(self, raw_bytes: bytes, *, source_name: str, period: str) -> CleanResult:
        """Return candidate CSV without file/network side effects.

        Period is YYYY-MM, confirmed by contents or an operator. Unknown layouts
        must fail explicitly. Do not infer business mappings from this contract.
        """
        ...
