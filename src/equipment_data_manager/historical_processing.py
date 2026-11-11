"""Confirmed local candidate orchestration; no cleaner, approval or publisher.

Plans/results retain safe aggregates and identities, never original report cells.
A fresh plan is required after restart. Durable recovery is the existing manifest.
"""
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
import csv
from io import StringIO
import json
import os
from pathlib import Path
from threading import Event, Lock
from weakref import WeakValueDictionary

from equipment_data_manager.historical import is_temporary_filename, verify_inventory_source, periods_between
from equipment_data_manager.historical_preview import ReportPreview, _summarize, diagnostic_target, write_diagnostic
from equipment_data_manager.processing.models import ProcessingError, ProcessingRequest, ReportType
from equipment_data_manager.processing.manifest import OUTPUT_NAMES
from equipment_data_manager.processing.repair_financial import powerbi_coordinator, summary_name
from equipment_data_manager.settings import candidate_location_error, FOLDER_LAYOUTS
from equipment_data_manager.storage.contracts import StorageFile
from equipment_data_manager.storage.local import LocalFolderStorage

ACTIONS = {'create': 'Create local candidate', 'skip': 'Skip — already processed',
    'correction': 'Correction review required — use single-report workflow', 'blocked': 'Blocked — preview again'}
RESULTS = {'created': 'Candidate created — unapproved', 'skipped': 'Already processed',
    'correction': 'Correction review required', 'blocked': 'Blocked — fresh discovery/preview required',
    'failed': 'Processing failed', 'not_started': 'Not started — stopped safely'}
_LOCKS = WeakValueDictionary()
_LOCK_GUARD = Lock()


def _lock_for(root):
    key = os.path.normcase(os.path.abspath(root))
    with _LOCK_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = Lock(); _LOCKS[key] = lock
        return lock


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def _configuration(workspace, layout):
    if layout not in FOLDER_LAYOUTS:
        raise ProcessingError('historical_invalid_layout')
    workspace.validate()
    root = Path(workspace.candidate_folder).absolute()
    for path in (root, root / 'powerbi_candidates', root / 'powerbi_candidates/versions',
                 root / 'powerbi_candidates/manifest.sqlite3'):
        if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)) or candidate_location_error(path):
            raise ProcessingError('batch_untrusted_candidate_location')
    return _digest(dict(layout=layout, roots=[str(p.resolve()) for p in
        (workspace.raw_folder, workspace.candidate_folder, workspace.approved_folder)]))


def _engine(workspace, coordinator):
    engine = coordinator or powerbi_coordinator(workspace.candidate_folder)
    if engine.store.root != (workspace.candidate_folder.resolve() / 'powerbi_candidates').resolve():
        raise ProcessingError('batch_configuration_changed')
    return engine


def _identity(source):
    if source is None:
        return None
    return dict(provider=source.provider, container_sha256=sha256(source.container.encode()).hexdigest(),
        parent_id=source.parent_id, item_id=source.item_id, name=source.name,
        version=source.version, size_bytes=source.size_bytes, sha256=source.sha256)


@dataclass(frozen=True)
class PlanItem:
    month: str
    report_type: str
    action: str
    code: str
    source: StorageFile | None
    preview: ReportPreview

    def document(self):
        return dict(month=self.month, report_type=self.report_type, action=self.action, code=self.code,
                    source=_identity(self.source), preview=self.preview.document())


@dataclass(frozen=True)
class ProcessingPlan:
    configuration_sha256: str
    created_at: str
    items: tuple[PlanItem, ...]
    stopped: bool = False

    @property
    def fingerprint(self):
        return _digest(dict(configuration=self.configuration_sha256, created_at=self.created_at,
                            items=[item.document() for item in self.items], stopped=self.stopped))

    def document(self):
        return dict(version=1, purpose='LocalUnapprovedCandidatePlan', fingerprint=self.fingerprint,
            configuration_sha256=self.configuration_sha256, created_at=self.created_at,
            stopped=self.stopped, items=[item.document() for item in self.items])


def make_plan(workspace, layout, inventory, batch, selected, *, coordinator=None,
              progress=None, on_start=None, cancelled=None):
    """Review current history against exact successful in-memory preview evidence."""
    configuration = _configuration(workspace, layout)
    if batch.candidate_root_sha256 != sha256(str(workspace.candidate_folder.resolve()).encode()).hexdigest():
        raise ProcessingError('batch_configuration_changed')
    if (inventory.stopped or inventory.root != str(workspace.raw_folder.resolve()) or
            inventory.layout != layout or (batch.start, batch.end, batch.layout) !=
            (inventory.start, inventory.end, layout)):
        raise ProcessingError('batch_configuration_changed')
    periods_between(batch.start, batch.end)
    try:
        keys = tuple((period, ReportType(kind).value) for period, kind in selected)
    except (TypeError, ValueError):
        raise ProcessingError('batch_invalid_selection') from None
    if not keys or len(set(keys)) != len(keys):
        raise ProcessingError('batch_invalid_selection')
    previous = {(r.month, r.report_type): r for r in batch.reports}
    discovered = {(m.period, r.report_type.value): r for m in inventory.months for r in m.reports}
    if any(key not in previous or key not in discovered for key in keys):
        raise ProcessingError('batch_invalid_selection')
    engine = _engine(workspace, coordinator)
    stop = cancelled if cancelled is not None else Event()
    items = []
    for index, key in enumerate(sorted(keys)):
        period, kind = key
        old, report = previous[key], discovered[key]
        source = report.sources[0] if len(report.sources) == 1 else None
        item = PlanItem(period, kind, 'blocked', old.code if old.status in ('failed','missing','unsupported','stale') else 'batch_preview_required', source, old)
        if stop.is_set():
            item = replace(item, code='batch_plan_stopped')
        elif old.status in ('previewed', 'warnings') and source and report.status == 'found':
            if on_start: on_start(period, kind)
            try:
                if (old.source_sha256 != source.sha256 or old.source_version != source.version or
                        old.source_filename != source.name or is_temporary_filename(source.name)):
                    raise ProcessingError('batch_preview_changed')
                read = verify_inventory_source(LocalFolderStorage(workspace.raw_folder, synced=source.provider == 'synced-local'), source)
                result = engine.preview(ProcessingRequest(kind, period, raw_bytes=read.content,
                    source_name=source.name), include_details=True)
                current = _summarize(result, period, ReportType(kind), source, read.integrity)
                if result.status == 'failure':
                    item = replace(item, code=result.code, preview=replace(old, status=current.status, code=result.code, failure_scope=current.failure_scope))
                elif (not old.proposed_output_sha256 or old.proposed_output_sha256 != current.proposed_output_sha256
                      or old.cleaner_version != current.cleaner_version):
                    item = replace(item, code='batch_preview_changed', preview=current)
                else:
                    action = ('correction' if result.status == 'needs_review' or
                        (current.existing_revision and current.existing_output_sha256 != current.proposed_output_sha256)
                        else 'skip' if result.status == 'skipped' else 'create')
                    item = replace(item, action=action, code='batch_correction_required' if action == 'correction' else result.code,
                                   preview=current)
            except ProcessingError as exc:
                item = replace(item, code=str(exc))
            except OSError:
                item = replace(item, code='file_or_storage_unavailable')
            except Exception:
                item = replace(item, code='processing_failed')
            finally:
                read = result = None
        items.append(item)
        if progress: progress(index + 1, len(keys))
    return ProcessingPlan(configuration, datetime.now(timezone.utc).isoformat(), tuple(items), stop.is_set())


@dataclass(frozen=True)
class BatchItemResult:
    month: str
    report_type: str
    status: str
    code: str
    source: StorageFile | None
    evidence: ReportPreview
    revision: str | None = None
    output_sha256: str = ''
    output_location: str = ''
    integrity: str = 'not_rechecked'

    def document(self):
        return dict(month=self.month, report_type=self.report_type, status=self.status, code=self.code,
            source=_identity(self.source), evidence=self.evidence.document(), revision=self.revision,
            output_sha256=self.output_sha256, output_location=self.output_location, integrity=self.integrity)


@dataclass(frozen=True)
class ProcessingRun:
    plan_fingerprint: str
    started_at: str
    finished_at: str
    items: tuple[BatchItemResult, ...]
    stopped: bool

    @property
    def summary(self):
        counts = Counter(item.status for item in self.items)
        retained = {kind.value: sum((item.evidence.retained_records or 0) for item in self.items
                    if item.report_type == kind.value and item.status in ('created', 'skipped')) for kind in ReportType}
        return dict(selected=len(self.items), **{key: counts[key] for key in RESULTS},
                    retained_committed_or_unchanged=retained)

    def document(self):
        return dict(version=1, purpose='NonproductionCandidateProcessingDiagnostic',
            approval='not_granted', publication='disabled', sync_verified=False,
            plan_fingerprint=self.plan_fingerprint, started_at=self.started_at, finished_at=self.finished_at,
            stopped=self.stopped, summary=self.summary, items=[item.document() for item in self.items])


def _check_candidate_paths(root, kind, period, *, windows=None):
    if not (os.name == 'nt' if windows is None else windows):
        return
    revision = Path(root) / 'versions' / ('0' * 32)
    paths = [revision / f'{OUTPUT_NAMES[kind]}_{period}.csv', revision / 'candidate.tmp']
    if kind == ReportType.REPAIRS:
        paths += [revision / summary_name(period), revision / (summary_name(period) + '.part')]
    if any(len(str(p.absolute()).encode('utf-16-le')) // 2 >= 260 or
           len(str(p.parent.absolute()).encode('utf-16-le')) // 2 >= 248 for p in paths):
        raise ProcessingError('batch_candidate_path_too_long')


def execute_plan(workspace, layout, plan, confirmation, *, coordinator=None,
                 progress=None, on_start=None, on_result=None, cancelled=None):
    """One ordinary guarded coordinator commit at a time; no correction tokens.

    The Python lock rejects overlapping in-process batches. The existing SQLite
    transaction plus expected-current guard handles other processes on this machine.
    """
    if not isinstance(confirmation, str) or confirmation != plan.fingerprint or plan.stopped:
        raise ProcessingError('batch_confirmation_required')
    if _configuration(workspace, layout) != plan.configuration_sha256:
        raise ProcessingError('batch_configuration_changed')
    lock = _lock_for(workspace.candidate_folder)
    if not lock.acquire(blocking=False):
        raise ProcessingError('batch_already_running')
    try:
        return _execute(workspace, layout, plan, coordinator, progress, on_start, on_result, cancelled)
    finally:
        lock.release()


def _execute(workspace, layout, plan, coordinator, progress, on_start, on_result, cancelled):
    engine = _engine(workspace, coordinator)
    stop = cancelled if cancelled is not None else Event()
    started = datetime.now(timezone.utc).isoformat()
    results = []
    for index, item in enumerate(plan.items):
        outcome = BatchItemResult(item.month, item.report_type, 'not_started', 'cancelled', item.source, item.preview)
        if not stop.is_set():
            if on_start: on_start(item.month, item.report_type)
            if item.action not in ('create', 'skip'):
                outcome = replace(outcome, status='correction' if item.action == 'correction' else 'blocked', code=item.code)
            else:
                try:
                    if _configuration(workspace, layout) != plan.configuration_sha256:
                        raise ProcessingError('batch_configuration_changed')
                    if item.source is None or is_temporary_filename(item.source.name):
                        raise ProcessingError('batch_preview_required')
                    read = verify_inventory_source(LocalFolderStorage(workspace.raw_folder, synced=item.source.provider == 'synced-local'), item.source)
                    if read.sha256 != item.preview.source_sha256:
                        raise ProcessingError('batch_preview_changed')
                    if item.action == 'create':
                        _check_candidate_paths(engine.store.root, ReportType(item.report_type), item.month)
                    result = engine.process_guarded(ProcessingRequest(item.report_type, item.month,
                        raw_bytes=read.content, source_name=item.source.name),
                        expected_revision=item.preview.existing_revision,
                        expected_output_hash=item.preview.proposed_output_sha256,
                        expected_cleaner_version=item.preview.cleaner_version)
                    evidence = _summarize(result, item.month, ReportType(item.report_type), item.source, read.integrity)
                    if result.cleaned is None:
                        evidence = replace(item.preview, status=evidence.status, code=result.code, failure_scope=evidence.failure_scope)
                    status = ('created' if result.status == 'success' else 'skipped' if result.status == 'skipped'
                              else 'correction' if result.status == 'needs_review' or result.code == 'batch_correction_required'
                              else 'failed' if result.code in ('file_or_storage_unavailable','manifest_unavailable','processing_failed') else 'blocked')
                    artifact = result.artifact
                    outcome = replace(outcome, status=status, code=result.code, evidence=evidence,
                        revision=artifact.revision_id if artifact else None, output_sha256=artifact.output_hash if artifact else '',
                        output_location=str(artifact.output_path) if artifact else '', integrity=read.integrity)
                except ProcessingError as exc:
                    outcome = replace(outcome, status='blocked', code=str(exc))
                except OSError:
                    outcome = replace(outcome, status='failed', code='file_or_storage_unavailable')
                except Exception:
                    outcome = replace(outcome, status='failed', code='processing_failed')
                finally:
                    read = result = None
        results.append(outcome)
        if on_result: on_result(outcome)
        if progress: progress(index + 1, len(plan.items))
    return ProcessingRun(plan.fingerprint, started, datetime.now(timezone.utc).isoformat(), tuple(results), stop.is_set())


PROCESSING_COLUMNS = ('Purpose', 'Month', 'ReportType', 'SourceFilename', 'SourceItemId', 'SourceVersion',
    'SourceSHA256', 'Status', 'ReasonCode', 'CandidateRevision', 'OutputSHA256', 'OutputLocation',
    'RetainedRecords', 'WarningCodes', 'FinancialSummary', 'Integrity')


def export_processing(run, target, *, protected_roots):
    path = diagnostic_target(target, protected_roots=protected_roots)
    if path.suffix.lower() == '.json':
        raw = json.dumps(run.document(), indent=2)
    else:
        stream = StringIO(newline=''); writer = csv.writer(stream); writer.writerow(PROCESSING_COLUMNS)
        for item in run.items:
            source = item.source
            values = ('NonproductionCandidateProcessingDiagnostic', item.month, item.report_type,
                source.name if source else '', source.item_id if source else '', source.version if source else '',
                source.sha256 if source else '', RESULTS[item.status], item.code, item.revision,
                item.output_sha256, item.output_location, item.evidence.retained_records,
                '; '.join(item.evidence.warnings), json.dumps(dict(item.evidence.financial)), item.integrity)
            writer.writerow("'" + value if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r')) else value for value in values)
        raw = stream.getvalue()
    return write_diagnostic(path, (raw + '\n').encode('utf-8-sig'))
