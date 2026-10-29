"""Count and report-level totals in the observed 14-column repair export.

These values are metadata, not extra transactions or approved business baselines.
The original cost/duration mappings are deliberately unchanged.
"""

from decimal import Decimal
import re

from equipment_data_manager.processing.interfaces import ReconciliationMetric
from equipment_data_manager.processing.models import ProcessingError


class SummaryRepairsLayout:
    HEADERS = frozenset({
        "AccountName2", "PersonnelId5", "PersonnelId1", "PersonnelId3", "PersonnelId4",
        "CompletedDate1", "Textbox38", "Description", "Details", "Textbox16",
        "Textbox10", "Textbox11", "Textbox12", "Textbox13",
    })

    @classmethod
    def matches(cls, columns):
        return set(columns) == cls.HEADERS

    @classmethod
    def metrics(cls, frame):
        if frame.empty:
            raise ProcessingError("no_output_rows")
        metrics = []
        fields = (
            ("Textbox13", r"# of Repairs:\s*([0-9]+)", "Source repair records", "count"),
            ("Textbox10", r"Total Labor:\s*\$([0-9,]+(?:\.[0-9]{2})?)", "Source reported labor", "legacy_dollars"),
            ("Textbox11", r"Total Parts:\s*\$([0-9,]+(?:\.[0-9]{2})?)", "Source reported parts", "legacy_dollars"),
            ("Textbox12", r"Total Cost:\s*\$([0-9,]+(?:\.[0-9]{2})?)", "Source reported cost", "legacy_dollars"),
        )
        for column, pattern, name, unit in fields:
            values = set()
            for cell in frame[column]:
                match = re.fullmatch(pattern, str(cell).strip())
                if match is None:
                    raise ProcessingError("invalid_repair_summary")
                values.add(Decimal(match.group(1).replace(",", "")))
            if len(values) != 1:
                raise ProcessingError("inconsistent_repair_summary")
            value = next(iter(values))
            if unit == "count" and value != len(frame):
                raise ProcessingError("repair_summary_count_mismatch")
            metrics.append(ReconciliationMetric(name, value, unit))
        return tuple(metrics)
