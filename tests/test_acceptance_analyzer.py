"""Adversarial invented acceptance bundles; production code is never edited."""
import csv
import io
import json
from hashlib import sha256
from pathlib import Path
import runpy
import shutil
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.acceptance import analyze_v3 as a
from tools.acceptance import reference as ref


@pytest.fixture(scope='module')
def invented(tmp_path_factory):
    root=tmp_path_factory.mktemp('acceptance-invented')/'demo'
    runpy.run_path('examples/create_comparison_classification_demo.py')['create_demo'](root)
    return root


@pytest.fixture
def bundle(invented,tmp_path):
    comparison=tmp_path/'comparison';canonical=tmp_path/'snapshot'
    shutil.copytree(invented/'comparison-1/comparison',comparison)
    shutil.copytree(invented/'canonical/snapshot',canonical)
    return comparison,canonical


def tree(root):return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
def check(report,key):return next(c for c in report['checks'] if c['id']==key)
def rows(path):return list(csv.DictReader(io.StringIO(path.read_text(),newline='')))


def edit(comparison,name,change,rehash=True):
    path=comparison/name;data=rows(path);change(data)
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    path.write_bytes(stream.getvalue().encode())
    if not rehash:return
    p=comparison/'comparison_manifest.json';m=json.loads(p.read_text())
    for entry in m['datasets']:
        if entry['file']==name:
            entry['sha256']=sha256(path.read_bytes()).hexdigest();entry['rows']=len(data)
            field='FirstObservedMonth' if name=='Equipment_History.csv' else 'ReportMonth'
            entry['rows_by_month']=a.monthly(data,field)
    for entry in m['diagnostics']:
        if entry['file']==name:entry['sha256']=sha256(path.read_bytes()).hexdigest()
    if m['lineage']['file']==name:m['lineage'].update(sha256=sha256(path.read_bytes()).hexdigest(),rows=len(data))
    p.write_text(json.dumps(m))


def test_valid_review_findings_readonly_redacted_and_business_not_approved(bundle):
    comparison,canonical=bundle;before=tree(comparison),tree(canonical)
    r=a.analyze(*bundle)
    assert r['counts']['FAIL']==0 and r['overall']=='REVIEW' and r['structurally_valid']
    assert not r['business_approved']
    assert r==a.analyze(*bundle)
    assert r['input_fingerprints']['canonical_manifest_sha256']==sha256((canonical/'snapshot_manifest.json').read_bytes()).hexdigest()
    assert check(r,'name_conflicts')['status']=='REVIEW'
    assert check(r,'maintenance_uncertain')['status']=='REVIEW'
    assert check(r,'id_unsupported')['status']=='REVIEW'
    assert check(r,'building_dimension')['status']=='NOT TESTED'
    assert check(r,'inputs_unchanged')['status']=='PASS'
    assert (tree(comparison),tree(canonical))==before
    text=json.dumps(r)+a.markdown_report(r)
    for private in ('E00045','Battery Backpack Vacuum','Old Buffer','Science and Technology Center 201',str(comparison)):
        assert private not in text
    assert sum(r['counts'].values())==len(r['checks'])


@pytest.mark.parametrize('name,change,failed_check',[
    ('Repairs_History.csv',lambda r:next(row for row in r if not row['ReportedTotalCost']).update(ReportedTotalCost='0.00'),'financial_repairs'),
    ('Repairs_History.csv',lambda r:r[0].update(RepairPersonHours='999'),'financial_repairs'),
    ('Repairs_History.csv',lambda r:r.append(dict(r[0])),'record_counts_repairs'),
    ('Repairs_History.csv',lambda r:r.pop(0),'record_counts_repairs'),
    ('Repairs_History.csv',lambda r:r.reverse(),'ordered_projection_repairs'),
    ('ServiceOrders_History.csv',lambda r:r[0].update(EquipmentId='R0000123'),'ordered_projection_service_orders'),
    ('ServiceOrders_History.csv',lambda r:r[0].update(EquipmentName='Private wrong name'),'ordered_projection_service_orders'),
    ('ServiceOrders_History.csv',lambda r:r[0].update(EquipmentType='Other'),'lookup_fact_service_orders'),
    ('ServiceOrders_History.csv',lambda r:r[0].update(MaintenanceType='Needed Repair'),'ordered_projection_service_orders'),
    ('ServiceOrders_History.csv',lambda r:r[0].update(Location='Private wrong location'),'ordered_projection_service_orders'),
    ('ServiceOrders_History.csv',lambda r:r[0].update(Building='Private wrong key'),'ordered_projection_service_orders'),
    ('Equipment_History.csv',lambda r:r.append(dict(r[0])),'equipment_unique'),
    ('Equipment_History.csv',lambda r:r[0].update(ObservationCount='999'),'equipment_resolution'),
    ('Equipment_History.csv',lambda r:r[0].update(EquipmentType='Ladder'),'equipment_resolution'),
    ('audit/lineage.csv',lambda r:r[0].update(CanonicalRecordNumber='999'),'complete_lineage'),
    ('audit/lineage.csv',lambda r:r.append(dict(r[0])),'complete_lineage'),
    ('audit/equipment_observations.csv',lambda r:r[0].update(OriginalDescription='Private fake source evidence'),'classification_source_evidence'),
])
def test_self_consistent_hashes_cannot_hide_independent_invariant_failures(bundle,monkeypatch,name,change,failed_check):
    comparison,canonical=bundle
    # Deliberately disable the shared producer's verifier: our assertions must fail independently.
    monkeypatch.setattr(a,'application_verification',lambda *_:'PASS')
    edit(comparison,name,change)
    r=a.analyze(*bundle)
    assert check(r,failed_check)['status']=='FAIL'
    if name in a.FILES.values() and name!='Equipment_History.csv' and len(rows(comparison/name))!=len(rows(canonical/name)):
        assert check(r,'complete_lineage')['status']=='FAIL'
    assert r['overall']=='FAIL' and not r['structurally_valid']


@pytest.mark.parametrize('name', ['Repairs_History.csv','comparison_warnings.txt','audit/diagnostics.csv','audit/classification_diagnostics.csv','audit/equipment_observations.csv','audit/lineage.csv'])
def test_each_dataset_audit_or_warning_hash_is_checked(bundle,name):
    comparison,canonical=bundle;p=comparison/name;p.write_bytes(p.read_bytes()+b'changed')
    r=a.analyze(*bundle);assert r['counts']['FAIL']>0


@pytest.mark.parametrize('change', ['order','type','rows','version','policy','boolean','nan','missing','unexpected','staging','json_array','duplicate_key'])
def test_incomplete_unsupported_or_malformed_inputs_rejected(bundle,change):
    comparison,canonical=bundle
    p=comparison/'comparison_manifest.json';m=json.loads(p.read_text())
    if change=='order':m['datasets'][0]['columns'].reverse()
    elif change=='type':m['datasets'][0]['columns'][0]['type']='integer'
    elif change=='rows':m['datasets'][0]['rows']=999
    elif change=='version':m['export_schema']='comparison-preview-v2'
    elif change=='policy':m['maintenance_type_policy']='future-unapproved'
    elif change=='boolean':edit(comparison,'Equipment_History.csv',lambda r:r[0].update(NameConflict='yes'));m=json.loads(p.read_text())
    elif change=='nan':edit(comparison,'Repairs_History.csv',lambda r:r[0].update(ReportedTotalCost='NaN'));m=json.loads(p.read_text())
    elif change=='missing':(comparison/'Equipment_History.csv').unlink()
    elif change=='unexpected':(comparison/'private-extra.txt').write_text('private data must not be read')
    elif change=='staging':comparison=comparison.rename(comparison.with_name('.s'))
    elif change=='json_array':m=[]
    elif change=='duplicate_key':p.write_text('{"export_schema":"comparison-preview-v3","export_schema":"comparison-preview-v3"}');m=None
    if m is not None:(comparison/'comparison_manifest.json').write_text(json.dumps(m))
    r=a.analyze(comparison,canonical);assert r['counts']['FAIL']>0
    assert 'private data must not be read' not in json.dumps(r)


def test_supplied_canonical_must_match_retained_copy(bundle,monkeypatch):
    comparison,canonical=bundle;monkeypatch.setattr(a,'application_verification',lambda *_:'PASS')
    p=canonical/'compatibility_report.md';p.write_bytes(p.read_bytes()+b'new independent report')
    m=canonical/'snapshot_manifest.json';j=json.loads(m.read_text());j['compatibility_report_sha256']=sha256(p.read_bytes()).hexdigest();m.write_text(json.dumps(j))
    r=a.analyze(*bundle);assert check(r,'source_association')['status']=='FAIL'


def test_building_dimension_exact_keys_duplicates_blanks_and_unmatched_are_review(bundle,tmp_path):
    dimension=tmp_path/'approved-synthetic-building.csv';dimension.write_text('Building\nMC\nMC\nLibrary\n""\n')
    r=a.analyze(*bundle,dimension)
    assert r['counts']['FAIL']==0
    assert check(r,'building_dimension_unmatched')['status']=='REVIEW'
    assert check(r,'building_dimension_ambiguous')['status']=='REVIEW'
    assert check(r,'building_dimension_authority')['status']=='NOT TESTED'
    assert 'MC' not in json.dumps(r)


def test_building_dimension_header_error_does_not_leak_private_cells(bundle,tmp_path):
    dimension=tmp_path/'private-dimension.csv';dimension.write_text('SecretHeader\nSecretPrivateCell\n')
    r=a.analyze(*bundle,dimension);assert r['counts']['FAIL']>0
    assert 'Secret' not in json.dumps(r)


def test_report_outputs_are_explicit_new_separate_and_leave_inputs_unchanged(bundle,tmp_path):
    comparison,canonical=bundle;before=tree(comparison),tree(canonical);r=a.analyze(*bundle)
    destination=tmp_path/'reports'
    a.write_reports(r,destination,bundle)
    assert json.loads((destination/'acceptance.json').read_text())==r
    assert (destination/'acceptance.md').read_text()==a.markdown_report(r)
    assert (tree(comparison),tree(canonical))==before
    with pytest.raises(FileExistsError):a.write_reports(r,destination,bundle)
    for target in (comparison/'reports',canonical/'reports',tmp_path):
        with pytest.raises(a.Rejected):a.write_reports(r,target,bundle)


def test_report_failure_cleanup_owns_only_new_directory(bundle,tmp_path,monkeypatch):
    r=a.analyze(*bundle);destination=tmp_path/'reports';before=tree(bundle[0]);opening=Path.open
    def failing(path,*args,**kwargs):
        if path==destination/'acceptance.md':raise OSError('Synthetic private error')
        return opening(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',failing)
    with pytest.raises(OSError):a.write_reports(r,destination,bundle)
    assert not destination.exists() and tree(bundle[0])==before


def test_linked_input_and_output_ancestors_rejected_without_windows_privilege(bundle,tmp_path,monkeypatch):
    parent=tmp_path/'redirected';parent.mkdir();old=Path.is_symlink
    monkeypatch.setattr(Path,'is_symlink',lambda p:True if p==parent else old(p))
    with pytest.raises(a.Rejected):a.write_reports(a.analyze(*bundle),parent/'reports',bundle)
    old_root=bundle[0]
    monkeypatch.setattr(Path,'is_symlink',lambda p:p==old_root)
    r=a.analyze(*bundle);assert r['counts']['FAIL']>0


def test_cli_formats_reports_and_fail_exit_status(bundle,tmp_path,capsys):
    comparison,canonical=bundle
    args=['--comparison',str(comparison),'--canonical',str(canonical)]
    assert a.main(args+['--output',str(tmp_path/'reports')])==0
    assert json.loads(capsys.readouterr().out)['business_approved'] is False
    assert a.main(args+['--format','markdown'])==0
    assert '# Equipment Data Manager acceptance report' in capsys.readouterr().out
    assert a.main(args+['--output',str(comparison/'reports')])==2
    capsys.readouterr()
    (comparison/'Equipment_History.csv').unlink()
    assert a.main(args)==1
    assert json.loads(capsys.readouterr().out)['overall']=='FAIL'


@pytest.mark.parametrize('tag,original,expected',[
    ('PM','','Preventive Maintenance'),('Repair','','Needed Repair'),('','shipment','Unclassified'),
    ('','equipment','Unclassified'),('PM','broken motor','Needs Review'),('','No PM','Needs Review'),
    ('','PM?','Needs Review'),('','annual inspection','Preventive Maintenance'),('','replace broken motor','Needed Repair')])
def test_independent_maintenance_reference_known_answers(tag,original,expected):
    assert ref.maintenance(tag,original,'')[0]==expected


@pytest.mark.parametrize('name,expected', [('Kaivac','Vacuum'),('Office cart','Scrubber'),('Trash can','Vacuum Trash can'),('Puzzi','Vacuum'),('Unknown','Other')])
def test_independent_equipment_reference_known_answers(name,expected):
    assert ref.equipment(name)[0]==expected


@pytest.mark.parametrize('mutation,check_id', [('boolean_as_integer','development_contract'),('count_as_boolean','dataset_repair_financial_summary')])
def test_documented_verifier_type_coercion_is_rejected_independently(bundle,mutation,check_id):
    from equipment_data_manager.comparison_export import validate_comparison
    comparison,canonical=bundle;p=comparison/'comparison_manifest.json';m=json.loads(p.read_text())
    if mutation=='boolean_as_integer':m['production_ready']=0
    else:
        entry=next(e for e in m['datasets'] if e['report_type']=='repair_financial_summary')
        first=next(iter(entry['rows_by_month']));assert entry['rows_by_month'][first]==1
        entry['rows_by_month'][first]=True
    p.write_text(json.dumps(m))
    # Owner-approved strict metadata fix; independent rejection remains required.
    from equipment_data_manager.processing.models import ProcessingError
    with pytest.raises(ProcessingError,match='comparison_contract_rejected'):
        validate_comparison(comparison)
    r=a.analyze(*bundle)
    assert check(r,check_id)['status']=='FAIL'


@pytest.mark.parametrize('field', ['ReportMonth','MaintenanceType'])
def test_malformed_aggregate_labels_cannot_leak_private_values_into_reports(bundle,field):
    comparison,canonical=bundle
    private='PrivateCellMustNeverAppearInAnAggregate'
    edit(comparison,'ServiceOrders_History.csv',lambda r:r[0].update({field:private}))
    r=a.analyze(*bundle)
    assert r['counts']['FAIL']>0
    assert private not in json.dumps(r) and private not in a.markdown_report(r)
