"""Read-only, redacted V3 acceptance checks. No generation or remediation API.

Run from the repository: python tools/acceptance/analyze_v3.py --help
Core analysis and report writing use only the standard library. The existing app
verifiers are an additional check; independent assertions do not trust them.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
import os
import re
from pathlib import Path
import shutil

try:
    from .contracts import (FILES, SPECS, CANONICAL_COLUMNS, BASE_LINEAGE, LINEAGE_FIELDS,
        DIAGNOSTIC_FIELDS, OBSERVATION_FIELDS, CLASS_DIAGNOSTIC_FIELDS, POLICIES)
    from .reference import FACTS, identifier, display_name, equipment, room_label, building, maintenance, resolve_equipment
except ImportError:  # Direct script execution, not an installed application module.
    from contracts import (FILES, SPECS, CANONICAL_COLUMNS, BASE_LINEAGE, LINEAGE_FIELDS,
        DIAGNOSTIC_FIELDS, OBSERVATION_FIELDS, CLASS_DIAGNOSTIC_FIELDS, POLICIES)
    from reference import FACTS, identifier, display_name, equipment, room_label, building, maintenance, resolve_equipment

STATUSES=('PASS','REVIEW','FAIL','NOT TESTED')
CANONICAL_FILES=tuple(FILES[k] for k in CANONICAL_COLUMNS)+('snapshot_manifest.json','compatibility_report.md')
AUDIT_SPECS={'audit/lineage.csv':LINEAGE_FIELDS,'audit/diagnostics.csv':DIAGNOSTIC_FIELDS,
    'audit/equipment_observations.csv':OBSERVATION_FIELDS,'audit/classification_diagnostics.csv':CLASS_DIAGNOSTIC_FIELDS}
EXTRAS=tuple(AUDIT_SPECS)+('comparison_manifest.json','comparison_warnings.txt',)
EXPECTED_COMPARISON=tuple(FILES.values())+EXTRAS+tuple('audit/canonical/'+f for f in CANONICAL_FILES)


class Rejected(ValueError):pass


def plain_path(path):
    path=Path(path).absolute()
    if str(path).startswith(('\\\\','//')):raise Rejected('network_path_rejected')
    for part in (path,*path.parents):
        if part.is_symlink() or getattr(part,'is_junction',lambda:False)():raise Rejected('linked_path_rejected')
    return path.resolve()


def read_bytes(path):
    path=plain_path(path)
    if not path.is_file():raise Rejected('regular_file_required')
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno());raw=stream.read();after=os.fstat(stream.fileno())
    keys=('st_dev','st_ino','st_size','st_mtime_ns')
    if tuple(getattr(before,k) for k in keys)!=tuple(getattr(after,k) for k in keys):raise Rejected('input_changed_during_read')
    return raw


def capture(root,expected):
    root=plain_path(root)
    if not root.is_dir() or root.name.startswith('.'):raise Rejected('incomplete_or_unavailable_directory')
    actual=set()
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in (*dirs,*files):plain_path(Path(parent)/name)
        actual.update((Path(parent)/name).relative_to(root).as_posix() for name in files)
    if actual!=set(expected):raise Rejected('missing_or_unexpected_files')
    return {name:read_bytes(root/name) for name in expected}


def document(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise Rejected('duplicate_json_key')
            result[key]=value
        return result
    def invalid_constant(_):raise Rejected('nonfinite_json_constant')
    value=json.loads(raw,object_pairs_hook=unique,parse_constant=invalid_constant)
    if not isinstance(value,dict):raise Rejected('json_object_required')
    return value


def records(raw,columns=None):
    table=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True))
    if not table or len(set(table[0]))!=len(table[0]):raise Rejected('missing_or_duplicate_csv_header')
    if columns is not None and table[0]!=list(columns):raise Rejected('ordered_csv_schema_mismatch')
    if any(len(row)!=len(table[0]) for row in table[1:]):raise Rejected('csv_record_width_mismatch')
    return [dict(zip(table[0],row)) for row in table[1:]]


def month(value):
    try:
        return isinstance(value,str) and len(value)==7 and value[4]=='-' and date.fromisoformat(value+'-01').strftime('%Y-%m')==value
    except (ValueError,TypeError):return False


def typed(rows,spec):
    try:
        for row in rows:
            for field,kind in spec:
                value=row[field]
                if kind=='text':
                    if field in ('ReportMonth','FirstObservedMonth','LastObservedMonth') and not month(value):return False
                elif kind=='boolean':
                    if value not in ('true','false'):return False
                elif not value:continue  # Financial and date nulls remain null.
                elif kind=='date':
                    if date.fromisoformat(value).isoformat()!=value:return False
                else:
                    number=Decimal(value)
                    if not number.is_finite() or kind=='integer' and number!=number.to_integral_value():return False
        return True
    except (ValueError,InvalidOperation,KeyError):return False


def application_verification(comparison,canonical):
    try:
        from equipment_data_manager.comparison_export import validate_comparison
        from equipment_data_manager.historical_dataset import validate_dataset
    except ImportError:return 'NOT TESTED'
    try:
        validate_dataset(canonical);validate_comparison(comparison)
    except Exception:return 'FAIL'  # Never copy a potentially private exception into reports.
    return 'PASS'


class Checks:
    def __init__(self):self.items=[]
    def add(self,key,status,summary,metrics=None,refs=(),action=''):
        assert status in STATUSES
        refs=list(refs)
        self.items.append(dict(id=key,status=status,summary=summary,metrics=metrics or {},
            evidence=refs[:20],evidence_total=len(refs),evidence_truncated=len(refs)>20,next_step=action))
    def invariant(self,key,ok,summary,metrics=None,refs=()):
        self.add(key,'PASS' if ok else 'FAIL',summary,metrics,refs,
            '' if ok else 'Keep inputs unchanged. Reproduce on a disposable copy and request owner review; do not repair data automatically.')
    def review(self,key,refs,summary,metrics=None):
        refs=list(refs)
        self.add(key,'REVIEW' if refs else 'PASS',summary,metrics,refs,
            'Review referenced records in the private audit evidence with the data owner; no automatic correction.' if refs else '')


def ref(kind,ordinal):return dict(dataset=FILES[kind],record=ordinal)


def monthly(rows,field='ReportMonth'):return dict(sorted(Counter(r[field] for r in rows).items()))


def public_months(value):
    safe=Counter()
    for key,n in value.items():safe[key if month(key) else '<invalid-month>']+=n
    return dict(sorted(safe.items()))


def count_map(value):
    return isinstance(value,dict) and all(type(n) is int and n>=0 and month(m) for m,n in value.items())


def _indexes(entries,kinds):
    if len(entries)!=len(kinds) or {e['report_type'] for e in entries}!=set(kinds):raise Rejected('manifest_dataset_set_mismatch')
    return {e['report_type']:e for e in entries}


def _analyze(checks,comparison,canonical,bundle,source,dimension):
    manifest=document(bundle['comparison_manifest.json']);original=document(source['snapshot_manifest.json'])
    if manifest.get('export_schema')!='comparison-preview-v3':raise Rejected('unsupported_export_version')
    if (original.get('snapshot_schema')!='historical-powerbi-v1' or original.get('financial_schema_version')!='2'
        or original.get('complete') is not True or original.get('stopped') is not False):raise Rejected('incomplete_or_unsupported_canonical')
    if any(manifest.get(k)!=v for k,v in POLICIES.items()):raise Rejected('unsupported_rule_version')
    gates=dict(purpose='DevelopmentComparison',status='CandidateUnverified',approval_status='NotApproved',production_ready=False)
    checks.invariant('development_contract',all(type(manifest.get(k)) is type(v) and manifest.get(k)==v for k,v in gates.items()),'Export is explicitly development-only, not production approval.')
    checks.invariant('source_association',manifest.get('source_manifest_sha256')==sha256(source['snapshot_manifest.json']).hexdigest()
        and all(bundle['audit/canonical/'+name]==raw for name,raw in source.items()),'Retained canonical bytes match the separately supplied snapshot.')
    checks.invariant('canonical_contract',all(type(original.get(k)) is type(v) and original.get(k)==v for k,v in dict(status='CandidateUnverified',approval_status='NotApproved',production_ready=False).items()),'Canonical input remains a complete unapproved historical snapshot.')
    checks.invariant('manifest_context',manifest.get('start')==original.get('start') and manifest.get('end')==original.get('end')
        and manifest.get('source_snapshot_schema')==original.get('snapshot_schema')
        and manifest.get('equipment_month_count_basis')=='FirstObservedMonth',
        'Selection interval, canonical contract and equipment monthly-count basis match the associated snapshot.')
    indexed=_indexes(manifest['datasets'],FILES);source_entries=_indexes(original['datasets'],CANONICAL_COLUMNS)
    tables={};canonical_rows={}
    for kind,name in FILES.items():
        entry=indexed[kind];spec=SPECS[kind]
        tables[kind]=records(bundle[name],[c[0] for c in spec])
        by_month=monthly(tables[kind],'FirstObservedMonth' if kind=='equipment' else 'ReportMonth')
        checks.invariant('dataset_'+kind,entry['file']==name and entry['sha256']==sha256(bundle[name]).hexdigest()
            and entry['columns']==[dict(name=n,type=t) for n,t in spec] and type(entry['rows']) is int
            and entry['rows']==len(tables[kind]) and count_map(entry['rows_by_month']) and entry['rows_by_month']==by_month and typed(tables[kind],spec),
            'Dataset hash, ordered schema, declared types and total/monthly counts match the frozen V3 reference.',
            dict(rows=len(tables[kind]),rows_by_month=public_months(by_month)))
        if kind in CANONICAL_COLUMNS:
            entry=source_entries[kind];canonical_rows[kind]=records(source[name],CANONICAL_COLUMNS[kind])
            checks.invariant('canonical_'+kind,entry['file']==name and entry['sha256']==sha256(source[name]).hexdigest()
                and entry['columns']==list(CANONICAL_COLUMNS[kind]) and type(entry['rows']) is int and entry['rows']==len(canonical_rows[kind])
                and count_map(entry['rows_by_month'])
                and entry['rows_by_month']==monthly(canonical_rows[kind]),'Canonical file schema/hash/counts match its manifest.')
    checks.invariant('canonical_report_hash',original['compatibility_report_sha256']==sha256(source['compatibility_report.md']).hexdigest(),'Canonical compatibility report hash matches.')
    audits={name:records(bundle[name],cols) for name,cols in AUDIT_SPECS.items()}
    lineage=manifest['lineage']
    extras=manifest['diagnostics'];extra_names=set(AUDIT_SPECS)-{'audit/lineage.csv'}|{'comparison_warnings.txt'}
    checks.invariant('audit_integrity',len(extras)==len(extra_names) and {e['file'] for e in extras}==extra_names
        and all(e['sha256']==sha256(bundle[e['file']]).hexdigest() for e in extras)
        and lineage['file']=='audit/lineage.csv' and lineage['columns']==list(LINEAGE_FIELDS)
        and type(lineage['rows']) is int and lineage['rows']==len(audits['audit/lineage.csv']) and lineage['sha256']==sha256(bundle['audit/lineage.csv']).hexdigest(),
        'All audit/warning hashes, ordered audit schemas and lineage counts match.')
    _semantic(checks,tables,canonical_rows,audits,dimension)
    checks.add('application_verifiers',application_verification(comparison,canonical),
        'Additional existing read-only canonical/comparison verifiers; independent assertions above do not depend on their verdict.',
        action='Use the frozen project environment. A verifier rejection needs investigation, not automatic repairs.')


def lineage_matches_outputs(links,tables):
    kinds={name:kind for kind,name in FILES.items()}
    try:
        for link in links:
            kind=kinds[link['Dataset']];ordinal=int(link['ExportRecordNumber'])
            if ordinal<1:return False
            row=tables[kind][ordinal-1]
            for field in ('ReportMonth','EquipmentId','RawEquipmentId','Location','Building',
                          'EquipmentType','MaintenanceType','ObservedEquipmentName'):
                if field in row and link[field]!=row[field]:return False
            if 'EquipmentName' in row and link['ResolvedEquipmentName']!=row['EquipmentName']:return False
        return True
    except (KeyError,IndexError,ValueError):return False


def _semantic(checks,tables,canonical,audits,dimension):
    resolved=resolve_equipment(canonical)
    lookup=tables['equipment'];lookup_map={r['EquipmentId']:r for r in lookup}
    checks.invariant('equipment_unique',len(lookup_map)==len(lookup) and '' not in lookup_map,'Lookup keys are unique and nonblank.',dict(lookup_rows=len(lookup)))
    actual_observation_counts=Counter(r['EquipmentId'] for k in FACTS for r in tables[k] if r['EquipmentId'])
    observed_counts_match=set(actual_observation_counts)==set(lookup_map) and all(str(actual_observation_counts[key])==row['ObservationCount'] for key,row in lookup_map.items())
    checks.invariant('equipment_resolution',lookup==[r['row'] for r in resolved.values()] and observed_counts_match,
        'Lookup names/types/months/counts/conflicts/order independently follow the documented most-recent-name policy.')
    known={room_label(r['Location']) for kind in FACTS for r in canonical[kind]}-{''}
    variants=defaultdict(set)
    for kind in FACTS:
        for row in canonical[kind]:
            key,status=identifier(row['EquipmentId'])
            if status in ('normalized','unchanged'):variants[key].add(row['EquipmentId'])
    issues=defaultdict(list);expected_links=[];expected_observations=[];maintenance_counts=Counter();financial={};maintenance_mismatch=[]
    for kind in CANONICAL_COLUMNS:
        old,new=canonical[kind],tables[kind]
        mismatch=[];link_mismatch=[]
        checks.invariant('record_counts_'+kind,len(old)==len(new) and monthly(old)==monthly(new),
            'Canonical and V3 transaction/summary counts match by month; repeated occurrences are retained.',
            dict(canonical=len(old),comparison=len(new),rows_by_month=public_months(monthly(new))))
        for ordinal,row in enumerate(old,1):
            expected={name:row[name] for name,_ in SPECS[kind] if name in row}
            evidence={key:'' for key in LINEAGE_FIELDS};evidence.update({key:row.get(key,'') for key in BASE_LINEAGE})
            evidence.update(Dataset=FILES[kind],ExportRecordNumber=str(ordinal),CanonicalDataset=FILES[kind],CanonicalRecordNumber=str(ordinal))
            if kind in FACTS:
                key,status=identifier(row['EquipmentId']);selected=resolved.get(key)
                name=selected['row']['EquipmentName'] if selected else display_name(row['EquipmentName'])
                category,rule,broad=equipment(name);building_value,building_status=building(row['Location'],known)
                original=row.get('RawDescription',row['Description']);tag=row.get('SourceMaintenanceTag','')
                maintenance_label,signals=maintenance(tag,original,row['Description'])
                expected.update(EquipmentId=key,EquipmentName=name,ObservedEquipmentName=row['EquipmentName'],
                    EquipmentType=category,Building=building_value,MaintenanceType=maintenance_label)
                conflict=selected['row']['NameConflict'] if selected else 'false'
                collision=len(variants[key])>1
                legacy=re.split('[0-9]',row['Location'].strip(),maxsplit=1)[0].strip() if kind=='repairs' else row['Location'].rsplit(' ',1)[0] if ' ' in row['Location'] else ''
                evidence.update(CanonicalEquipmentId=row['EquipmentId'],EquipmentId=key,RawEquipmentId=row['RawEquipmentId'],Location=row['Location'],
                    Building=building_value,BuildingStatus=building_status,EquipmentIdStatus=status,LegacyBuilding=legacy,
                    LegacyBuildingPolicy='repairs_before_first_digit' if kind=='repairs' else 'service_before_final_space',Collision=str(collision).lower(),
                    ObservedEquipmentName=row['EquipmentName'],ResolvedEquipmentName=name,EquipmentType=category,MaintenanceType=maintenance_label)
                observation=dict(Dataset=FILES[kind],CanonicalRecordNumber=str(ordinal),RecordId=row.get('RecordId',''),ReportMonth=row['ReportMonth'],
                    SourceFileSHA256=row.get('SourceFileSHA256',''),SourceRecordNumber=row.get('SourceRecordNumber',''),EquipmentId=key,
                    ObservedEquipmentName=row['EquipmentName'],ResolvedEquipmentName=name,EquipmentType=category,EquipmentRule=rule,
                    EquipmentWarnings=json.dumps(broad),NameConflict=conflict,EquipmentExportRecordNumber=str(selected['ordinal']) if selected else '',
                    SourceMaintenanceTag=tag,OriginalDescription=original,CleanedDescription=row['Description'],MaintenanceType=maintenance_label,
                    MaintenanceEvidence=dict(tag=tag,original=original,cleaned=row['Description'],signals=signals))
                expected_observations.append(observation)
                if selected:
                    link=dict(evidence,Dataset=FILES['equipment'],ExportRecordNumber=str(selected['ordinal']))
                    expected_links.append(link)
                reference=ref(kind,ordinal)
                if conflict=='true':issues['name_conflicts'].append(reference)
                if collision:issues['id_collisions'].append(reference)
                if status in ('missing','unsupported'):issues['id_'+status].append(reference)
                if category=='Other':issues['equipment_other'].append(reference)
                if broad:issues['broad_equipment_keywords'].append(reference)
                if 'kaivac' in name.casefold():issues['kaivac_precedence'].append(reference)
                if building_status in ('missing','unresolved','ambiguous'):issues['building_'+building_status].append(reference)
                if maintenance_label in ('Needs Review','Unclassified'):issues['maintenance_uncertain'].append(reference)
                if ordinal<=len(new):
                    maintenance_counts[(kind,row['ReportMonth'],new[ordinal-1]['MaintenanceType'])]+=1
                    if new[ordinal-1]['MaintenanceType']!=maintenance_label:maintenance_mismatch.append(reference)
            if ordinal>len(new) or new[ordinal-1]!=expected:mismatch.append(ref(kind,ordinal))
            expected_links.append(evidence)
        checks.invariant('ordered_projection_'+kind,not mismatch and len(old)==len(new),
            'Every ordered occurrence independently matches canonical values plus documented enrichment; no row deduplication, reordering or value replacement.',
            dict(mismatched_occurrences=len(mismatch)),mismatch)
        if kind in FACTS:
            link_mismatch=[ref(kind,i) for i,r in enumerate(new,1) if r['EquipmentId'] and
                (r['EquipmentId'] not in lookup_map or any(r[f]!=lookup_map[r['EquipmentId']][f] for f in ('EquipmentName','EquipmentType')))]
            checks.invariant('lookup_fact_'+kind,not link_mismatch,'Every nonblank fact key has a lookup with the same resolved name/type.',refs=link_mismatch)
        if kind in ('repairs','service_orders','repair_financial_summary'):
            fields=[(name,t) for name,t in SPECS[kind] if t in ('integer','decimal')]
            field_results={}
            for field,_ in fields:
                left=[r[field] for r in old];right=[r[field] for r in new]
                try:equal_totals=sum((Decimal(v) for v in left if v),Decimal(0))==sum((Decimal(v) for v in right if v),Decimal(0))
                except InvalidOperation:equal_totals=False
                field_results[field]=dict(canonical_nulls=left.count(''),comparison_nulls=right.count(''),equal_cells=left==right,equal_totals=equal_totals)
            financial[kind]=field_results
            checks.invariant('financial_'+kind,all(v['equal_cells'] and v['equal_totals'] for v in field_results.values()),
                'Each count/hour/financial field is compared separately, including nulls and decimal totals. Reported amounts are never combined with estimates.',field_results)
    # One original link per occurrence and one derived lookup link per contributor.
    pack=lambda row:tuple(row.get(key,'') for key in LINEAGE_FIELDS)
    same_counts=all(len(tables[k])==len(canonical[k]) for k in CANONICAL_COLUMNS)
    checks.invariant('complete_lineage',same_counts and len(lookup)==len(resolved) and observed_counts_match
        and lineage_matches_outputs(audits['audit/lineage.csv'],tables)
        and Counter(map(pack,expected_links))==Counter(map(pack,audits['audit/lineage.csv'])),
        'Lineage maps every output occurrence and equipment contributor to its canonical dataset/ordinal, record ID, revision and hashes.',dict(expected_links=len(expected_links),actual_links=len(audits['audit/lineage.csv'])))
    actual_observations=audits['audit/equipment_observations.csv'];observations=[]
    try:
        for row in actual_observations:
            item=dict(row);item['MaintenanceEvidence']=document(item['MaintenanceEvidence']);observations.append(item)
        valid=json.dumps(observations,sort_keys=True)==json.dumps(expected_observations,sort_keys=True)
    except (ValueError,TypeError):valid=False
    checks.invariant('classification_source_evidence',valid and all(len(tables[k])==len(canonical[k]) for k in FACTS),'Every classification/conflicting name retains exact source tags/descriptions, canonical source references and independently checked rule evidence.',
        dict(expected_observations=len(expected_observations),actual_observations=len(actual_observations)))
    checks.invariant('maintenance_evidence_consistency',not maintenance_mismatch,
        'Maintenance labels independently match prioritized source evidence; contradictory/uncertain evidence cannot silently become Needed Repair.',
        dict(suspicious_classifications=len(maintenance_mismatch)),maintenance_mismatch)
    labels={'Preventive Maintenance','Needed Repair','Unclassified','Needs Review'}
    checks.invariant('maintenance_contract',all(key[2] in labels for key in maintenance_counts),
        'Maintenance labels use the four-value contract, preserving Unclassified and Needs Review.',
        {'by_report_month':[dict(report_type=k,month=m if month(m) else '<invalid-month>',classification=label if label in labels else '<invalid-label>',rows=n) for (k,m,label),n in sorted(maintenance_counts.items())]})
    review_text={
        'name_conflicts':'Conflicting verbatim equipment names; use referenced observation audit rows to inspect competing names and sources.',
        'id_collisions':'Distinct supported original IDs normalize to one key; review aliases before joining. No observations were merged.',
        'id_missing':'Missing IDs remain in fact tables without fictitious lookup records.',
        'id_unsupported':'Unsupported ID formats are retained literal text; unsupported does not mean an invalid identifier.',
        'equipment_other':'No equipment rule matched; Other requires departmental review.',
        'broad_equipment_keywords':'Vac, ICE or Trash substring matches may be overbroad; compatibility rules were not changed.',
        'kaivac_precedence':'Kaivac matches the earlier Vac rule; this accepted compatibility limitation is not a code failure.',
        'building_missing':'Location is blank; no Building was invented.',
        'building_unresolved':'Building remains unresolved; check source evidence and the departmental dimension.',
        'building_ambiguous':'Location is ambiguous under the conservative Building policy; no aliases or corrections applied.',
        'maintenance_uncertain':'Unclassified or Needs Review remains explicit; inspect source evidence rather than forcing Needed Repair.'}
    for key,text in review_text.items():checks.review(key,issues[key],text,dict(affected_observations=len(issues[key])))
    missing=[ref('repairs',i) for i,r in enumerate(canonical['repairs'],1) if not r['ReportedTotalCost']]
    checks.review('missing_repair_costs',missing,'Missing reported repair costs stay blank. Partial known totals are not complete source totals.',dict(rows=len(missing)))
    _dimension(checks,tables,dimension)
    checks.add('inventory_authority','REVIEW','Observed equipment covers only the selected history; it is not an authoritative complete inventory.',action='Confirm lookup coverage and aliases with the department.')


def _dimension(checks,tables,dimension):
    if dimension is None:
        checks.add('building_dimension','NOT TESTED','No Building dimension supplied; membership and unmatched/ambiguous dimension keys cannot be established.',action='Rerun with an owner-approved CSV containing the exact text Building column.')
        return
    rows=records(dimension)
    # No trimming, case folding, aliasing or numeric casting of dimension keys.
    if not rows:
        reader=csv.reader(io.StringIO(dimension.decode('utf-8-sig')));header=next(reader,[])
    else:header=list(rows[0])
    if 'Building' not in header:raise Rejected('building_dimension_column_missing')
    keys=Counter(row['Building'] for row in rows if row['Building'])
    duplicates=sum(n>1 for n in keys.values());blanks=sum(not row['Building'] for row in rows)
    checks.add('dimension_key_quality','REVIEW' if duplicates or blanks else 'PASS',
        'Dimension duplicate/blank keys are reported without changing the dimension.',
        dict(duplicate_keys=duplicates,blank_rows=blanks),action='Owner reviews dimension key quality before relationships.')
    unmatched=[];ambiguous=[]
    for kind in FACTS:
        for ordinal,row in enumerate(tables[kind],1):
            key=row['Building']
            if key and key not in keys:unmatched.append(ref(kind,ordinal))
            if key and keys[key]>1:ambiguous.append(ref(kind,ordinal))
    checks.review('building_dimension_unmatched',unmatched,'Nonblank Building keys unmatched by exact text in the supplied dimension.',dict(affected_observations=len(unmatched)))
    checks.review('building_dimension_ambiguous',ambiguous,'Fact Building keys refer to duplicate dimension keys; relationships require review.',dict(duplicate_dimension_keys=sum(n>1 for n in keys.values()),affected_observations=len(ambiguous)))
    checks.add('building_dimension_authority','NOT TESTED','Supplying a CSV does not authenticate departmental approval or prove relationship correctness.',action='Owner confirms dimension authority and validates relationships in a backup PBIX.')


def analyze(comparison,canonical,building_dimension=None):
    checks=Checks();captured=[];identity={}
    try:
        comparison,canonical=plain_path(comparison),plain_path(canonical)
        bundle=capture(comparison,EXPECTED_COMPARISON);source=capture(canonical,CANONICAL_FILES)
        captured=[(comparison,EXPECTED_COMPARISON,bundle),(canonical,CANONICAL_FILES,source)]
        dimension=read_bytes(building_dimension) if building_dimension is not None else None
        identity=dict(comparison_manifest_sha256=sha256(bundle['comparison_manifest.json']).hexdigest(),
            canonical_manifest_sha256=sha256(source['snapshot_manifest.json']).hexdigest(),
            building_dimension_sha256=sha256(dimension).hexdigest() if dimension is not None else None)
        _analyze(checks,comparison,canonical,bundle,source,dimension)
        stable=all(capture(root,names)==before for root,names,before in captured)
        if building_dimension is not None:stable=stable and read_bytes(building_dimension)==dimension
        checks.invariant('inputs_unchanged',stable,'All captured input bytes remain unchanged after analysis; no application write/generation API was called.')
    except (Rejected,OSError,ValueError,KeyError,TypeError,csv.Error,UnicodeError,OverflowError):
        checks.add('input_rejected','FAIL','Inputs are incomplete, unsupported, unsafe or structurally malformed; analysis cannot certify this bundle.',
            action='Verify paths/version/completeness and reproduce using disposable copies. No input was repaired.')
        checks.add('remaining_evidence','NOT TESTED','Remaining assertions and final stability checks may be incomplete after input rejection.',action='Provide complete supported inputs and rerun.')
    for key,text in [('business_accuracy','Business accuracy, source completeness and departmental policy approval require independent human evidence.'),
                     ('power_bi_runtime','Actual five-table M import, DAX, visuals and relationships have not been executed by this analyzer.'),
                     ('native_desktop','This data analyzer does not execute Windows or native desktop UI tests.')]:
        checks.add(key,'NOT TESTED',text,action='Follow the documented Windows/backup-PBIX acceptance procedure and record separate evidence.')
    counts=dict(Counter(c['status'] for c in checks.items));counts={k:counts.get(k,0) for k in STATUSES}
    overall='FAIL' if counts['FAIL'] else 'REVIEW' if counts['REVIEW'] else 'NOT TESTED' if counts['NOT TESTED'] else 'PASS'
    return dict(report_schema='edm-acceptance-v1',scope='ReadOnlyDevelopmentComparison',overall=overall,
        structurally_valid=not bool(counts['FAIL']),business_approved=False,
        executive_summary=f"{counts['PASS']} PASS, {counts['REVIEW']} REVIEW, {counts['FAIL']} FAIL, {counts['NOT TESTED']} NOT TESTED. Structural validation is not business approval.",
        counts=counts,checks=checks.items,input_fingerprints=identity,
        privacy='Aggregate months/approved labels, counts, schema names, fingerprints and CSV references; no identifying source cells, private paths or exception text.')


def markdown_report(report):
    lines=['# Equipment Data Manager acceptance report','',f"**Overall: {report['overall']}**",'',report['executive_summary'],'',
        'Business approval: **not established**. REVIEW findings are not automatically code defects.','',
        '| Check | Status | Finding | Next step |','|---|---|---|---|']
    for c in report['checks']:
        clean=lambda v:str(v).replace('|','/').replace('\n',' ')
        lines.append('| '+' | '.join(clean(c[k]) for k in ('id','status','summary','next_step'))+' |')
    identity={k:report[k] for k in ('report_schema','application_commit','application_tree_clean','platform','python','executable_sha256','input_fingerprints') if k in report}
    lines+=['','## Evidence identity','','```json',json.dumps(identity,sort_keys=True,indent=2),'```','','## Detailed counts and redacted references','']
    for c in report['checks']:
        if c['metrics'] or c['evidence']:
            lines += [f"### {c['id']}",'','```json',json.dumps(dict(metrics=c['metrics'],evidence=c['evidence'],evidence_total=c['evidence_total'],evidence_truncated=c['evidence_truncated']),sort_keys=True,indent=2),'```','']
    return '\n'.join(lines).rstrip()+'\n'


def write_reports(report,output,protected):
    output=plain_path(output)
    for value in protected:
        if value is None:continue
        path=plain_path(value)
        if output.is_relative_to(path) or path.is_relative_to(output):raise Rejected('report_destination_overlaps_input')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.mkdir(exist_ok=False)
    try:
        for name,raw in [('acceptance.json',json.dumps(report,sort_keys=True,indent=2)+'\n'),('acceptance.md',markdown_report(report))]:
            with (output/name).open('x',encoding='utf-8',newline='\n') as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
    except BaseException:
        shutil.rmtree(output)
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comparison',type=Path,required=True)
    parser.add_argument('--canonical',type=Path,required=True)
    parser.add_argument('--building-dimension',type=Path)
    parser.add_argument('--output',type=Path,help='NEW separate report directory; never overwrite or write inside an input')
    parser.add_argument('--format',choices=('json','markdown'),default='json',help='stdout format; --output always writes both')
    args=parser.parse_args(argv)
    report=analyze(args.comparison,args.canonical,args.building_dimension)
    if args.output:
        try:write_reports(report,args.output,(args.comparison,args.canonical,args.building_dimension))
        except (OSError,Rejected):
            print('Report destination rejected or unavailable. Inputs and existing reports were not overwritten.',file=__import__('sys').stderr)
            return 2
    print(json.dumps(report,sort_keys=True,indent=2) if args.format=='json' else markdown_report(report))
    return 1 if report['counts']['FAIL'] else 0


if __name__=='__main__':raise SystemExit(main())
