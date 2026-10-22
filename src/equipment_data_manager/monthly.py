"""Offline monthly discovery and immutable review packets, never publication."""

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tomllib
from uuid import uuid4

from equipment_data_manager.processing.cleaners import validate_period
from equipment_data_manager.processing.manifest import OUTPUT_NAMES
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.ui.workflow import SourceFile, SUPPORTED_REPORTS


@dataclass(frozen=True)
class Workspace:
    raw_folder: Path
    candidate_folder: Path
    approved_folder: Path

    def validate(self):
        paths = [p.resolve() for p in (self.raw_folder, self.candidate_folder, self.approved_folder)]
        if any(a.is_relative_to(b) or b.is_relative_to(a)
               for i, a in enumerate(paths) for b in paths[i + 1:]):
            raise ProcessingError("workspace_folders_overlap")
        return self


def load_workspace(path: Path) -> Workspace:
    """Relative paths resolve against TOML location, never a developer's home."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        keys = {"raw_folder", "candidate_folder", "approved_folder"}
        if set(data) != keys or any(not isinstance(v, str) or not v.strip() for v in data.values()):
            raise ValueError
        return Workspace(**{k: (path.resolve().parent / v).resolve() for k, v in data.items()}).validate()
    except (OSError, ValueError):
        raise ProcessingError("invalid_workspace_configuration") from None


@dataclass(frozen=True)
class MonthlySelection:
    period: str
    files: tuple[tuple[ReportType, SourceFile], ...]
    issues: tuple[str, ...]

    @property
    def missing(self):
        present = {kind for kind, _ in self.files}
        return tuple(kind for kind in ReportType if kind not in present)

    @property
    def summary(self):
        missing = ", ".join(SUPPORTED_REPORTS[k] for k in self.missing) or "none"
        return f"Month {self.period} | Missing reports: {missing}. " + " ".join(self.issues)


def discover(workspace: Workspace, period: str) -> MonthlySelection:
    """Read ONLY direct files in raw/YYYY-MM/type; never recurse or guess type."""
    workspace.validate()
    validate_period(period)
    found, issues = [], []
    for kind in ReportType:
        folder = workspace.raw_folder / period / kind.value
        # Do not follow links/junctions outside the configured raw tree.
        if not folder.resolve().is_relative_to(workspace.raw_folder.resolve()):
            issues.append(f"{kind.value}: unsafe linked folder; not scanned.")
            continue
        try:
            entries = sorted(folder.iterdir())
        except FileNotFoundError:
            issues.append(f"{kind.value}: folder missing; check configuration and local availability.")
            continue
        except OSError:
            issues.append(f"{kind.value}: folder unavailable; check permissions/download availability and sync-client errors. Sync is unverified.")
            continue
        for path in entries:
            if path.name.startswith((".", "~")) or path.is_symlink() or not path.is_file():
                continue
            if not path.resolve().is_relative_to(folder.resolve()):
                issues.append(f"{kind.value}: linked file ignored.")
                continue
            allowed = (".xlsx", ".xls") if kind == ReportType.TMA_WORK_ORDERS else (".csv",)
            if path.suffix.lower() in allowed:
                found.append((kind, SourceFile(str(path), path.name)))
    return MonthlySelection(period, tuple(found), tuple(issues))


def export_review_packet(workspace: Workspace, coordinator, period: str) -> Path:
    """Copy one verified CURRENT normalized candidate/type into a new snapshot.

    One consistent SQLite read snapshot; historical files are never discovered.
    The directory becomes visible only after all files and its manifest are ready.
    No approved destination is created or written. Single trusted local operator.
    """
    workspace.validate()
    validate_period(period)
    expected_root = (workspace.candidate_folder / "powerbi_candidates").resolve()
    if coordinator.store.root != expected_root:
        raise ProcessingError("review_packet_requires_powerbi_workspace")
    from equipment_data_manager.powerquery_contract import read_table
    payloads, manifest = {}, []
    with coordinator.store.read_transaction() as connection:
        for kind in ReportType:
            artifact, warnings = coordinator.store.current(connection, kind, period)
            if artifact is None:
                raise ProcessingError("review_packet_missing_reports")
            raw = artifact.output_path.read_bytes()
            if sha256(raw).hexdigest() != artifact.output_hash:
                raise ProcessingError("existing_output_hash_mismatch")
            rows = read_table(raw, kind, allow_candidates=True)
            if len(rows) != artifact.output_rows or any(r["ReportMonth"] != period for r in rows):
                raise ProcessingError("review_packet_contract_mismatch")
            name = f"{OUTPUT_NAMES[kind]}_{period}.csv"
            payloads[kind] = (name, raw)
            manifest.append(dict(report_type=kind.value, period=period, file=f"{kind.value}/{name}",
                revision=artifact.revision_id, sha256=artifact.output_hash, rows=len(rows), warnings=list(warnings)))
    parent = workspace.candidate_folder / "review_packets"
    if not parent.resolve().is_relative_to(workspace.candidate_folder.resolve()):
        raise ProcessingError("unsafe_review_packet_folder")
    parent.mkdir(parents=True, exist_ok=True)
    identifier = uuid4().hex
    staged, final = parent / f".staging-{identifier}", parent / f"{period}-{identifier}"
    staged.mkdir()
    try:
        for kind, (name, raw) in payloads.items():
            (staged / kind.value).mkdir()
            with (staged / kind.value / name).open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        (staged / "packet.json").write_text(json.dumps(dict(status="CandidateUnverified", period=period,
            production_ready=False, sync_verified=False, files=manifest), indent=2) + "\n", encoding="utf-8")
        staged.rename(final)
    except BaseException:
        shutil.rmtree(staged)
        raise
    return final
