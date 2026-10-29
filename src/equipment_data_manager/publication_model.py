"""IN-MEMORY SPECIFICATION MODEL ONLY. No filesystem, HTTP, Graph or real approvals.

Mock grants model a future independently verified authority. These grants cannot
approve review requests; the desktop never constructs or calls this model.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from threading import RLock
from uuid import uuid4

from equipment_data_manager.processing.models import ProcessingError
from equipment_data_manager.review import digest


@dataclass(frozen=True)
class SandboxSnapshot:
    selection_fingerprint: str
    files: tuple[tuple[str, bytes], ...]

    @property
    def identity(self):
        names = [name for name, _ in self.files]
        required = {'repairs.csv', 'repair_financial_summary.csv', 'service_orders.csv', 'tma_work_orders.csv'}
        if set(names) != required or len(names) != 4:
            raise ProcessingError('model_incomplete_snapshot')
        return digest(dict(selection=self.selection_fingerprint,
            files=sorted((name, sha256(raw).hexdigest()) for name, raw in self.files)))


class MockReviewerAuthority:
    """Synthetic allowlist and grant ledger, NOT organizational authentication."""
    def __init__(self, authorized_reviewers=()):
        self.reviewers = frozenset(authorized_reviewers)
        self.grants = {}

    def issue(self, reviewer, snapshot, *, operation='publish', generation=None):
        if reviewer not in self.reviewers:
            raise ProcessingError('model_unauthorized_reviewer')
        grant = uuid4().hex
        self.grants[grant] = dict(reviewer=reviewer, snapshot=snapshot.identity, operation=operation,
            generation=generation, verified_at=datetime.now(timezone.utc).isoformat())
        return grant

    def verify(self, grant, snapshot, operation, generation=None):
        record = self.grants.get(grant)
        if (record is None or record['reviewer'] not in self.reviewers or record['snapshot'] != snapshot.identity
                or record['operation'] != operation or record['generation'] != generation):
            raise ProcessingError('model_missing_or_stale_approval')
        return record.copy()


class MemoryPublicationModel:
    """Executable protocol design. State vanishes on exit; never a real publisher.

    In-memory locking/CAS simulate a future shared server lease/conditional pointer.
    They provide no coordination or durability across machines. Uploaded bytes are
    retained only in dictionaries. No path or storage-provider argument exists.
    """
    def __init__(self, authority):
        self.authority = authority
        self.staging, self.published = {}, {}
        self.current, self.generation = None, 0
        self.events = []
        self.lock = RLock()

    def stage(self, snapshot, grant, *, current_selection, transfer=None):
        self.authority.verify(grant, snapshot, 'publish')
        if current_selection() != snapshot.selection_fingerprint:
            raise ProcessingError('model_candidate_changed')
        identity = snapshot.identity
        with self.lock:
            staged = self.staging.setdefault(identity, {})
        for name, raw in snapshot.files:
            received = raw if transfer is None else transfer(name, raw)
            if received != raw:
                raise ProcessingError('model_transfer_integrity_failed')
            with self.lock:
                if name in staged and staged[name] != raw:
                    raise ProcessingError('model_staging_conflict')
                staged[name] = received
        return identity

    def select(self, snapshot, grant, *, expected_generation, current_selection):
        # Hold the model lock across final revalidation/selection; actual service
        # needs shared locking plus a server-enforced ETag/lease, not this RLock.
        with self.lock:
            evidence = self.authority.verify(grant, snapshot, 'publish')
            if current_selection() != snapshot.selection_fingerprint:
                raise ProcessingError('model_candidate_changed')
            identity = snapshot.identity
            if self.current == identity:
                return 'already_selected'
            if expected_generation != self.generation:
                raise ProcessingError('model_selection_conflict')
            expected = dict(snapshot.files)
            if self.staging.get(identity) != expected:
                raise ProcessingError('model_partial_snapshot')
            # Immutable tuple copy; staging mutations cannot change a published set.
            existing = self.published.get(identity)
            if existing is not None and existing != snapshot:
                raise ProcessingError('model_immutable_conflict')
            self.published[identity] = snapshot
            previous = self.current
            self.current, self.generation = identity, self.generation + 1
            self.events.append(dict(action='select', previous=previous, current=identity,
                generation=self.generation, approval=evidence))
            return 'selected'

    def rollback(self, target, grant, *, expected_generation):
        with self.lock:
            if target not in self.published:
                raise ProcessingError('model_rollback_target_unavailable')
            snapshot = self.published[target]
            evidence = self.authority.verify(grant, snapshot, 'rollback', expected_generation)
            if expected_generation != self.generation:
                raise ProcessingError('model_selection_conflict')
            previous = self.current
            self.current, self.generation = target, self.generation + 1
            self.events.append(dict(action='rollback', previous=previous, current=target,
                generation=self.generation, approval=evidence))
            return 'selected_previous_snapshot'
