"""Observed CompuClean Service Orders List export without a price field.

Column mappings and transformations remain in the original service cleaner.
This adapter only recognizes the exact observed header set, checks report-count
metadata, and represents the absent price as missing (not a guessed cost).
"""

import re

import pandas as pd

from equipment_data_manager.processing.models import ProcessingError


class SummaryServiceOrdersLayout:
    HEADERS = frozenset({
        "AccountName2", "EquipmentId1", "EquipmentName1", "VendorName",
        "ScheduledDate", "CompletedDate", "Name", "Description", "Textbox21", "Textbox56",
    })

    @classmethod
    def matches(cls, columns) -> bool:
        return set(columns) == cls.HEADERS

    @classmethod
    def prepare(cls, frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        if not cls.matches(frame.columns):
            raise ProcessingError("missing_required_columns")
        if frame.empty:
            raise ProcessingError("no_output_rows")
        counts = set()
        for value in frame["Textbox56"]:
            match = re.fullmatch(r"Total Service Orders:\s*([0-9]+)\s*", str(value).strip())
            if match is None:
                raise ProcessingError("invalid_service_order_summary")
            counts.add(int(match.group(1)))
        if len(counts) != 1 or next(iter(counts)) != len(frame):
            raise ProcessingError("service_order_summary_mismatch")
        prepared = frame.copy()
        # The original parse_dollar(missing) -> 0 path emits a blank Estimated
        # Price. This does not assert the service was free or invent a cost.
        prepared["Cost"] = pd.NA
        return prepared, next(iter(counts))
