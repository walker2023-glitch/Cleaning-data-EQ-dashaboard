"""Invented six-month canonical snapshots and repeatable comparison exports.

Use a NEW disposable local --output directory; no private data or Power BI access.
"""
import argparse
from pathlib import Path
import runpy

from equipment_data_manager.comparison_export import generate_comparison, validate_comparison
from equipment_data_manager.monthly import load_workspace


def create_demo(target):
    target = Path(target).absolute()
    canonical_demo = runpy.run_path(str(Path(__file__).with_name('create_historical_dataset_demo.py')))['create_demo']
    snapshots = canonical_demo(target)
    workspace = load_workspace(target / 'workspace.toml')
    outputs = [generate_comparison(workspace, snapshots[0], target / f'comparison-{i}', confirmed=True) for i in (1, 2)]
    manifests = [validate_comparison(path) for path in outputs]
    if manifests[0] != manifests[1]:
        raise RuntimeError('Comparison output was not deterministic')
    for entry in manifests[0]['datasets']:
        print(entry['file'], entry['rows'], 'rows', entry['sha256'])
    return outputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for output in create_demo(args.output):
        print(output)
