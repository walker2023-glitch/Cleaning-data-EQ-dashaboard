"""Plain-language presentation of engine categories; never display raw errors."""

from equipment_data_manager.processing.models import ProcessingStatus

ERRORS = {
    "review_packet_missing_reports": "A complete review packet requires all three current Power BI candidates for this month. Process the missing reports first.",
    "review_packet_requires_powerbi_workspace": "Load the matching folder configuration and use Power BI CSV candidate mode before exporting.",
    "review_packet_contract_mismatch": "A selected candidate failed the packet schema/count/month checks. Keep the store intact and contact your maintainer.",
    "folder_ingestion_contract_rejected": "The candidate failed the folder-ingestion schema/type/status checks. No review packet was exported.",
    "unsafe_review_packet_folder": "The review packet folder redirects outside the candidate workspace. Choose a trusted local folder.",
    "workspace_folders_overlap": "Raw, candidate and approved folders must be separate and must not contain each other.",
    "input_not_a_file": "This file is missing or is not a regular file. Select it again.",
    "unsupported_file_format": "Select CSV for CompuClean or the supported XLSX layout for TMA Work Orders.",
    "empty_input": "This report is empty. Select a report containing records.",
    "missing_required_columns": "The columns do not match this report type's supported layout. Check the report type and export.",
    "duplicate_headers": "The report has duplicate column headings. Supply a corrected export.",
    "blank_headers": "The report has blank column headings. Supply a corrected export.",
    "invalid_csv_row_width": "Some rows have an unexpected number of columns. Check the CSV export.",
    "invalid_csv_or_encoding": "The file is not a supported UTF-8 CSV. Check its format and encoding.",
    "unverified_header_layout": "This header layout has not been verified. Supply a representative sample for review.",
    "ambiguous_service_layout": "This service export has competing column names. The layout needs review.",
    "report_type_awaiting_verified_fixtures": "TMA Work Orders are awaiting format validation and cannot be processed.",
    "legacy_xls_awaiting_sample": "Legacy XLS needs an actual export sample and format validation. Do not rename it to CSV or XLSX.",
    "invalid_xlsx_file": "This is not a readable XLSX workbook. Check the original Excel export.",
    "unsupported_work_order_layout": "TMA requires one worksheet with its title, five-column header, records and final summary.",
    "work_order_title_period_mismatch": "The TMA report title does not match the supported title and selected reporting month.",
    "invalid_work_order_summary": "The TMA final record-count summary is missing or invalid.",
    "work_order_summary_count_mismatch": "The TMA summary does not match the number of source records.",
    "invalid_repair_summary": "The repeated repair summary has an unrecognized value. Check the complete export.",
    "inconsistent_repair_summary": "Repeated repair summaries disagree. Supply a consistent export.",
    "repair_summary_count_mismatch": "The repair summary count does not match the source records.",
    "invalid_legacy_export_schema": "The legacy candidate does not match its known output schema. Normalized export stopped.",
    "invalid_normalized_schema": "The Power BI candidate schema failed validation. No candidate was selected.",
    "invalid_normalized_number": "A candidate number cannot be represented safely in the normalized schema.",
    "invalid_normalized_date": "A candidate date does not match the known legacy date format.",
    "normalization_source_alignment_failed": "Source records could not be paired reliably with the cleaned candidate. Export stopped rather than guessing.",
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
        "production_publication_blocked": "Power BI CSV candidate only. Production publication is blocked until financial reconciliation and trusted-output approval.",
        "normalized_financial_values_unavailable": "Rows with unavailable source parts/total values left blank; original calculated values remain in the Legacy columns",
        "source_record_numbers_unavailable": "TMA exclusions prevent a verified source-record mapping. SourceRecordNumber is blank; candidate ordinals remain available.",
        "legacy_unmapped_source_columns": "Source columns omitted by the legacy candidate; the normalized export restores supported metadata in explicit columns",
        "normalized_unmapped_source_columns": "Additional source columns are outside the normalized contract and remain only in the original input",
        "production_accuracy_unverified": "Accuracy against departmental reports has not been verified. Review this candidate before use.",
        "legacy_duration_defaults_and_rate_unverified": "Existing duration defaults and labor rate were retained; they still need departmental approval.",
        "legacy_parser_warnings": "The existing date parser reported a warning. Review date interpretation.",
        "invalid_source_dates": "Source date values could not be parsed",
        "invalid_source_money": "Source money values were invalid; the existing cleaner may treat them as zero",
        "rows_excluded_by_legacy": "Rows excluded by the existing cleaning rules",
        "unmapped_source_columns": "Source columns are not included in the cleaned output",
        "cross_period_output_dates": "Accepted service dates fall outside the selected month",
        "service_status_inferred": "Blank or unrecognized service statuses used the existing date-based fallback",
        "repair_source_totals_differ": "Reported repair totals differ from the existing calculated totals. Review the cost mapping and labor rules before use.",
        "repair_cost_mapping_unverified": "Repair source cost fields and calculated totals need a trusted expected result; existing calculations were preserved.",
        "tma_output_contract_provisional": "TMA uses the original requests cleaner's candidate schema and title. Departmental output approval is still required.",
        "estimated_price_unavailable": "This export has no cost field. Estimated Price is blank; no price has been inferred.",
    }
    text = messages.get(key, "The engine reported an additional warning requiring review.")
    return f"{text}: {count}" if count.isdigit() else text


REASONS = {
    'accepted': 'Accepted by existing rules',
    'missing_equipment_identity': 'Excluded: both equipment ID and name missing',
    'invalid_completed_date': 'Excluded: completed date missing or invalid',
    'outside_reporting_period': 'Parsed dates outside confirmed reporting month',
    'missing_equipment_id': 'Excluded: equipment ID missing',
    'missing_scheduled_date': 'Excluded: scheduled date missing',
    'placeholder_description': 'Excluded: placeholder description',
    'no_parseable_service_date': 'Excluded: neither service date parses',
    'empty_cleaned_description': 'Excluded: description empty after existing suffix removal',
    'delete_duplicate_description': 'Excluded: description starts with delete duplicate',
}


def diagnostic_lines(diagnostics):
    """Private date cells are visible locally, never saved to history or logs."""
    summary = diagnostics.summary()
    lines = [f"Engine reporting month: {diagnostics.selected_period}",
             f"Source SHA-256: {diagnostics.source_sha256}",
             f"Cleaner: {diagnostics.cleaner_version}",
             f"Source records: {len(diagnostics.records)} | Retained by cleaner before validation: {diagnostics.retained_rows}"]
    lines.extend(f"{REASONS.get(reason, 'Unclassified reason')}: {count}"
                 for reason, count in summary['reason_counts'].items())
    lines.append("Local date trace (data-record numbers, not CSV line numbers):")
    for row in diagnostics.records:
        values = '; '.join(f"{date.column} {date.raw_value!r} -> {date.parsed_value or 'invalid/blank'}"
                           for date in row.dates)
        lines.append(f"Record {row.record}: {REASONS.get(row.reason, 'Unclassified reason')} | {values}")
    return lines
