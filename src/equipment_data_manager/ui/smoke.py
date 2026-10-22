"""Automated, visible-window smoke check using only bundled synthetic samples."""

import json
from pathlib import Path
from time import monotonic

from equipment_data_manager.processing.models import ProcessingStatus as Status, ReportType


def run_smoke(directory: Path | None) -> int:
    if directory is None:
        return 2
    from equipment_data_manager.ui.app import EquipmentDataManager, sample_path

    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    # Each check uses a new output store, even if the diagnostic directory exists.
    from tempfile import mkdtemp
    workspace = Path(mkdtemp(prefix="desktop-check-", dir=directory))
    source = workspace / "synthetic.csv"
    source.write_bytes(sample_path(ReportType.REPAIRS).read_bytes())
    from equipment_data_manager.ui.workflow import DesktopWorkflow
    app = EquipmentDataManager(workspace / "candidates", workflow=DesktopWorkflow(workspace / "candidates"))
    state = {"phase": 0, "started": monotonic(), "first_artifact": None, "status": "failed"}
    app.set_files([str(source)])
    app.month.set("September")
    app.year.set("2026")
    app.month_confirmed.set(True)

    def finish(passed):
        state["status"] = "passed" if passed else "failed"
        (directory / "desktop-smoke.json").write_text(json.dumps({
            "status": state["status"], "phase": state["phase"],
            "checks": ["window", "preview_without_writes", "M1_processing", "duplicate_skip",
                       "explicit_correction_review", "previous_revision_retained", "history", "TMA_XLSX_preview_process", "powerbi_all_report_types", "publication_blocked", "monthly_discovery", "mixed_preview_process", "candidate_review_packet", "approved_folder_untouched"],
        }, indent=2), encoding="utf-8")
        app._close()

    def advance():
        try:
            if monotonic() - state["started"] > 90:
                finish(False)
                return
            if app.worker.busy:
                app.after(50, advance)
                return
            phase = state["phase"]
            if phase == 0:
                app.preview_button.invoke()
            elif phase == 1:
                assert app.previews[0].result.status == Status.SUCCESS
                assert not app.workflow.output_root.exists()
                app.process_button.invoke()
            elif phase == 2:
                assert app.results[0].result.status == Status.SUCCESS
                state["first_artifact"] = app.results[0].result.output_location
                app.show_page("Process Reports")
                app.preview_button.invoke()
            elif phase == 3:
                assert app.previews[0].result.status == Status.SKIPPED
                app.process_button.invoke()
            elif phase == 4:
                assert app.results[0].result.status == Status.SKIPPED
                source.write_bytes(source.read_bytes().replace(b"$10.00", b"$20.00"))
                app.set_files([str(source)])
                app.month_confirmed.set(True)
                app.preview_button.invoke()
            elif phase == 5:
                assert app.previews[0].result.status == Status.NEEDS_REVIEW
                assert app.process_button.cget("state") == "disabled"
                app.review_button.invoke()
                app.update_idletasks()
                assert app.dialog.confirm_button.cget("state") == "disabled"
                app.dialog.confirmation_check.toggle()
                app.dialog.confirm_button.invoke()
                assert app.can_process()
                app.process_button.invoke()
            elif phase == 6:
                assert app.results[0].result.status == Status.SUCCESS
                assert state["first_artifact"].is_file()
                assert app.results[0].result.output_location != state["first_artifact"]
                app.show_page("History")
            elif phase == 7:
                assert len(app.history_entries) == 2
                assert sum(entry.is_current for entry in app.history_entries) == 1
                app.report_buttons[2].invoke()
                app.sample_button.invoke()
                app.month_confirmed.set(True)
                app.preview_button.invoke()
            elif phase == 8:
                assert app.previews[0].result.code == "ready_to_process"
                assert app.previews[0].result.output_rows == 3
                app.process_button.invoke()
            elif phase == 9:
                assert app.results[0].result.status == Status.SUCCESS
                assert app.results[0].result.output_rows == 3
                app.format_selector.set("Power BI CSV candidate")
                app._output_format_changed()
                app.show_page("Process Reports")
                app.month_confirmed.set(True)
                app.preview_button.invoke()
            elif phase == 10:
                assert app.previews[0].result.code == "ready_to_process"
                assert app.previews[0].result.cleaned.schema[0].name == "WorkOrderId"
                assert "production_publication_blocked" in app.previews[0].result.warnings
                app.process_button.invoke()
            elif phase == 11:
                assert app.results[0].result.status == Status.SUCCESS
                assert app.results[0].result.output_rows == 3
                app.report_buttons[0].invoke()
                app.sample_button.invoke()
                app.month_confirmed.set(True)
                app.preview_button.invoke()
            elif phase == 12:
                assert app.previews[0].result.code == "ready_to_process"
                assert app.previews[0].result.cleaned.schema[0].name == "LegacyRowNumber"
                app.process_button.invoke()
            elif phase == 13:
                assert app.results[0].result.status == Status.SUCCESS
                assert app.results[0].result.output_location.read_text(encoding="utf-8").startswith("LegacyRowNumber,")
                app.report_buttons[1].invoke()
                app.sample_button.invoke()
                app.month_confirmed.set(True)
                app.preview_button.invoke()
            elif phase == 14:
                assert app.previews[0].result.code == "ready_to_process"
                assert app.previews[0].result.cleaned.schema[0].name == "EquipmentId"
                app.process_button.invoke()
            elif phase == 15:
                assert app.results[0].result.status == Status.SUCCESS
                assert len(app.workflow.coordinator.store.history()) == 3
                assert state["first_artifact"].is_file()
                # Route bundled synthetic inputs through the actual monthly UI.
                for kind in ReportType:
                    folder = workspace / "raw" / "2026-01" / kind.value
                    folder.mkdir(parents=True)
                    sample = sample_path(kind)
                    raw = sample.read_bytes()
                    if sample.suffix == ".csv":
                        raw = raw.replace(b"2026-09", b"2026-01")
                    (folder / sample.name).write_bytes(raw)
                config = workspace / "workspace.toml"
                config.write_text('raw_folder="raw"\ncandidate_folder="monthly-candidates"\napproved_folder="approved"\n', encoding="utf-8")
                from tkinter import filedialog
                original_picker = filedialog.askopenfilename
                try:
                    filedialog.askopenfilename = lambda **kwargs: str(config)
                    app.workspace_button.invoke()
                finally:
                    filedialog.askopenfilename = original_picker
                assert app.workflow.output_format == "powerbi"
                app.month.set("January")
                app.scan_button.invoke()
            elif phase == 16:
                assert len(app.sources) == 3 and not app.monthly_selection.missing
                assert not app.workflow.output_root.exists()
                app.month_confirmed.set(True)
                app.preview_button.invoke()
            elif phase == 17:
                assert len(app.previews) == 3 and app.can_process()
                assert not app.workflow.output_root.exists()
                app.process_button.invoke()
            elif phase == 18:
                assert len(app.results) == 3 and all(e.result.status == Status.SUCCESS for e in app.results)
                app.packet_button.invoke()
            elif phase == 19:
                packets = tuple((app.workspace.candidate_folder / "review_packets").iterdir())
                assert len(packets) == 1
                packet = json.loads((packets[0] / "packet.json").read_text(encoding="utf-8"))
                assert packet["status"] == "CandidateUnverified" and packet["production_ready"] is False
                assert packet["sync_verified"] is False and len(packet["files"]) == 3
                assert not app.workspace.approved_folder.exists()
                assert "Candidate review packet saved" in app.status.get()
                finish(True)
                return
            state["phase"] += 1
            app.after(50, advance)
        except Exception:
            finish(False)

    app.after(100, advance)
    app.mainloop()
    return 0 if state["status"] == "passed" else 1
