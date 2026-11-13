"""Read selected candidate revisions into an immutable LOCAL UNAPPROVED snapshot.

No cleaning, source reads, manifest writes, approval, Graph or Power BI execution.
A missing slot blocks generation; no historical revision is used as a fallback.
"""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from importlib.resources import files
from io import StringIO
import csv
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys

from equipment_data_manager.historical import periods_between
from equipment_data_manager.monthly import Workspace, _check_windows_packet_paths
from equipment_data_manager.powerbi_readiness import _same_provenance, _record_contract, _financial_check
from equipment_data_manager.powerquery_contract import read_table
from equipment_data_manager.processing.manifest import LocalOutputStore
from equipment_data_manager.processing.models import ProcessingError, ReportType
from equipment_data_manager.processing.powerbi import schema as v1_schema
from equipment_data_manager.processing.repair_financial import schema as v2_schema, SUMMARY_COLUMNS, summary_name, powerbi_coordinator
from equipment_data_manager.settings import candidate_location_error

SNAPSHOT_SCHEMA = 'historical-powerbi-v1'
NAMES = {'repairs':'Repairs_History.csv', 'service_orders':'ServiceOrders_History.csv',
         'tma_work_orders':'TMAWorkOrders_History.csv', 'repair_financial_summary':'RepairFinancialSummaries.csv'}
PROVENANCE = ('ReportingMonth','CandidateRevisionId','CandidateOutputSHA256','CandidateCleanerVersion')
SUMS = ('EstimatedLaborCost','LegacyPartsCost','LegacyLaborCost','LegacyEstimatedTotalCost')
SUMMARY_EXTRA = tuple(n for c in SUMS for n in (c+'Sum', c+'MissingCount'))


def columns(kind):
    base = SUMMARY_COLUMNS + SUMMARY_EXTRA if kind == 'repair_financial_summary' else tuple(
        c.name for c in (v2_schema() if kind == 'repairs' else v1_schema(ReportType(kind))))
    return tuple(base) + PROVENANCE


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def _digest(value):
    return sha256(_json(value).encode()).hexdigest()


def _safe(path, *, local=False):
    path=Path(path).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (path,*path.parents)):
        raise ProcessingError('dataset_link_rejected')
    if local and candidate_location_error(path):
        raise ProcessingError('dataset_trusted_local_required')
    return path


def _roots(workspace):
    workspace.validate()
    root=_safe(workspace.candidate_folder,local=True)/'powerbi_candidates'
    for path in (root,root/'versions',root/'manifest.sqlite3'):
        _safe(path,local=True)
    return root,_digest([str(Path(p).absolute()) for p in
        (workspace.raw_folder,workspace.candidate_folder,workspace.approved_folder)])


def _raw_rows(raw):
    return list(csv.DictReader(StringIO(raw.decode('utf-8-sig'),newline=''),strict=True))


@dataclass(frozen=True)
class Selection:
    month: str
    report_type: str
    status: str
    code: str = ''
    revision: str = ''
    source_sha256: str = ''
    output_sha256: str = ''
    cleaner_version: str = ''
    rows: int | None = None
    warnings: tuple[str,...] = ()
    summary_sha256: str = ''
    reconciliation: str = ''
    unavailable_costs: int | None = None
    missing_assignments: int | None = None
    missing_identifiers: int | None = None

    def document(self):
        from dataclasses import asdict
        return asdict(self)


@dataclass(frozen=True)
class DatasetPlan:
    start: str
    end: str
    configuration: str
    selections: tuple[Selection,...]
    stopped: bool = False

    @property
    def ready(self):
        return not self.stopped and bool(self.selections) and all(s.status=='ready' for s in self.selections)

    def document(self):
        return dict(snapshot_schema=SNAPSHOT_SCHEMA,start=self.start,end=self.end,configuration=self.configuration,
            selections=[s.document() for s in self.selections],stopped=self.stopped,complete=self.ready,
            status='CandidateUnverified',production_ready=False)

    @property
    def fingerprint(self):
        return _digest(self.document())


@contextmanager
def _store(workspace):
    root,configuration=_roots(workspace)
    try:
        with LocalOutputStore(root).read_transaction() as connection:
            if connection is not None and connection.execute('PRAGMA journal_mode').fetchone()[0]!='delete':
                raise ProcessingError('dataset_manifest_journal_rejected')
            yield root,configuration,connection
    except ProcessingError:
        raise
    except (sqlite3.Error,OSError,ValueError,KeyError,TypeError):
        raise ProcessingError('dataset_store_unreadable') from None


def _selected(root, connection, month, kind, supported):
    """Validate/parse the very same bytes hashed here. No recursive listing."""
    if connection is None:
        return Selection(month,kind,'missing','dataset_selected_revision_missing'),None,None
    row=connection.execute('''SELECT r.id,r.source_hash,r.output_hash,r.cleaner_version,r.input_rows,
        r.output_rows,r.warnings,r.report_type,r.period FROM active a LEFT JOIN revisions r
        ON r.id=a.revision_id WHERE a.report_type=? AND a.period=?''',(kind,month)).fetchone()
    if row is None:
        return Selection(month,kind,'missing','dataset_selected_revision_missing'),None,None
    if row[0] is None or row[7:]!=(kind,month):
        raise ProcessingError('dataset_revision_binding_rejected')
    revision,source_hash,output_hash,version,input_rows,count,warning_json,_,_=row
    if (version!=supported[ReportType(kind)] or not all(re.fullmatch('[0-9a-f]{64}',h or '') for h in (source_hash,output_hash))
            or not isinstance(count,int) or count<1 or not isinstance(input_rows,int) or input_rows<count):
        raise ProcessingError('dataset_revision_metadata_rejected')
    warnings=json.loads(warning_json)
    if not isinstance(warnings,list) or any(not isinstance(w,str) for w in warnings):
        raise ProcessingError('dataset_revision_metadata_rejected')
    path=LocalOutputStore(root).artifact_path(ReportType(kind),month,revision)
    _safe(path)
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=output_hash:
        raise ProcessingError('dataset_candidate_hash_mismatch')
    typed=read_table(raw,ReportType(kind),allow_candidates=True)
    if len(typed)!=count or typed[0]['ReportMonth']!=month or any(r['SourceFileSHA256']!=source_hash for r in typed):
        raise ProcessingError('dataset_revision_binding_rejected')
    expected_schema='2' if kind=='repairs' else '1'
    if typed[0]['SchemaVersion']!=expected_schema or version!=typed[0]['ExportVersion']+':'+typed[0]['CleanerVersion']:
        raise ProcessingError('dataset_schema_or_cleaner_rejected')
    _same_provenance(typed,ReportType(kind));_record_contract(typed,ReportType(kind))
    records=_raw_rows(raw)
    extra=None;summary_sha='';state='';unavailable=0
    if kind=='repairs':
        summary_path=_safe(path.parent/summary_name(month));summary_raw=summary_path.read_bytes()
        summary_sha=sha256(summary_raw).hexdigest()
        if any(r['FinancialSummarySHA256']!=summary_sha for r in typed):
            raise ProcessingError('dataset_summary_hash_mismatch')
        summary=read_table(summary_raw,ReportType.REPAIRS,allow_candidates=True,financial_summary=True)[0]
        if summary['SourceRecordCount']!=input_rows:
            raise ProcessingError('dataset_revision_binding_rejected')
        state=_financial_check(typed,summary);unavailable=int(summary['UnavailableRepairCostCount'])
        extra=_raw_rows(summary_raw)[0]
        # Summary controls only, never inferred per-repair source parts/labor.
        for column in SUMS:
            values=[r[column] for r in typed];missing=sum(v is None for v in values)
            extra[column+'Sum']='' if missing else format(sum(values,Decimal(0)),'f')
            extra[column+'MissingCount']=str(missing)
    return Selection(month,kind,'ready',revision=revision,source_sha256=source_hash,
        output_sha256=output_hash,cleaner_version=version,rows=count,warnings=tuple(warnings),
        summary_sha256=summary_sha,reconciliation=state,unavailable_costs=unavailable,
        missing_assignments=sum(not r['AssignedTo'] for r in typed) if kind=='tma_work_orders' else 0,
        missing_identifiers=sum(not r['WorkOrderId' if kind=='tma_work_orders' else 'EquipmentId'] for r in typed)),records,extra


def _collect(workspace,start,end,root,configuration,connection,progress,cancelled):
    months=periods_between(start,end)
    supported={k:c.version for k,c in powerbi_coordinator(workspace.candidate_folder).cleaners.items()}
    selections=[];datasets={k:[] for k in NAMES};seen=set();stopped=False
    for month in months:
        for kind in ReportType:
            if cancelled():stopped=True
            if stopped:
                selections.append(Selection(month,kind.value,'not_assessed','dataset_cancelled'));continue
            try:
                item,records,summary=_selected(root,connection,month,kind.value,supported)
                if item.revision and item.revision in seen:raise ProcessingError('dataset_duplicate_revision')
                if item.revision:seen.add(item.revision)
                if records:
                    provenance=dict(zip(PROVENANCE,(month,item.revision,item.output_sha256,item.cleaner_version)))
                    datasets[kind.value].extend(dict(r,**provenance) for r in records)
                    if summary:datasets['repair_financial_summary'].append(dict(summary,**provenance))
            except ProcessingError as exc:
                item=Selection(month,kind.value,'invalid',str(exc))
            except (OSError,ValueError,TypeError,KeyError,csv.Error):
                item=Selection(month,kind.value,'invalid','dataset_candidate_unreadable')
            selections.append(item);progress(len(selections),len(months)*len(ReportType))
    return DatasetPlan(start,end,configuration,tuple(selections),stopped),datasets


def preview_dataset(workspace,start,end,*,progress=lambda *_:None,cancelled=lambda:False):
    with _store(workspace) as (root,configuration,connection):
        return _collect(workspace,start,end,root,configuration,connection,progress,cancelled)[0]


def _encode(records, fields):
    stream=StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
    writer.writeheader();writer.writerows(records)
    return stream.getvalue().encode('utf-8')


def _write(path,raw):
    with path.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    if sha256(path.read_bytes()).digest()!=sha256(raw).digest():raise ProcessingError('dataset_write_integrity_failed')


def compatibility_report(plan):
    base=files('equipment_data_manager.resources.guides').joinpath('historical_powerbi_compatibility.md').read_text(encoding='utf-8')
    lines=['# Snapshot-specific assessment','',f'Range: {plan.start} through {plan.end}.',
        'Status: CandidateUnverified. Approval: Not approved. Compatibility gaps acknowledged for a backup test only.',
        'Completeness: all requested slots selected and integrity checked. This is not source/business verification.',
        '','| Month | Type | Records | Missing costs | Missing assignments | Reconciliation |',
        '|---|---|---:|---:|---:|---|']
    lines += [f'| {s.month} | {s.report_type} | {s.rows} | {s.unavailable_costs} | {s.missing_assignments} | {s.reconciliation or "Not applicable"} |' for s in plan.selections]
    return '\n'.join(lines)+'\n\n'+base


def _destination(workspace,destination,*,windows=None):
    final=_safe(destination)
    stage=final/'.s';completed=final/'snapshot'
    if (windows if windows is not None else sys.platform=='win32'):
        try:_check_windows_packet_paths(stage,completed,tuple(NAMES.values())+('snapshot_manifest.json','compatibility_report.md'))
        except ProcessingError:raise ProcessingError('dataset_windows_path_too_long') from None
    if candidate_location_error(final):raise ProcessingError('dataset_trusted_local_required')
    for protected in (workspace.raw_folder,workspace.candidate_folder,workspace.approved_folder):
        p=Path(protected).resolve()
        if final.resolve().is_relative_to(p) or p.is_relative_to(final.resolve()):
            raise ProcessingError('dataset_destination_overlaps_workspace')
    return final,stage,completed


def generate_dataset(workspace,plan,destination,*,confirmation,local_confirmed=False,compatibility_acknowledged=False,
                     progress=lambda *_:None,cancelled=lambda:False):
    if not plan.ready:raise ProcessingError('dataset_incomplete_selection')
    if confirmation!=plan.fingerprint or not local_confirmed or not compatibility_acknowledged:
        raise ProcessingError('dataset_confirmation_required')
    final,stage,completed=_destination(workspace,destination)
    if final.exists():raise ProcessingError('dataset_destination_exists')
    # Retain the existing read transaction through finalization. Under the existing
    # SQLite rollback journal, writers cannot commit a changed selection meanwhile.
    with _store(workspace) as (root,configuration,connection):
        fresh,datasets=_collect(workspace,plan.start,plan.end,root,configuration,connection,progress,cancelled)
        if cancelled() or fresh.stopped:raise ProcessingError('dataset_cancelled')
        if fresh.fingerprint!=plan.fingerprint:raise ProcessingError('dataset_plan_stale')
        _destination(workspace,destination)
        final.parent.mkdir(parents=True,exist_ok=True)
        final.mkdir(exist_ok=False)  # Exclusive ownership; never remove someone else's snapshot.
        try:
            stage.mkdir();entries=[]
            for kind,name in NAMES.items():
                if cancelled():raise ProcessingError('dataset_cancelled')
                raw=_encode(datasets[kind],columns(kind));_write(stage/name,raw)
                counts={month:sum(r['ReportingMonth']==month for r in datasets[kind]) for month in periods_between(plan.start,plan.end)}
                entries.append(dict(report_type=kind,file=name,sha256=sha256(raw).hexdigest(),rows=len(datasets[kind]),
                    rows_by_month=counts,columns=columns(kind)))
            report=compatibility_report(plan).encode('utf-8');_write(stage/'compatibility_report.md',report)
            manifest=dict(plan.document(),created_utc=datetime.now(timezone.utc).isoformat(),plan_sha256=plan.fingerprint,
                financial_schema_version='2',business_verification='Unverified',approval_status='NotApproved',
                source_bytes_verified=False,missing_selections=[],explicit_exclusions=[],datasets=entries,
                compatibility_report_sha256=sha256(report).hexdigest(),compatibility_policy='canonical_no_dashboard_exclusions',
                compatibility_gaps_acknowledged=True)
            # Duplicate business IDs are diagnostics, never a deduplication rule.
            ids=[r['WorkOrderId'] for r in datasets['tma_work_orders'] if r['WorkOrderId']]
            manifest['repeated_work_order_id_occurrences']=len(ids)-len(set(ids))
            _write(stage/'snapshot_manifest.json',(_json(manifest)+'\n').encode('utf-8'))
            validate_dataset(stage)
            if cancelled():raise ProcessingError('dataset_cancelled')
            stage.rename(completed)  # All four datasets become visible together.
        except BaseException:
            shutil.rmtree(final)
            raise
    return completed


def validate_dataset(root):
    """Offline hash/schema/binding check of one completed test snapshot, no model execution."""
    root=_safe(root,local=True)
    try:
        manifest=json.loads((root/'snapshot_manifest.json').read_text(encoding='utf-8'))
        if (manifest['snapshot_schema']!=SNAPSHOT_SCHEMA or manifest['status']!='CandidateUnverified'
                or manifest['production_ready'] is not False or manifest['approval_status']!='NotApproved'
                or manifest['financial_schema_version']!='2' or not manifest['complete']):
            raise ProcessingError('dataset_snapshot_contract_rejected')
        months=periods_between(manifest['start'],manifest['end'])
        selections={(s['month'],s['report_type']):s for s in manifest['selections']}
        expected={(m,k.value) for m in months for k in ReportType}
        if (set(selections)!=expected or len(manifest['selections'])!=len(expected)
                or any(s['status']!='ready' for s in selections.values())):
            raise ProcessingError('dataset_snapshot_contract_rejected')
        entries=manifest['datasets']
        if len(entries)!=4 or {e['report_type'] for e in entries}!=set(NAMES):
            raise ProcessingError('dataset_snapshot_contract_rejected')
        if {p.name for p in root.iterdir()}!=set(NAMES.values())|{'snapshot_manifest.json','compatibility_report.md'}:
            raise ProcessingError('dataset_snapshot_contract_rejected')
        report=_safe(root/'compatibility_report.md').read_bytes()
        if sha256(report).hexdigest()!=manifest['compatibility_report_sha256']:
            raise ProcessingError('dataset_snapshot_hash_mismatch')
        tables={}
        for entry in entries:
            kind=entry['report_type']
            if entry['file']!=NAMES[kind] or entry['columns']!=list(columns(kind)):
                raise ProcessingError('dataset_snapshot_contract_rejected')
            raw=_safe(root/NAMES[kind]).read_bytes()
            if sha256(raw).hexdigest()!=entry['sha256']:raise ProcessingError('dataset_snapshot_hash_mismatch')
            rows=_raw_rows(raw)
            if not rows or list(rows[0])!=list(columns(kind)) or any(None in r or any(v is None for v in r.values()) for r in rows):
                raise ProcessingError('dataset_snapshot_contract_rejected')
            counts={m:sum(r['ReportingMonth']==m for r in rows) for m in months}
            if (entry['rows']!=len(rows) or entry['rows_by_month']!=counts or sum(counts.values())!=len(rows)):
                raise ProcessingError('dataset_snapshot_contract_rejected')
            tables[kind]=rows
            for month in months:
                selection=selections[month,'repairs' if kind=='repair_financial_summary' else kind]
                monthly=[r for r in rows if r['ReportingMonth']==month]
                if (len(monthly)!=(1 if kind=='repair_financial_summary' else selection['rows']) or any(
                    r['ReportMonth']!=month or r['CandidateRevisionId']!=selection['revision'] or
                    r['CandidateOutputSHA256']!=selection['output_sha256'] or
                    r['CandidateCleanerVersion']!=selection['cleaner_version'] or
                    r['SourceFileSHA256']!=selection['source_sha256'] for r in monthly)):
                    raise ProcessingError('dataset_snapshot_contract_rejected')
                base=SUMMARY_COLUMNS if kind=='repair_financial_summary' else columns(kind)[:-len(PROVENANCE)]
                read_table(_encode([{k:r[k] for k in base} for r in monthly],base),
                    ReportType.REPAIRS if kind=='repair_financial_summary' else ReportType(kind),
                    allow_candidates=True,financial_summary=kind=='repair_financial_summary')
        return manifest
    except ProcessingError:raise
    except (OSError,ValueError,KeyError,TypeError,csv.Error):
        raise ProcessingError('dataset_snapshot_contract_rejected') from None


def main():
    parser=argparse.ArgumentParser(description='Local unapproved historical dataset; no PBIX/Graph/approval operations')
    parser.add_argument('--verify-snapshot',type=Path)
    for name in ('raw-folder','candidate-folder','approved-folder','destination'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--start');parser.add_argument('--end')
    parser.add_argument('--create-local-unapproved',action='store_true')
    args=parser.parse_args()
    if args.verify_snapshot:
        try:
            result=validate_dataset(args.verify_snapshot)
            print('CandidateUnverified snapshot integrity passed; not business approval. Range:',result['start'],result['end']);return
        except ProcessingError as exc:parser.exit(1,str(exc)+'\n')
    if any(getattr(args,key) is None for key in ('raw_folder','candidate_folder','approved_folder','destination','start','end')):
        parser.error('Provide workspace folders, destination, start and end, or --verify-snapshot')
    workspace=Workspace(args.raw_folder,args.candidate_folder,args.approved_folder)
    try:
        plan=preview_dataset(workspace,args.start,args.end)
        print(json.dumps(plan.document(),indent=2))
        if args.create_local_unapproved:
            print(generate_dataset(workspace,plan,args.destination,confirmation=plan.fingerprint,
                local_confirmed=True,compatibility_acknowledged=True))
    except (ProcessingError,OSError) as exc:
        parser.exit(1,f'Historical snapshot stopped: {str(exc) if isinstance(exc,ProcessingError) else "local_storage_unavailable"}\n')


if __name__=='__main__':main()
