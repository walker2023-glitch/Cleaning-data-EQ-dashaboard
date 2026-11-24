"""Exact JSON scalar types; generated contracts and dataset bytes stay unchanged."""
import json
from pathlib import Path

import pytest

from equipment_data_manager.comparison_export import generate_comparison,validate_comparison
from equipment_data_manager.historical_dataset import preview_dataset,validate_dataset,NAMES
from equipment_data_manager.processing.models import ProcessingError
from test_historical_dataset import selected,build


@pytest.fixture(scope='module')
def bundles(tmp_path_factory):
    root=tmp_path_factory.mktemp('strict-manifest');w=selected(root,(1,2))
    canonical=build(w,preview_dataset(w,'2026-01','2026-02'),root/'canonical')
    comparisons={version:generate_comparison(w,canonical,root/version,confirmed=True,
        export_schema='comparison-preview-'+version) for version in ('v1','v2','v3')}
    return canonical,comparisons


def mutate(path,parts,value):
    document=json.loads(path.read_bytes());node=document
    for part in parts[:-1]:node=node[part]
    if type(value) is float:value=float(node[parts[-1]])  # Equal value, wrong JSON scalar type.
    node[parts[-1]]=value
    path.write_text(json.dumps(document),encoding='utf-8')


def copy_bundle(source,target):
    import shutil
    return Path(shutil.copytree(source,target))


@pytest.mark.parametrize('version',['v1','v2','v3'])
def test_valid_generated_manifests_and_reordered_keys_remain_compatible(bundles,tmp_path,version):
    canonical,comparisons=bundles;comparison=copy_bundle(comparisons[version],tmp_path/'comparison')
    before={p.relative_to(comparison):p.read_bytes() for p in comparison.rglob('*') if p.is_file()}
    m=validate_comparison(comparison);assert m['export_schema']=='comparison-preview-'+version
    assert validate_dataset(canonical)['complete'] is True
    assert before=={p.relative_to(comparison):p.read_bytes() for p in comparison.rglob('*') if p.is_file()}
    manifest=comparison/'comparison_manifest.json'
    manifest.write_text(json.dumps(dict(reversed(list(m.items()))),indent=2))
    assert validate_comparison(comparison)==m  # JSON key order/whitespace is not a contract change.
    assert all((comparison/p).read_bytes()==raw for p,raw in before.items() if p.name!='comparison_manifest.json')


@pytest.mark.parametrize('version',['v1','v2','v3'])
@pytest.mark.parametrize('path,value',[
    (('production_ready',),0), (('production_ready',),1),
    (('production_ready',),'false'), (('production_ready',),None),
    (('datasets',0,'rows'),True), (('datasets',0,'rows'),False),
    (('datasets',0,'rows'),3.0), (('datasets',0,'rows'),'3'),
    (('datasets',3,'rows_by_month','2026-01'),True),
    (('datasets',3,'rows_by_month','2026-01'),1.0),
    (('datasets',3,'rows_by_month','2026-01'),'1'),
    (('lineage','rows'),True), (('lineage','rows'),False),
])
def test_comparison_scalar_mutations_rejected_at_all_nesting_levels(bundles,tmp_path,version,path,value):
    _,comparisons=bundles;comparison=copy_bundle(comparisons[version],tmp_path/'comparison')
    mutate(comparison/'comparison_manifest.json',path,value)
    with pytest.raises(ProcessingError,match='comparison_contract_rejected'):validate_comparison(comparison)


@pytest.mark.parametrize('version',['v2','v3'])
@pytest.mark.parametrize('value',[False,True,0.0,'0',None])
def test_nested_warning_counts_require_actual_integers(bundles,tmp_path,version,value):
    _,comparisons=bundles;comparison=copy_bundle(comparisons[version],tmp_path/'comparison')
    path=comparison/'comparison_manifest.json';m=json.loads(path.read_bytes())
    key=next(iter(m['warning_counts']));count=m['warning_counts'][key]
    # The generated count is integral; use its equal-valued float too.
    changed=float(count) if type(value) is float else value
    mutate(path,('warning_counts',key),changed)
    with pytest.raises(ProcessingError,match='comparison_contract_rejected'):validate_comparison(comparison)


@pytest.mark.parametrize('field',['complete','stopped','production_ready','source_bytes_verified','compatibility_gaps_acknowledged'])
@pytest.mark.parametrize('value',[0,1,'true',None])
def test_canonical_flags_require_booleans(bundles,tmp_path,field,value):
    canonical,_=bundles;copy=copy_bundle(canonical,tmp_path/'snapshot')
    mutate(copy/'snapshot_manifest.json',(field,),value)
    with pytest.raises(ProcessingError,match='dataset_snapshot_contract_rejected'):validate_dataset(copy)


@pytest.mark.parametrize('path',[
    ('repeated_work_order_id_occurrences',),('datasets',0,'rows'),
    ('datasets',3,'rows_by_month','2026-01'),('selections',0,'rows'),
    ('selections',0,'unavailable_costs'),('selections',0,'missing_assignments'),
    ('selections',0,'missing_identifiers'),
])
@pytest.mark.parametrize('value',[False,True,1.0,'1'])
def test_canonical_counts_reject_boolean_or_coerced_numeric_values(bundles,tmp_path,path,value):
    canonical,_=bundles;copy=copy_bundle(canonical,tmp_path/'snapshot')
    mutate(copy/'snapshot_manifest.json',path,value)
    with pytest.raises(ProcessingError,match='dataset_snapshot_contract_rejected'):validate_dataset(copy)


def test_nullable_metadata_and_csv_values_are_not_coerced(bundles,tmp_path):
    canonical,_=bundles;copy=copy_bundle(canonical,tmp_path/'snapshot')
    manifest=copy/'snapshot_manifest.json';m=json.loads(manifest.read_bytes())
    for key in ('unavailable_costs','missing_assignments','missing_identifiers'):m['selections'][0][key]=None
    manifest.write_text(json.dumps(m))
    assert validate_dataset(copy)['selections'][0]['unavailable_costs'] is None
    assert all((copy/name).read_bytes()==(canonical/name).read_bytes() for name in NAMES.values())


def test_comparison_rejects_bad_scalar_in_retained_canonical_manifest(bundles,tmp_path):
    _,comparisons=bundles;copy=copy_bundle(comparisons['v3'],tmp_path/'comparison')
    mutate(copy/'audit/canonical/snapshot_manifest.json',('complete',),1)
    with pytest.raises(ProcessingError,match='dataset_snapshot_contract_rejected'):validate_comparison(copy)
