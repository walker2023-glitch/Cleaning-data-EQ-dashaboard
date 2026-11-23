"""Session-only hybrid planning over existing immutable canonical snapshots.

No new persisted contract, cleaner, candidate writer or active-output authority.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from threading import Event

from equipment_data_manager.historical import discover_history, periods_between
from equipment_data_manager.historical_dataset import (
    DatasetPlan, Selection, NAMES, _digest, _safe, _destination, _store,
    preview_dataset, generate_dataset, validate_dataset,
)
from equipment_data_manager.processing.models import ProcessingError
from equipment_data_manager.storage.local import LocalFolderStorage, _stat, _version
from equipment_data_manager.storage.contracts import StorageError

ADD = 'Add New Months'
REBUILD = 'Rebuild History'
UNCHANGED = 'No Update Needed'
REVIEW = 'Review Required'


@dataclass(frozen=True)
class UpdatePlan:
    dataset: DatasetPlan | None
    layout: str
    baseline: str | None
    baseline_digest: str
    baseline_range: tuple[str, ...]
    baseline_counts: tuple[tuple[str, str, int], ...]
    destination: str
    recommendation: str
    permitted: tuple[str, ...]
    added: tuple[str, ...]
    unchanged: tuple[str, ...]
    removed: tuple[str, ...]
    replacements: tuple[tuple[str, str, str, str], ...]
    issues: tuple[str, ...]
    sources: tuple[tuple[str, ...], ...]

    @property
    def fingerprint(self):
        return _digest(asdict(self))

    def confirmation(self, mode):
        return _digest([self.fingerprint, mode])

    @property
    def changes_history(self):
        return bool(self.removed or self.replacements)

    def summary(self):
        dataset = self.dataset
        lines = [self.recommendation,
            'Baseline: '+(' through '.join(self.baseline_range) if self.baseline else 'None — initial historical build'),
            'Proposed: '+(f'{dataset.start} through {dataset.end}' if dataset else 'Unavailable'),
            'Reports: Repairs, Service Orders, TMA; one repair financial summary per month.',
            'New months: '+(', '.join(self.added) or 'None'),
            'Unchanged months: '+(', '.join(self.unchanged) or 'None'),
            'Excluded / removed baseline months: '+(', '.join(self.removed) or 'None'),
            'Destination: '+self.destination]
        lines += [f'Replace {m} {k}: {old} → {new}' for m,k,old,new in self.replacements]
        lines += ['Review required: '+issue for issue in self.issues]
        previous={(m,k):n for m,k,n in self.baseline_counts}
        lines += [f'Excluded {m} {k}: previously {n} records' for m,k,n in self.baseline_counts if m in self.removed]
        if dataset:
            for s in dataset.selections:
                before=previous.get((s.month,s.report_type),'not included')
                lines.append(f'{s.month} {s.report_type}: previous records {before}; proposed records {s.rows if s.rows is not None else "not assessed"}')
                lines.append(f'{s.month} {s.report_type}: {s.status}; records {s.rows if s.rows is not None else "not assessed"}; missing costs {s.unavailable_costs}; missing assignments {s.missing_assignments}; missing IDs {s.missing_identifiers}')
                lines += [f'Warning ({s.month} {s.report_type}): {w}' for w in s.warnings]
        lines.append('Local unapproved output only. No activation, publication or Power BI refresh.')
        return '\n'.join(lines)


def _baseline(path, configuration):
    root = _safe(path, local=True)
    if root.name != 'snapshot':
        raise ProcessingError('monthly_baseline_completed_folder_required')
    manifest = validate_dataset(root)
    old = DatasetPlan(manifest['start'], manifest['end'], manifest['configuration'],
        tuple(Selection(**dict(s, warnings=tuple(s['warnings']))) for s in manifest['selections']), manifest['stopped'])
    if old.configuration != configuration or old.fingerprint != manifest['plan_sha256'] or not old.ready:
        raise ProcessingError('monthly_baseline_binding_invalid')
    # Bind all six exact files, including completion evidence, rather than folder dates.
    digest = _digest([(n,sha256(_safe(root/n).read_bytes()).hexdigest())
        for n in (*NAMES.values(),'snapshot_manifest.json','compatibility_report.md')])
    return old, digest


def preview_update(workspace, start, end, layout, destination, *, baseline=None,
                   progress=lambda *_: None, cancelled=None):
    stop = cancelled if cancelled is not None else Event()
    issues=[]; dataset=None; old=None; digest=''; sources=[]
    added=unchanged=removed=(); replacements=()
    destination=str(Path(destination).absolute())
    baseline=str(Path(baseline).absolute()) if baseline is not None else None
    try:
        _destination(workspace,destination)
        if Path(destination).exists():raise ProcessingError('dataset_destination_exists')
        if baseline and (Path(destination).is_relative_to(Path(baseline).parent)
                         or Path(baseline).is_relative_to(Path(destination))):
            raise ProcessingError('monthly_destination_overlaps_baseline')
        dataset=preview_dataset(workspace,start,end,progress=progress,cancelled=stop.is_set)
        if not dataset.ready:
            issues.extend(f'{s.month} {s.report_type}: {s.status} ({s.code}). Process or correct this report, then preview again.'
                for s in dataset.selections if s.status!='ready')
        if baseline:old,digest=_baseline(baseline,dataset.configuration)
        inventory=discover_history(LocalFolderStorage(workspace.raw_folder),start,end,layout,cancelled=stop)
        selected={(s.month,s.report_type):s for s in dataset.selections}
        for month in inventory.months:
            for report in month.reports:
                key=(month.period,report.report_type.value);item=selected[key]
                blocking=[i.code for i in (*month.issues,*report.issues) if i.code!='historical_temporary_file_ignored']
                if blocking or report.status!='found' or len(report.sources)!=1:
                    issues.append(f'{key[0]} {key[1]}: raw report missing, ambiguous or unavailable. Restore the complete export and discover again. '+', '.join(blocking));continue
                source=report.sources[0]
                sources.append((key[0],key[1],source.item_id,source.version,source.sha256 or ''))
                if not source.sha256 or source.sha256!=item.source_sha256:
                    issues.append(f'{key[0]} {key[1]}: source changed or has no committed matching candidate. Complete the existing single-report correction approval AND processing, then preview again.')
        if stop.is_set():issues.append('Update review stopped. Preview again before confirming.')
        current_months=set(periods_between(start,end))
        previous_months=set(periods_between(old.start,old.end)) if old else set()
        added=tuple(sorted(current_months-previous_months));removed=tuple(sorted(previous_months-current_months))
        previous={(s.month,s.report_type):s for s in old.selections} if old else {}
        replacements=tuple((s.month,s.report_type,previous[s.month,s.report_type].revision,s.revision)
            for s in dataset.selections if (s.month,s.report_type) in previous
            and s.document()!=previous[s.month,s.report_type].document())
        changed_months={s[0] for s in replacements}
        unchanged=tuple(sorted((current_months & previous_months)-changed_months))
    except (ProcessingError,StorageError,OSError,ValueError,TypeError,KeyError) as exc:
        # Sanitized identifiers only: never display untrusted parser/path exception text.
        code=str(exc) if isinstance(exc,(ProcessingError,StorageError)) else 'monthly_evidence_unreadable'
        issues.append('Cannot verify update evidence ('+code+'). Check the explicitly selected completed baseline, workspace and local destination; preview again.')
    if issues:recommendation,permitted=REVIEW,()
    elif removed:recommendation,permitted=REVIEW,(REBUILD,)
    elif replacements:recommendation,permitted=REBUILD,(REBUILD,)
    elif old and not added:recommendation,permitted=UNCHANGED,()
    elif old:recommendation,permitted=ADD,(ADD,REBUILD)
    else:recommendation,permitted=REBUILD,(REBUILD,)
    if removed and not issues:
        issues.append('Proposed range removes baseline months. Only an explicitly confirmed Rebuild History may exclude them; expand the range to retain them.')
    return UpdatePlan(dataset,layout,baseline,digest,(old.start,old.end) if old else (),
        tuple((s.month,s.report_type,s.rows) for s in old.selections) if old else (),destination,
        recommendation,permitted,added,unchanged,removed,replacements,tuple(issues),tuple(sources))



def _evidence_versions(workspace, plan):
    """Cheap stable-file identity checks between writes, using the raw read contract."""
    provider=LocalFolderStorage(workspace.raw_folder)
    paths=[provider._path(s[2]) for s in plan.sources]
    if plan.baseline:
        paths += [_safe(Path(plan.baseline)/n) for n in
            (*NAMES.values(),'snapshot_manifest.json','compatibility_report.md')]
    return tuple(_version(_stat(p)) for p in paths)


def generate_update(workspace, plan, *, mode, confirmation, changes_confirmed=False,
                    local_confirmed=False, compatibility_acknowledged=False,
                    progress=lambda *_:None, cancelled=None):
    if mode not in plan.permitted:
        raise ProcessingError('monthly_update_blocked_or_unchanged')
    if confirmation!=plan.confirmation(mode) or (plan.changes_history and not changes_confirmed):
        raise ProcessingError('monthly_update_confirmation_required')
    stop=cancelled if cancelled is not None else Event()
    # Hold the existing DELETE-journal read lock through recheck and generation.
    # Baseline/source evidence is reread without cleaning; no candidate writes occur.
    with _store(workspace):
        try:versions=_evidence_versions(workspace,plan)
        except (StorageError,OSError):
            raise ProcessingError('monthly_update_plan_stale') from None
        fresh=preview_update(workspace,plan.dataset.start,plan.dataset.end,plan.layout,plan.destination,
            baseline=plan.baseline,progress=progress,cancelled=stop)
        if stop.is_set():raise ProcessingError('dataset_cancelled')
        if fresh.fingerprint!=plan.fingerprint:raise ProcessingError('monthly_update_plan_stale')
        def guarded_cancelled():
            if stop.is_set():return True
            try:
                if _evidence_versions(workspace,plan)!=versions:
                    raise ProcessingError('monthly_update_plan_stale')
            except (StorageError,OSError):
                raise ProcessingError('monthly_update_plan_stale') from None
            return False
        return generate_dataset(workspace,plan.dataset,plan.destination,
            confirmation=plan.dataset.fingerprint,local_confirmed=local_confirmed,
            compatibility_acknowledged=compatibility_acknowledged,progress=progress,cancelled=guarded_cancelled)
