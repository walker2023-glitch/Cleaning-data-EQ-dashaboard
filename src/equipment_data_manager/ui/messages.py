"""Plain-language presentation of engine categories; never display raw errors."""

from equipment_data_manager.processing.models import ProcessingStatus

ERRORS = {
    "input_not_a_file": "This file is missing or is not a regular file. Select it again.",
    "unsupported_file_format": "Select a CSV export. Excel files are not supported in this prototype.",
    "empty_input": "This report is empty. Select a report containing records.",
    "missing_required_columns": "The columns do not match this report type's supported layout. Check the report type and export.",
    "duplicate_headers": "The report has duplicate column headings. Supply a corrected export.",
    "blank_headers": "The report has blank column headings. Supply a corrected export.",
    "invalid_csv_row_width": "Some rows have an unexpected number of columns. Check the CSV export.",
    "invalid_csv_or_encoding": "The file is not a supported UTF-8 CSV. Check its format and encoding.",
    "unverified_header_layout": "This header layout has not been verified. Supply a representative sample for review.",
    "ambiguous_service_layout": "This service export has competing column names. The layout needs review.",
    "report_type_awaiting_verified_fixtures": "TMA Work Orders are awaiting format validation and cannot be processed.",
    "invalid_reporting_period": "Choose a valid reporting month and four-digit year.",
    "output_period_mismatch": "The cleaned records do not match the selected reporting month. Check the month and file.",
    "no_output_rows": "No eligible records remain after the existing cleaning rules. Check the report and month.",
    "nonfinite_output_number": "The report produced an invalid numeric result. Supply a corrected report for review.",
    "file_or_storage_unavailable": "A file or output folder could not be accessed. Check that it is available and writable.",
    "manifest_unavailable": "Processing history could not be read. Keep the output folder intact and contact your maintainer.",
    "existing_output_hash_mismatch": "An earlier output was changed outside the application. Processing stopped to protect its history.",
    "existing_output_missing_or_unreadable": "An earlier output is missing or unreadable. Processing stopped; do not delete the history.",
    "input_changed_since_preview": "This file changed after preview. Preview it again before processing.",
    "multiple_files_same_period": "Different files were selected for the same report type and month. Select one version, then preview again.",
    "correction_not_approved": "This correction needs your explicit review and confirmation.",
    "replacement_confirmation_required": "This month has a different current output. Review the proposed correction.",
    "cancelled": "Stopped before this file was processed. Completed files remain saved.",
    "invalid_service_order_summary": "The repeated service-order summary is missing or has an unrecognized format. Check the export.",
    "service_order_summary_mismatch": "The report's service-order summary does not match its record count. Check the complete export before processing.",
}


def result_label(result, *, preview=False):
    if result.status == ProcessingStatus.SUCCESS:
        return "New report" if preview else "Saved locally"
    if result.status == ProcessingStatus.SKIPPED:
        return "Already processed - will skip" if preview else "Skipped - already processed"
    if result.status == ProcessingStatus.NEEDS_REVIEW:
        return "Potential correction - review required"
    return "Stopped" if result.code == "cancelled" else "Needs attention"


def error_message(code: str):
    return ERRORS.get(code, "This report could not be processed safely. Preview again or contact your maintainer.")


def warning_message(code: str):
    key, _, count = code.partition(":")
    messages = {
        "production_accuracy_unverified": "Accuracy against departmental reports has not been verified. Review this candidate before use.",
        "legacy_duration_defaults_and_rate_unverified": "Existing duration defaults and labor rate were retained; they still need departmental approval.",
        "legacy_parser_warnings": "The existing date parser reported a warning. Review date interpretation.",
        "invalid_source_dates": "Source date values could not be parsed",
        "invalid_source_money": "Source money values were invalid; the existing cleaner may treat them as zero",
        "rows_excluded_by_legacy": "Rows excluded by the existing cleaning rules",
        "unmapped_source_columns": "Source columns are not included in the cleaned output",
        "cross_period_output_dates": "Accepted service dates fall outside the selected month",
        "estimated_price_unavailable": "This export has no cost field. Estimated Price is blank; no price has been inferred.",
    }
    text = messages.get(key, "The engine reported an additional warning requiring review.")
    return f"{text}: {count}" if count.isdigit() else text
