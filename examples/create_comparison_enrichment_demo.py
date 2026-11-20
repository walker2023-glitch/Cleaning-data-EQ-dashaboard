"""Invented ID collisions, building cases and missing costs; NEW local folder only."""
import argparse
import json
from pathlib import Path
import runpy

from equipment_data_manager.comparison_export import generate_comparison, validate_comparison, _rows, _encode
from equipment_data_manager.historical import discover_history
from equipment_data_manager.historical_preview import preview_history
from equipment_data_manager.historical_processing import make_plan, execute_plan
from equipment_data_manager.historical_dataset import preview_dataset, generate_dataset
from equipment_data_manager.monthly import Workspace
from equipment_data_manager.storage.local import LocalFolderStorage


def create_demo(target):
    target=Path(target).absolute()
    target.mkdir(parents=True,exist_ok=False)
    make_raw=runpy.run_path(str(Path(__file__).with_name('create_historical_batch_demo.py')))['create_demo']
    raw=make_raw(target/'invented-inputs')/'sharepoint'
    # Edit only these newly invented inputs BEFORE processing; never canonical data.
    for folder in sorted((raw/'2026').iterdir()):
        path=folder/'CompuClean Repair Report.csv'
        records=_rows(path.read_bytes())
        for row,identifier,location in zip(records,['R 123','E 00045','R123'],
                ['MC 188','Science and Technology Center 201','MC']):
            row['PersonnelId1']='Equipment Id: '+identifier
            row['PersonnelId4']='Location: '+location
        records[1]['Textbox38']=records[1]['Textbox16']=''
        path.write_bytes(_encode(records,list(records[0])))
        path=folder/'CompuClean Service Orders List.csv'
        records=_rows(path.read_bytes())
        for row,identifier,location in zip(records,['R123','Q 123'],['Library 204','Building 2 101']):
            row.update(EquipmentId1=identifier,Name=location)
        path.write_bytes(_encode(records,list(records[0])))
    workspace=Workspace(raw,target/'candidates',target/'reserved-approved')
    provider=LocalFolderStorage(raw)
    inventory=discover_history(provider,'2026-01','2026-06','sharepoint_year_month')
    preview=preview_history(provider,inventory,workspace.candidate_folder)
    plan=make_plan(workspace,inventory.layout,inventory,preview,[(r.month,r.report_type) for r in preview.reports])
    run=execute_plan(workspace,inventory.layout,plan,plan.fingerprint)
    if run.summary['created']!=18:raise RuntimeError('Invented processing did not complete')
    plan=preview_dataset(workspace,'2026-01','2026-06')
    canonical=generate_dataset(workspace,plan,target/'canonical',confirmation=plan.fingerprint,
        local_confirmed=True,compatibility_acknowledged=True)
    outputs=[generate_comparison(workspace,canonical,target/f'comparison-{i}',confirmed=True,export_schema='comparison-preview-v2') for i in (1,2)]
    manifests=[validate_comparison(output) for output in outputs]
    if manifests[0]!=manifests[1]:raise RuntimeError('Comparison was not deterministic')
    (target/'workspace.toml').write_text('\n'.join(key+' = '+json.dumps(str(value)) for key,value in
        [('raw_folder',raw),('candidate_folder',workspace.candidate_folder),('approved_folder',workspace.approved_folder)])+'\n')
    print(json.dumps(manifests[0]['warning_counts'],sort_keys=True))
    return outputs


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    for path in create_demo(parser.parse_args().output):print(path)
