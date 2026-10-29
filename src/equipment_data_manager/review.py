"""Local review requests only: no identity provider, approval or publication authority."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.processing.cleaners import validate_period
from equipment_data_manager.processing.repair_financial import summary_name
from equipment_data_manager.powerquery_contract import read_table
from equipment_data_manager.powerbi_readiness import _same_provenance, _record_contract, _financial_check
from equipment_data_manager.settings import candidate_location_error
from equipment_data_manager.storage.local import read_local_file


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return sha256(encoded(value)).hexdigest()


class ReviewService:
    """Bound to one trusted local candidate store; never edits processing metadata.

    SQLite audit records are locally integrity-checked, NOT authenticated business
    approvals or a tamper-proof enterprise audit. Local clock is not trusted time.
    """
    def __init__(self, coordinator, *, raw_folder=None):
        self.coordinator = coordinator
        self.root = coordinator.store.root / 'review_requests'
        self.raw_folder = None if raw_folder is None else Path(raw_folder).resolve()

    def _path(self):
        if candidate_location_error(self.root) or any(p.is_symlink() or p.is_junction() for p in (self.root, *self.root.parents)):
            raise ProcessingError('review_store_unsafe')
        path = self.root / 'requests.sqlite3'
        if path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()):
            raise ProcessingError('review_store_unsafe')
        return path

    def capture(self, period):
        validate_period(period)
        files, reports, missing = [], {}, []
        with self.coordinator.store.read_transaction() as connection:
            for kind in ReportType:
                artifact, warnings = self.coordinator.store.current(connection, kind, period)
                if artifact is None:
                    missing.append(kind.value)
                    continue
                raw = read_local_file(artifact.output_path, expected_sha256=artifact.output_hash).content
                rows = read_table(raw, kind, allow_candidates=True)
                if not rows or len(rows) != artifact.output_rows or any(r['ReportMonth'] != period for r in rows):
                    raise ProcessingError('review_candidate_contract_rejected')
                _same_provenance(rows, kind)
                if kind == ReportType.REPAIRS and any(r['SchemaVersion'] != '2' for r in rows):
                    raise ProcessingError('review_requires_repair_v2')
                _record_contract(rows, kind)
                first = rows[0]
                if first['SourceFileSHA256'] != artifact.source_hash or f"{first['ExportVersion']}:{first['CleanerVersion']}" != artifact.cleaner_version:
                    raise ProcessingError('review_candidate_provenance_rejected')
                source_check = 'original_bytes_not_rechecked'
                if self.raw_folder is not None:
                    folder = self.raw_folder / period / kind.value
                    source = folder / first['SourceFileName']
                    if not source.resolve().is_relative_to(self.raw_folder) or source.is_symlink():
                        raise ProcessingError('review_source_unsafe')
                    try:
                        read_local_file(source, expected_sha256=artifact.source_hash)
                        source_check = 'local_original_bytes_match'
                    except ProcessingError as exc:
                        # Missing/hydration errors are visible evidence gaps; changed
                        # original bytes invalidate the selected candidate for review.
                        if str(exc) == 'storage_source_hash_mismatch':
                            raise ProcessingError('review_source_changed') from None
                        source_check = 'original_unavailable:' + str(exc)
                selected = dict(report_type=kind.value, revision=artifact.revision_id,
                    source_sha256=artifact.source_hash, output_sha256=artifact.output_hash,
                    schema_version=first['SchemaVersion'], cleaner_version=artifact.cleaner_version,
                    source_check=source_check)
                files.append(selected)
                reports[kind.value] = dict(input_rows=artifact.input_rows, retained_rows=len(rows),
                    warnings=list(warnings), missing_values={key: sum(r[key] is None or r[key] == '' for r in rows)
                        for key in rows[0] if any(r[key] is None or r[key] == '' for r in rows)})
                if kind == ReportType.REPAIRS:
                    expected = {r['FinancialSummarySHA256'] for r in rows}
                    if len(expected) != 1:
                        raise ProcessingError('review_summary_reference_rejected')
                    summary_bytes = read_local_file(artifact.output_path.parent / summary_name(period),
                        expected_sha256=next(iter(expected))).content
                    summary_rows = read_table(summary_bytes, kind, allow_candidates=True, financial_summary=True)
                    if len(summary_rows) != 1:
                        raise ProcessingError('review_summary_reference_rejected')
                    summary = summary_rows[0]
                    state = _financial_check(rows, summary)
                    selected['summary_sha256'] = sha256(summary_bytes).hexdigest()
                    reports[kind.value]['financial_summary'] = {key: None if summary[key] is None else str(summary[key])
                        for key in ('ReportedLaborCost', 'ReportedPartsCost', 'ReportedTotalCost',
                            'ReportedRepairCount', 'KnownRepairTotalCost', 'UnavailableRepairCostCount',
                            'RepairTotalDifference', 'SummaryComponentsDifference')}
                    reports[kind.value]['financial_reconciliation'] = state
        evidence = dict(period=period, selected=files, reports=reports, missing_reports=missing,
            candidate_status='CandidateUnverified', approval='unavailable_authority_not_configured',
            publication='disabled', sync_verified=False)
        return dict(evidence=evidence, fingerprint=digest(evidence))

    def request(self, period, expected_fingerprint, evidence_note):
        if not isinstance(evidence_note, str) or not evidence_note.strip() or len(evidence_note) > 4000:
            raise ProcessingError('review_evidence_required')
        captured = self.capture(period)
        if captured['evidence']['missing_reports']:
            raise ProcessingError('review_missing_reports')
        if captured['fingerprint'] != expected_fingerprint:
            raise ProcessingError('review_selection_changed')
        body = dict(**captured, record_version=1, evidence_note=evidence_note.strip(),
            note_authority='unverified_submitter_statement', status='ReviewRequestedLocallyNotSent',
            approval=None, requester_identity='not_verified', reviewer_identity=None)
        # Duplicate requests from simultaneous local operations return one record.
        key = digest(body)
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path, timeout=5) as db:
            db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, dedup TEXT UNIQUE NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL)')
            db.execute("CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON requests BEGIN SELECT RAISE(ABORT, 'append only'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON requests BEGIN SELECT RAISE(ABORT, 'append only'); END")
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT id, body, hash FROM requests WHERE dedup=?', (key,)).fetchone()
            if existing:
                return self._verified(existing)
            body.update(request_id=uuid4().hex, requested_at=datetime.now(timezone.utc).isoformat())
            db.execute('INSERT INTO requests VALUES (?,?,?,?)', (body['request_id'], key, encoded(body).decode(), digest(body)))
        return body

    @staticmethod
    def _verified(row):
        try:
            body = json.loads(row[1])
            if (body['record_version'] != 1 or digest(body) != row[2] or body['request_id'] != row[0]
                    or body['status'] != 'ReviewRequestedLocallyNotSent' or body['approval'] is not None
                    or body['reviewer_identity'] is not None
                    or digest(body['evidence']) != body['fingerprint']):
                raise ValueError
            return body
        except (ValueError, KeyError, TypeError):
            raise ProcessingError('review_audit_integrity_failed') from None

    def history(self):
        path = self._path()
        if not path.exists():
            return []
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=5) as db:
            return [self._verified(row) for row in db.execute('SELECT id,body,hash FROM requests ORDER BY rowid DESC')]

    def status(self, record):
        # Validate even a caller-supplied record; never trust an Approved checkbox.
        if record.get('approval') is not None or record.get('reviewer_identity') is not None:
            raise ProcessingError('review_unauthorized_reviewer')
        try:
            current = self.capture(record['evidence']['period'])
        except ProcessingError:
            return 'StaleOrUnavailable'
        return 'ReviewRequestedLocallyNotSent' if current['fingerprint'] == record['fingerprint'] else 'StaleSelectionChanged'

    def approve(self, *args, **kwargs):
        raise ProcessingError('review_approval_unavailable')

    def publish(self, *args, **kwargs):
        raise ProcessingError('review_publication_disabled')
