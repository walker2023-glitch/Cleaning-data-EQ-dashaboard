"""Comparison v2 enrichment only; canonical/financial behavior remains unchanged."""
import io
import json
from pathlib import Path
import re

import pytest

from equipment_data_manager import comparison_export as module
from equipment_data_manager.comparison_enrichment import (
    normalize_equipment_id, resolve_building, legacy_building, DIAGNOSTIC_FIELDS, EVIDENCE_FIELDS,
)
from equipment_data_manager.processing.models import ProcessingError
from test_comparison_export import tree, rows


@pytest.mark.parametrize('original,expected,status', [
    ('R 123','R123','normalized'), ('E 456','E456','normalized'), ('Z 007','Z007','normalized'),
    ('R123','R123','unchanged'), ('E 00045','E00045','normalized'), ('E00045','E00045','unchanged'),
    ('Z\t\t007','Z007','normalized'), ('R\u00a0123','R123','normalized'), ('E\u2003001','E001','normalized'),
    ('R\n123','R123','normalized'), ('R 0','R0','normalized'), ('','', 'missing'), (' \t','', 'missing'),
    ('Q 123','Q 123','unsupported'), ('r 123','r 123','unsupported'), ('00045','00045','unsupported'),
    ('R-123','R-123','unsupported'), ('R 12 3','R 12 3','unsupported'), (' R 123',' R 123','unsupported'),
    ('R 123 ','R 123 ','unsupported'), ('R１２３','R１２３','unsupported'), ('RE 123','RE 123','unsupported'),
])
def test_equipment_id_narrow_normalization_preserves_text(original,expected,status):
    result=normalize_equipment_id(original)
    assert (result.value,result.status)==(expected,status)


@pytest.mark.parametrize('location,recognized,building,status', [
    ('MC 188',(), 'MC','room_pattern'), ('Library 204',(), 'Library','room_pattern'),
    ('STC 101A',(), 'STC','room_pattern'), ('Ricks 125',(), 'Ricks','room_pattern'),
    ('Science and Technology Center 201',(), 'Science and Technology Center','room_pattern'),
    ('Science & Technology Center 201',(), 'Science & Technology Center','room_pattern'),
    ('Smith-Jones 201B',(), 'Smith-Jones','room_pattern'), ("O'Brien 204",(), "O'Brien",'room_pattern'),
    ('M.C. 188',(), 'M.C.','room_pattern'), (' MC 188 ',(), 'MC','room_pattern'),
    ('MC\t188',(), 'MC','room_pattern'), ('MC',('MC',), 'MC','observed_building_only'),
    ('MC',(), '', 'unresolved'), ('Library',('Library',), 'Library','observed_building_only'),
    ('mc',('MC',), '', 'unresolved'), ('',(), '', 'missing'), ('  ',(), '', 'missing'),
    ('Building 2 101',(), '', 'ambiguous'), ('Building 2',(), '', 'ambiguous'),
    ('2nd Building 201',(), '', 'ambiguous'), ('MC 188/190',(), '', 'ambiguous'),
    ('MC / STC 188',(), '', 'ambiguous'), ('MC - 188',(), '', 'ambiguous'),
    ('MC 188, STC 101',(), '', 'ambiguous'), ('MC188',(), '', 'ambiguous'),
    ('MC 101AB',(), '', 'ambiguous'), ('Outdoor',(), '', 'unresolved'),
    ('Room 188',(), '', 'ambiguous'), ('MC\n188',(), '', 'ambiguous'),
    ('MC\n',('MC',), '', 'ambiguous'),
])
def test_building_conservative_format_and_observed_only_names(location,recognized,building,status):
    result=resolve_building(location,recognized)
    assert (result.value,result.status)==(building,status)


def test_separate_legacy_references_are_not_forced_to_agree():
    assert legacy_building('MC 188','repairs')[0]=='MC'
    assert legacy_building('MC 188','service_orders')[0]=='MC'
    assert legacy_building('Building 2 101','repairs')[0]=='Building'
    assert legacy_building('Building 2 101','service_orders')[0]=='Building 2'
    assert resolve_building('Building 2 101').value==''


@pytest.fixture
def enriched_source(tmp_path):
    from test_historical_processing import prepare,preview,plan_for,execute
    from test_repair_financial import raw_report
    from report_samples import service_csv
    from equipment_data_manager.historical_dataset import preview_dataset
    from test_historical_dataset import build
    workspace,_,_=prepare(tmp_path)
    folder=workspace.raw_folder/'2026/2026-01 (January)'
    repair=module._rows(raw_report(count=8,costs=['$0.00','','bad','$10.00','$0.00','$0.00','$0.00','$0.00']))
    ids=['R 123','E 00045','Z007','R123','','Q 123','000439','R 123']
    locations=['MC 188','Science and Technology Center 201','MC','Building 2 101','','STC 101A','MC / STC 188','MC 188']
    for row,identifier,location in zip(repair,ids,locations):
        row['PersonnelId1']='Equipment Id: '+identifier
        row['PersonnelId4']='Location: '+location
    (folder/'CompuClean Repair Report.csv').write_bytes(module._encode(repair,list(repair[0])))
    services=module._rows(service_csv(count=3))
    for row,identifier,location in zip(services,['R123','E00045','X-7'],['Library 204','Ricks 125','STC 101A']):
        row.update(EquipmentId1=identifier,Name=location)
    (folder/'CompuClean Service Orders List.csv').write_bytes(module._encode(services,list(services[0])))
    inventory,batch=preview(workspace,'2026-01','2026-01')
    run=execute(workspace,inventory,plan_for(workspace,inventory,batch))
    assert run.summary['created']==3
    plan=preview_dataset(workspace,'2026-01','2026-01')
    return workspace,build(workspace,plan,tmp_path/'canonical')


def create(source,target,**kwargs):
    return module.generate_comparison(source[0],source[1],target,confirmed=True,**kwargs)


def test_v2_determinism_collisions_originals_counts_lineage_and_financial_nulls(enriched_source,tmp_path):
    workspace,canonical=enriched_source
    before,candidates,raw=tree(canonical),tree(workspace.candidate_folder),tree(workspace.raw_folder)
    first,second=[create(enriched_source,tmp_path/f'out-{i}') for i in (1,2)]
    assert tree(first)==tree(second)
    manifest=module.validate_comparison(first)
    assert manifest['export_schema']=='comparison-preview-v2'
    assert manifest['warning_counts']==dict(normalized_rows=3,collision_groups=2,collision_rows=6,
        unsupported_ids=3,missing_ids=1,unresolved_buildings=3,legacy_building_differences=2)
    assert tree(canonical)==before==tree(first/'audit/canonical')
    assert tree(workspace.candidate_folder)==candidates and tree(workspace.raw_folder)==raw
    evidence=rows(first/'audit/lineage.csv')
    assert list(evidence[0])==list(module.LINEAGE_FIELDS+EVIDENCE_FIELDS)
    for kind,name in module.NAMES.items():
        original,result=rows(canonical/name),rows(first/name)
        assert len(original)==len(result)
        assert list(result[0])==list(module.FIELDS_V2[kind])
        for ordinal,(old,new) in enumerate(zip(original,result),1):
            assert all(old[key]==new[key] for key in module.FIELDS[kind] if key!='EquipmentId')
            link=next(r for r in evidence if r['Dataset']==name and r['ExportRecordNumber']==str(ordinal))
            assert link['CanonicalRecordNumber']==str(ordinal) and link['RecordId']==old.get('RecordId','')
            if kind in ('repairs','service_orders'):
                assert link['CanonicalEquipmentId']==old['EquipmentId']
                assert link['RawEquipmentId']==new['RawEquipmentId']==old['RawEquipmentId']
                assert link['Location']==new['Location']==old['Location']
    repairs=rows(first/module.NAMES['repairs'])
    assert [r['EquipmentId'] for r in repairs]==['R123','E00045','Z007','R123','','Q 123','000439','R123']
    assert repairs[0]==repairs[7] and len(repairs)==8  # Truly repeated projected transactions stay.
    assert [r['ReportedTotalCost'] for r in repairs[:3]]==['0.00','','']
    assert repairs[2]['Building']=='MC' and repairs[3]['Building']==''
    issues=rows(first/'audit/diagnostics.csv')
    assert list(issues[0])==list(DIAGNOSTIC_FIELDS)
    collisions=[r for r in issues if r['Issue']=='id_collision']
    assert len(collisions)==6
    assert all(json.loads(r['OriginalVariants'])==['R 123','R123'] for r in collisions if r['EquipmentId']=='R123')
    assert {r['Issue'] for r in issues}>={'id_missing','id_unsupported','building_ambiguous','legacy_building_difference'}
    report=(first/module.WARNINGS_NAME).read_text()
    assert 'ID collisions: 2 group(s), 6 row(s)' in report and 'not validated Building_Dim' in report
    assert 'sha256' not in report.lower()
    assert 'Building' not in rows(first/module.NAMES['tma_work_orders'])[0]


def test_v1_is_still_valid_and_keeps_original_equipment_ids(enriched_source,tmp_path):
    output=create(enriched_source,tmp_path/'v1',export_schema=module.EXPORT_SCHEMA)
    assert module.validate_comparison(output)['export_schema']=='comparison-preview-v1'
    assert rows(output/'Repairs_History.csv')[0]['EquipmentId']=='R 123'
    assert 'Building' not in rows(output/'Repairs_History.csv')[0]
    assert not (output/module.WARNINGS_NAME).exists()
    assert not (output/module.DIAGNOSTICS_NAME).exists()


@pytest.mark.parametrize('artifact',[module.DIAGNOSTICS_NAME,module.WARNINGS_NAME,'audit/lineage.csv','Repairs_History.csv'])
def test_v2_changed_outputs_or_warnings_are_rejected(enriched_source,tmp_path,artifact):
    output=create(enriched_source,tmp_path/'out')
    path=output/artifact;path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ProcessingError):module.validate_comparison(output)


@pytest.mark.parametrize('fault',['write_diagnostic','write_warning','cancel','rename','verify'])
def test_v2_failures_keep_inputs_and_previous_outputs(enriched_source,tmp_path,monkeypatch,fault):
    previous=create(enriched_source,tmp_path/'previous')
    before,source_before=tree(previous),tree(enriched_source[1])
    write,rename=module._write,Path.rename
    stopped=[];target=tmp_path/'new'
    def writing(path,raw):
        write(path,raw)
        if path.name=='diagnostics.csv':
            if fault=='write_diagnostic':raise OSError('Synthetic failure')
            if fault=='cancel':stopped.append(True)
        if path.name==module.WARNINGS_NAME and fault=='write_warning':raise OSError('Synthetic failure')
    def renaming(path,other):
        if path==target/'.s' and fault=='rename':raise OSError('Synthetic failure')
        return rename(path,other)
    def invalid(_):raise ProcessingError('comparison_contract_rejected')
    monkeypatch.setattr(module,'_write',writing);monkeypatch.setattr(Path,'rename',renaming)
    if fault=='verify':monkeypatch.setattr(module,'validate_comparison',invalid)
    with pytest.raises((OSError,ProcessingError)):create(enriched_source,target,cancelled=lambda:bool(stopped))
    assert not target.exists() and tree(previous)==before and tree(enriched_source[1])==source_before


def test_v2_collision_cannot_overwrite_and_unknown_contract_cannot_write(enriched_source,tmp_path):
    previous=create(enriched_source,tmp_path/'out');before=tree(previous)
    with pytest.raises(ProcessingError,match='destination_exists'):create(enriched_source,tmp_path/'out')
    assert tree(previous)==before
    with pytest.raises(ProcessingError,match='version_unsupported'):create(enriched_source,tmp_path/'other',export_schema='unknown')
    assert not (tmp_path/'other').exists()


def test_v2_source_integrity_failure_creates_nothing(enriched_source,tmp_path):
    source=enriched_source[1]/'Repairs_History.csv'
    source.write_bytes(source.read_bytes()+b'bad')
    with pytest.raises(ProcessingError):create(enriched_source,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_v2_helper_exact_columns_types_and_rejects_v1():
    text=Path('powerquery/fnReadComparisonPreviewV2.pq').read_text()
    for kind in module.FIELDS_V2:
        body=re.search(r'\b'+kind+r' = \{([^\n]+)\}',text).group(1)
        assert re.findall(r'\{"([^"]+)", "([^"]+)"',body)==[(c.name,c.data_type) for c in module.schema(kind,module.LATEST_SCHEMA)]
    assert 'comparison-preview-v2' in text and 'comparison-preview-v1' not in text
    assert 'Folder.Files' not in text and 'type nullable number' in text
