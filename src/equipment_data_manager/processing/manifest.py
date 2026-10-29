"""Single-machine manifest with immutable revisions and transactional selection.

Only the active table selects current outputs. Never ingest the versions folder
recursively: it intentionally retains superseded and potentially orphaned files.
"""

from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from equipment_data_manager.processing.interfaces import CleanResult
from equipment_data_manager.processing.models import HistoryEntry, OutputRevision, ProcessingError, ReportType

OUTPUT_NAMES = {
    ReportType.REPAIRS: "CompuClean_RepairReports",
    ReportType.SERVICE_ORDERS: "CompuClean_ServiceOrders",
    ReportType.TMA_WORK_ORDERS: "TMA_WorkOrders",
}


class LocalOutputStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    @contextmanager
    def read_transaction(self):
        """Read a consistent existing manifest without creating/migrating it."""
        path = self.root / "manifest.sqlite3"
        if path.is_symlink():
            raise ProcessingError("unsafe_output_store")
        if not path.exists():
            yield None
            return
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
        try:
            if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ProcessingError("unsupported_manifest_version")
            connection.execute("BEGIN")
            yield connection
        finally:
            connection.close()

    def history(self) -> tuple[HistoryEntry, ...]:
        """Completed revisions, not a log of failed attempts or validation approval."""
        with self.read_transaction() as connection:
            if connection is None:
                return ()
            rows = connection.execute(
                """SELECT r.id, r.report_type, r.period, r.source_hash, r.output_hash,
                          r.cleaner_version, r.input_rows, r.output_rows, r.warnings,
                          a.revision_id IS NOT NULL
                   FROM revisions r LEFT JOIN active a ON a.revision_id = r.id
                   ORDER BY r.rowid DESC"""
            ).fetchall()
            return tuple(
                HistoryEntry(
                    ReportType(row[1]), row[2],
                    OutputRevision(row[0], self.artifact_path(ReportType(row[1]), row[2], row[0]),
                                   row[3], row[4], row[5], row[6], row[7]),
                    bool(row[9]), tuple(json.loads(row[8])),
                ) for row in rows
            )

    @contextmanager
    def transaction(self):
        self.root.mkdir(parents=True, exist_ok=True)
        database_path = self.root / "manifest.sqlite3"
        if database_path.is_symlink():
            raise ProcessingError("unsafe_output_store")
        connection = sqlite3.connect(database_path, timeout=5)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            if connection.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
                raise ProcessingError("unsupported_manifest_version")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS revisions (
                    id TEXT PRIMARY KEY, report_type TEXT NOT NULL, period TEXT NOT NULL,
                    source_hash TEXT NOT NULL, output_hash TEXT NOT NULL,
                    cleaner_version TEXT NOT NULL, input_rows INTEGER NOT NULL,
                    output_rows INTEGER NOT NULL, warnings TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS active (
                    report_type TEXT NOT NULL, period TEXT NOT NULL,
                    revision_id TEXT NOT NULL REFERENCES revisions(id),
                    PRIMARY KEY (report_type, period)
                );
                PRAGMA user_version = 1;
            """)
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        finally:
            if connection.in_transaction:
                connection.rollback()
            connection.close()

    def artifact_path(self, report_type: ReportType, period: str, revision_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", revision_id):
            raise ProcessingError("invalid_manifest_revision")
        path = self.root / "versions" / revision_id / f"{OUTPUT_NAMES[report_type]}_{period}.csv"
        if not path.resolve().is_relative_to(self.root):
            raise ProcessingError("unsafe_output_store")
        return path

    def current(self, connection, report_type: ReportType, period: str):
        if connection is None:
            return None, ()
        row = connection.execute(
            """SELECT r.id, r.source_hash, r.output_hash, r.cleaner_version,
                      r.input_rows, r.output_rows, r.warnings
               FROM active a JOIN revisions r ON r.id = a.revision_id
               WHERE a.report_type = ? AND a.period = ?""",
            (report_type.value, period),
        ).fetchone()
        if row is None:
            return None, ()
        artifact = OutputRevision(
            row[0], self.artifact_path(report_type, period, row[0]),
            row[1], row[2], row[3], row[4], row[5],
        )
        try:
            actual_hash = sha256(artifact.output_path.read_bytes()).hexdigest()
        except OSError:
            raise ProcessingError("existing_output_missing_or_unreadable") from None
        if actual_hash != artifact.output_hash:
            raise ProcessingError("existing_output_hash_mismatch")
        return artifact, tuple(json.loads(row[6]))

    def write_revision(self, report_type: ReportType, period: str, source_hash: str,
                       cleaned: CleanResult) -> OutputRevision:
        revision_id = uuid4().hex
        final = self.artifact_path(report_type, period, revision_id)
        final.parent.mkdir(parents=True, exist_ok=False)
        staged = final.parent / "candidate.tmp"
        try:
            with staged.open("xb") as stream:
                stream.write(cleaned.output_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            # Destination is in a fresh, exclusive revision directory.
            os.replace(staged, final)
        finally:
            staged.unlink(missing_ok=True)
        return OutputRevision(
            revision_id, final, source_hash, sha256(cleaned.output_bytes).hexdigest(),
            cleaned.cleaner_version, cleaned.input_rows, cleaned.output_rows,
        )

    def select_revision(self, connection, report_type: ReportType, period: str,
                        artifact: OutputRevision, warnings: tuple[str, ...]) -> None:
        connection.execute(
            "INSERT INTO revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (artifact.revision_id, report_type.value, period, artifact.source_hash,
             artifact.output_hash, artifact.cleaner_version, artifact.input_rows,
             artifact.output_rows, json.dumps(warnings)),
        )
        connection.execute(
            """INSERT INTO active VALUES (?, ?, ?) ON CONFLICT(report_type, period)
               DO UPDATE SET revision_id = excluded.revision_id""",
            (report_type.value, period, artifact.revision_id),
        )
