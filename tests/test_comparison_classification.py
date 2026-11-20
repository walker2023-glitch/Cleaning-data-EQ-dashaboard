"""Milestone 1c: invented data only, including adversarial uncertainty/integrity."""
from copy import deepcopy
import json
from pathlib import Path
import re

import pytest

from equipment_data_manager import comparison_export as export
from equipment_data_manager.comparison_classification import (
    EQUIPMENT_RULES, classify_records, equipment_type, maintenance_type, normalize_name, validate_lookup,
)
from equipment_data_manager.comparison_enrichment import enrich_records
from equipment_data_manager.processing.models import ProcessingError
from test_comparison_enrichment import enriched_source
from test_comparison_export import tree, rows


@pytest.mark.parametrize('name,expected', [
    ('Battery Backpack Vacuum','Battery-powered backpack vacuum'),
    ('BATTERY VAC','Battery-powered vacuum'),('Backpack','Backpack Vacuum'),
    ('Trash Can','Vacuum Trash can'),('Vacuum','Vacuum'),('Versamatic','Vacuum'),
    ('Lindhaus','Vacuum'),('Puzzi','Vacuum'),('puzi','Vacuum'),('PuZZi','Vacuum'),
    ('Carpet Cleaner Head','Carpet Cleaner Head'),('Carpet Cleaning Machine','Carpet Cleaning Machine'),
    ('Carpet Cleaning','Carpet Cleaning'),('Extractor','Carpet Cleaning'),
    ('Upholstery Cleaner','Upholstery Cleaner'),('Upholstery','Upholstery machine'),
    ('Scrubber','Scrubber'),('i18B','Scrubber'),('ICE','Scrubber'),('Nautilus','Scrubber'),
    ('Burnisher','Burnisher'),('Buffer','Buffer'),('Chariot','Chariot'),('Agitator','Agitator'),
    ('Swing Arm','Swing Arm'),('RX-20','Swing Arm'),('Kaivac','Vacuum'),
    ('Dispenser','Chemical Dispenser'),('Chemical','Chemical Dispenser'),('Mop Station','Chemical Dispenser'),
    ('Fan','Floor Fan'),('Waxie','Floor Fan'),('Ladder','Ladder'),('Lift','Lift'),('Steamer','Steamer'),
    ('','Other'),('Unidentified','Other'),('Battery trash backpack','Battery-powered backpack vacuum'),
    ('Vac Carpet Cleaner Head','Vacuum'),('Office Cart','Scrubber'),('Trash Lift','Vacuum Trash can'),
])
def test_dax_ordered_equipment_compatibility(name,expected):
    assert equipment_type(name)[0]==expected
    assert equipment_type(name.swapcase())[0]==expected


def test_unreachable_kaivac_rule_and_broad_terms_are_preserved_and_flagged():
    assert 'Kaivac' in [label for label,_ in EQUIPMENT_RULES]
    assert equipment_type('Kaivac')==('Vacuum','equipment-rule-05',['vac'])
    assert equipment_type('Office Cart')[2]==['ice']
    assert equipment_type('Trash Cart')[2]==['trash']
    assert normalize_name('Puzzi puzzi PuZZi')=='Puzi puzi PuZi'


@pytest.mark.parametrize('tag,original,cleaned,expected', [
    ('PM','','','Preventive Maintenance'),('Repair','','','Needed Repair'),
    ('preventative maintenance','','','Preventive Maintenance'),
    ('','Annual inspection','','Preventive Maintenance'),('','routine tune-up','','Preventive Maintenance'),
    ('','preventive maintenance','','Preventive Maintenance'),('','preventative service','','Preventive Maintenance'),
    ('','quarterly scheduled service','','Preventive Maintenance'),('','PM check','','Preventive Maintenance'),
    ('','equipment cart','','Unclassified'),('','shipment received','','Unclassified'),
    ('','','','Unclassified'),('','Checked cart','','Unclassified'),
    ('','Repair motor','','Needed Repair'),('','Replace failed motor','','Needed Repair'),
    ('','Broken and leaking','','Needed Repair'),('','PM and repair motor','','Needs Review'),
    ('PM','broken motor','','Needs Review'),('Repair','annual inspection','','Needs Review'),
    ('','no repair needed','','Needs Review'),('','not scheduled for PM','','Needs Review'),
    ('','without inspection','','Needs Review'),('','cancelled annual inspection','','Needs Review'),
    ('','No PM needed','PM needed','Needs Review'),('','','routine service','Preventive Maintenance'),
    ('','routine service','repair','Needs Review'),('Review','','','Needs Review'),
    ('','PM?','','Needs Review'),('','possibly repair motor','','Needs Review'),
    ('','check if inspection needed','','Needs Review'),('','replacing motor','','Needed Repair'),
    ('PM','','replace motor','Needs Review'),('repair','fixed leak','repair','Needed Repair'),
])
def test_maintenance_evidence(tag,original,cleaned,expected):
    label,evidence=maintenance_type(tag,original,cleaned)
    assert label==expected
    assert json.loads(evidence)['original']==original


def observation(identifier='E00045',name='Old Buffer',month='2026-01',record='a',**kw):
    return dict(EquipmentId=identifier,EquipmentName=name,ReportMonth=month,RecordId=record,
        RawEquipmentId=identifier,Location='MC 188',Description='',**kw)


def classified(repairs,services):
    canonical=dict(repairs=repairs,service_orders=services,tma_work_orders=[],repair_financial_summary=[])
    tables,*_=enrich_records(canonical,export.NAMES)
    return classify_records(tables,export.NAMES)


def test_lookup_resolution_observations_blanks_and_shared_fact_names():
    repairs=[observation(identifier='E 00045'),observation(name='New Puzzi',month='2026-03'),
        observation(identifier='',name='Fan'),observation(name='New Puzzi',month='2026-03'),
        observation(identifier='00045',name='Ladder'),observation(name='',month='2026-06')]
    services=[observation(name='Service Scrubber',month='2026-03',record='0',RawDescription='PM',SourceMaintenanceTag='PM')]
    original=deepcopy([repairs,services])
    tables,evidence,audit,diagnostics,counts,links=classified(repairs,services)
    assert [repairs,services]==original
    assert len(tables['equipment'])==2
    lookup={r['EquipmentId']:r for r in tables['equipment']}
    item=lookup['E00045']
    assert item==dict(EquipmentId='E00045',EquipmentName='New Puzi',EquipmentType='Vacuum',
        FirstObservedMonth='2026-01',LastObservedMonth='2026-06',ObservationCount='5',NameConflict='true')
    assert lookup['00045']['EquipmentType']=='Ladder'  # Names never merge distinct IDs.
    assert tables['repairs'][2]['EquipmentId']=='' and len(tables['repairs'])==6
    assert len(links)==6 and len(audit)==7
    assert all(r['EquipmentName']=='New Puzi' and r['EquipmentType']=='Vacuum'
        for kind in ('repairs','service_orders') for r in tables[kind] if r['EquipmentId']=='E00045')
    assert tables['repairs'][0]['ObservedEquipmentName']=='Old Buffer'
    assert tables['service_orders'][0]['MaintenanceType']=='Preventive Maintenance'
    assert tables['repairs'][0]['MaintenanceType']=='Unclassified'  # No report-type defaults.
    assert counts['name_conflict_rows']==5
    assert {r['Issue'] for r in diagnostics}>={'equipment_name_conflict','maintenance_unclassified'}


def test_stable_source_identifier_ties_not_input_order():
    a=observation(name='Ladder',record='z');b=observation(name='Fan',record='a')
    left=classified([a,b],[])[0]['equipment']
    right=classified([b,a],[])[0]['equipment']
    assert left==right and left[0]['EquipmentName']=='Fan'
    assert classified([observation(name='')],[observation(name='Steamer')])[0]['equipment'][0]['EquipmentName']=='Steamer'


def test_latest_month_and_all_blank_names():
    lookup=classified([observation(name='Buffer'),observation(name='Lift',month='2026-02')],[])[0]['equipment']
    assert lookup[0]['EquipmentName']=='Lift'
    lookup=classified([observation(name='')],[observation(name=' ')])[0]['equipment']
    assert lookup[0]['EquipmentName']=='' and lookup[0]['EquipmentType']=='Other'


@pytest.mark.parametrize('change',['type','name','count','key','duplicate','missing','extra'])
def test_lookup_fact_mismatch_is_blocking(change):
    tables=classified([observation()],[])[0]
    if change in ('type','name','count','key'):
        key={'type':'EquipmentType','name':'EquipmentName','count':'ObservationCount','key':'EquipmentId'}[change]
        tables['equipment'][0][key]='wrong'
    elif change=='duplicate':tables['equipment'].append(dict(tables['equipment'][0]))
    elif change=='missing':tables['equipment']=[]
    else:tables['equipment'].append(dict(tables['equipment'][0],EquipmentId='extra'))
    with pytest.raises(ProcessingError,match='equipment_mismatch'):validate_lookup(tables)


def make(source,target,**kw):
    return export.generate_comparison(*source,target,confirmed=True,**kw)


def test_v3_full_export_determinism_schema_lineage_finance_and_integrity(enriched_source,tmp_path):
    workspace,canonical=enriched_source
    before=[tree(p) for p in (workspace.raw_folder,workspace.candidate_folder,canonical)]
    first,second=[make(enriched_source,tmp_path/f'out-{i}') for i in (1,2)]
    assert tree(first)==tree(second)
    manifest=export.validate_comparison(first)
    assert manifest['export_schema']=='comparison-preview-v3'
    assert len(manifest['datasets'])==5
    assert all(key in manifest for key in ('equipment_name_policy','equipment_type_policy','maintenance_type_policy'))
    evidence=rows(first/'audit/lineage.csv')
    assert len(evidence)==manifest['lineage']['rows']
    for kind,name in export.NAMES_V3.items():
        result=rows(first/name)
        assert list(result[0])==list(export.FIELDS_V3[kind])
        if kind=='equipment':continue
        old=rows(canonical/name)
        assert len(old)==len(result)
        for ordinal,(a,b) in enumerate(zip(old,result),1):
            assert all(a[k]==b[k] for k in export.FIELDS[kind] if k not in ('EquipmentId','EquipmentName'))
            link=next(e for e in evidence if e['Dataset']==name and e['ExportRecordNumber']==str(ordinal))
            assert link['RecordId']==a.get('RecordId','') and link['CanonicalRecordNumber']==str(ordinal)
            assert link['CanonicalDataset']==name
            if kind in ('repairs','service_orders'):assert b['ObservedEquipmentName']==a['EquipmentName']
    facts=[r for k in ('repairs','service_orders') for r in rows(first/export.NAMES[k])]
    for ordinal,item in enumerate(rows(first/'Equipment_History.csv'),1):
        contributors=[r for r in facts if r['EquipmentId']==item['EquipmentId']]
        links=[r for r in evidence if r['Dataset']=='Equipment_History.csv' and r['ExportRecordNumber']==str(ordinal)]
        assert len(contributors)==int(item['ObservationCount'])==len(links)
        for link in links:
            old=rows(canonical/link['CanonicalDataset'])[int(link['CanonicalRecordNumber'])-1]
            assert old['RecordId']==link['RecordId']
    repair=rows(first/'Repairs_History.csv')
    assert repair[0]==repair[7] and len(repair)==8
    assert [r['ReportedTotalCost'] for r in repair[:3]]==['0.00','','']
    assert len(rows(first/'audit/equipment_observations.csv'))==len(facts)
    assert before==[tree(p) for p in (workspace.raw_folder,workspace.candidate_folder,canonical)]
    assert tree(first/'audit/canonical')==before[-1]


@pytest.mark.parametrize('artifact',['Equipment_History.csv',export.OBSERVATIONS_NAME,export.CLASSIFICATION_NAME,'audit/lineage.csv','comparison_manifest.json'])
def test_v3_tamper_rejected(enriched_source,tmp_path,artifact):
    out=make(enriched_source,tmp_path/'out');p=out/artifact;p.write_bytes(p.read_bytes()+b'bad')
    with pytest.raises(ProcessingError):export.validate_comparison(out)


@pytest.mark.parametrize('fault',['observations','classifications','equipment','cancel','rename','validate'])
def test_v3_failure_cleanup_preserves_sources_and_previous(enriched_source,tmp_path,monkeypatch,fault):
    previous=make(enriched_source,tmp_path/'previous');before=tree(previous);source=tree(enriched_source[1])
    write,rename=export._write,Path.rename;stopped=[]
    def writing(path,raw):
        write(path,raw)
        match={'observations':'equipment_observations.csv','classifications':'classification_diagnostics.csv','equipment':'Equipment_History.csv'}
        if path.name==match.get(fault):raise OSError('synthetic')
        if fault=='cancel' and path.name=='Equipment_History.csv':stopped.append(True)
    def renaming(path,other):
        if fault=='rename':raise OSError('synthetic')
        return rename(path,other)
    def invalid(_):raise ProcessingError('synthetic_validation')
    monkeypatch.setattr(export,'_write',writing);monkeypatch.setattr(Path,'rename',renaming)
    if fault=='validate':monkeypatch.setattr(export,'validate_comparison',invalid)
    with pytest.raises((ProcessingError,OSError)):make(enriched_source,tmp_path/'out',cancelled=lambda:bool(stopped))
    assert not (tmp_path/'out').exists() and tree(previous)==before and tree(enriched_source[1])==source


def test_v3_source_corruption_destination_collision_and_bad_contract(enriched_source,tmp_path):
    out=make(enriched_source,tmp_path/'out');before=tree(out)
    with pytest.raises(ProcessingError,match='destination_exists'):make(enriched_source,tmp_path/'out')
    assert tree(out)==before
    with pytest.raises(ProcessingError,match='version_unsupported'):make(enriched_source,tmp_path/'bad',export_schema='v4')
    source=enriched_source[1]/'Repairs_History.csv';source.write_bytes(source.read_bytes()+b'bad')
    with pytest.raises(ProcessingError):make(enriched_source,tmp_path/'corrupt')
    assert not (tmp_path/'corrupt').exists()


def test_empty_equipment_is_header_only_and_m_helper_accepts_it():
    tables=classified([observation(identifier='')],[])[0]
    assert tables['equipment']==[]
    helper=Path('powerquery/fnReadComparisonPreviewV3.pq').read_text()
    assert 'Table.RowCount(Csv) >= 1' in helper


def test_powerquery_v3_explicit_ordered_schemas_types_and_contract():
    text=Path('powerquery/fnReadComparisonPreviewV3.pq').read_text()
    for kind in export.FIELDS_V3:
        body=re.search(r'\b'+kind+r' = \{([^\n]+)\}',text).group(1)
        assert re.findall(r'\{"([^"]+)", "([^"]+)"',body)==[(c.name,c.data_type) for c in export.schema(kind,export.LATEST_SCHEMA)]
    assert 'comparison-preview-v3' in text and 'comparison-preview-v2' not in text
    assert 'type logical' in text and 'FirstObservedMonth' in text
    assert 'Folder.Files' not in text and 'type nullable number' in text
