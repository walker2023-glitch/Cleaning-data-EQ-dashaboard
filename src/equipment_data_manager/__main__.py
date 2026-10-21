"""Offline diagnostics and explicit local-only candidate processing."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from equipment_data_manager import __version__
from equipment_data_manager.config import ConfigurationError, load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Equipment Data Manager (offline)")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--check-config", type=Path, metavar="PATH")
    commands = parser.add_subparsers(dest="command")
    process = commands.add_parser("process", help="Create local candidate CSVs; production accuracy is unverified")
    process.add_argument("files", nargs="+", type=Path)
    process.add_argument("--report-type", required=True, choices=["repairs", "service_orders", "tma_work_orders"])
    process.add_argument("--period", required=True, help="Operator-confirmed YYYY-MM")
    process.add_argument("--output-dir", required=True, type=Path)
    process.add_argument("--replacement-token", help="Token from the reviewed corrected-file result (single file only)")
    process.add_argument("--output-format", choices=["legacy", "powerbi"], default="legacy", help="Candidate CSV format; Power BI mode does not publish")
    process.add_argument("--preview", action="store_true", help="Validate without writing candidate files or history")
    process.add_argument("--include-date-values", action="store_true", help="Include private source date cells/record numbers in local diagnostics; do not publish this output")
    args = parser.parse_args(argv)
    if args.command == "process":
        if args.check_config is not None:
            parser.error("Use configuration diagnostics separately from processing.")
        if args.replacement_token and len(args.files) != 1:
            parser.error("Replacement confirmation requires exactly one input file.")
        from equipment_data_manager.processing.coordinator import ProcessingCoordinator
        from equipment_data_manager.processing.models import ProcessingRequest, ProcessingStatus

        if args.output_format == "powerbi":
            from equipment_data_manager.processing.powerbi import powerbi_coordinator
            coordinator = powerbi_coordinator(args.output_dir)
        else:
            coordinator = ProcessingCoordinator(args.output_dir)
        operation = coordinator.preview if args.preview else coordinator.process
        results = tuple(operation(ProcessingRequest(args.report_type, args.period, input_path=path,
                              replacement_token=args.replacement_token))
            for path in args.files
        )
        print(json.dumps([
            {
                "status": result.status.value, "code": result.code,
                "input_rows": result.input_rows, "output_rows": result.output_rows,
                "output_location": str(result.output_location) if result.output_location else None,
                "revision_id": result.artifact.revision_id if result.artifact else None,
                "previous_revision": result.previous.revision_id if result.previous else None,
                "previous_output_location": str(result.previous.output_path) if result.previous else None,
                "previous_input_rows": result.previous.input_rows if result.previous else None,
                "previous_output_rows": result.previous.output_rows if result.previous else None,
                "candidate_output_hash": sha256(result.cleaned.output_bytes).hexdigest() if result.cleaned else None,
                "candidate_metrics": [
                    {"name": metric.name, "value": str(metric.value), "unit": metric.unit}
                    for metric in result.cleaned.reconciliation_metrics
                ] if result.cleaned else [],
                "replacement_token": result.replacement_token, "warnings": result.warnings,
                "diagnostics": result.diagnostics.summary(include_date_values=args.include_date_values) if result.diagnostics else None,
            }
            for result in results
        ], indent=2))
        return 0 if all(r.status in (ProcessingStatus.SUCCESS, ProcessingStatus.SKIPPED) for r in results) else 1
    if args.check_config is not None:
        try:
            load_config(args.check_config)
        except ConfigurationError as exc:
            # Exceptions contain categories only, never config values.
            parser.exit(2, f"Configuration error: {exc}\n")
        print("Configuration valid for M0 offline mode; Microsoft access is disabled.")
    else:
        print("Equipment Data Manager: processing is not enabled by default. Use 'process' for offline candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
