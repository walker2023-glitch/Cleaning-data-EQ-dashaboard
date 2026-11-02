"""Create ONLY synthetic raw trees; no cleaning, SQLite, Graph or snapshots.

January is populated in both layouts. Other months intentionally remain missing.
Run from the cloned repo with --output data/historical-preview (new destination).
"""
import argparse
from importlib.resources import files
from pathlib import Path


def create_demo(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    resources = files('equipment_data_manager').joinpath('resources/samples')
    for kind, sample, name in (
        ('repairs', 'repairs_sample.csv', 'CompuClean Repair Report.csv'),
        ('service_orders', 'service_sample.csv', 'CompuClean Service Orders List.csv'),
        ('tma_work_orders', 'tma_sample.xlsx', 'Work Orders January 2026.xlsx'),
    ):
        raw = resources.joinpath(sample).read_bytes()
        if sample.endswith('.csv'):
            raw = raw.replace(b'2026-09', b'2026-01')
        for folder in (output / 'standard/2026-01' / kind,
                       output / 'sharepoint/2026/2026-01 (January)'):
            folder.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(raw)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    create_demo(parser.parse_args().output)
