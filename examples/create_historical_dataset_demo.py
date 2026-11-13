"""Create invented January–June inputs, selected candidates and two identical datasets.

NEW disposable local directory only. No Graph, PBIX, approval or publication.
"""
import argparse
import json
from pathlib import Path
import runpy

from equipment_data_manager.monthly import Workspace
from equipment_data_manager.historical import discover_history
from equipment_data_manager.historical_preview import preview_history
from equipment_data_manager.historical_processing import make_plan,execute_plan
from equipment_data_manager.historical_dataset import preview_dataset,generate_dataset,validate_dataset
from equipment_data_manager.storage.local import LocalFolderStorage


def create_demo(target):
    target=Path(target).absolute()
    target.mkdir(parents=True,exist_ok=False)
    raw=runpy.run_path(str(Path(__file__).with_name('create_historical_batch_demo.py')))['create_demo'](target/'invented-inputs')/'sharepoint'
    workspace=Workspace(raw,target/'candidates',target/'reserved-approved')
    provider=LocalFolderStorage(raw);inventory=discover_history(provider,'2026-01','2026-06','sharepoint_year_month')
    batch=preview_history(provider,inventory,workspace.candidate_folder)
    plan=make_plan(workspace,inventory.layout,inventory,batch,[(r.month,r.report_type) for r in batch.reports])
    result=execute_plan(workspace,inventory.layout,plan,plan.fingerprint)
    if result.summary['created']!=18:raise RuntimeError('Synthetic setup did not complete')
    snapshot_plan=preview_dataset(workspace,'2026-01','2026-06')
    if not snapshot_plan.ready:raise RuntimeError('Synthetic selection incomplete')
    outputs=[generate_dataset(workspace,snapshot_plan,target/f'test-snapshot-{i}',confirmation=snapshot_plan.fingerprint,
        local_confirmed=True,compatibility_acknowledged=True) for i in (1,2)]
    manifests=[validate_dataset(p) for p in outputs]
    if [r['sha256'] for r in manifests[0]['datasets']]!=[r['sha256'] for r in manifests[1]['datasets']]:
        raise RuntimeError('Synthetic datasets were not deterministic')
    (target/'workspace.toml').write_text('\n'.join(k+' = '+json.dumps(str(v)) for k,v in
        [('raw_folder',workspace.raw_folder),('candidate_folder',workspace.candidate_folder),('approved_folder',workspace.approved_folder)])+'\n')
    return outputs


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    for path in create_demo(args.output):print(path)
