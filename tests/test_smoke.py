from pathlib import Path

import pytest

from equipment_data_manager import __version__
from equipment_data_manager.__main__ import main
from equipment_data_manager.storage.graph_sharepoint import (
    GraphSharePointRepository,
    IntegrationNotEnabledError,
)
from equipment_data_manager.storage.interface import ReportRepository

ROOT = Path(__file__).resolve().parents[1]


def test_offline_entrypoint(capsys):
    assert main([]) == 0
    assert "processing is not enabled" in capsys.readouterr().out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == __version__


def test_config_cli(capsys):
    assert main(["--check-config", str(ROOT / "config.example.toml")]) == 0
    assert "Microsoft access is disabled" in capsys.readouterr().out


@pytest.mark.parametrize("operation", ["list", "download", "create"])
def test_sharepoint_operations_fail_closed(operation):
    repository: ReportRepository = GraphSharePointRepository()
    with pytest.raises(IntegrationNotEnabledError, match="disabled in M0"):
        if operation == "list":
            repository.list_files("synthetic-folder")
        elif operation == "download":
            repository.download("synthetic-item", expected_etag="synthetic-v1")
        else:
            repository.create_output("synthetic-folder", name="example.csv", content=b"")


def test_smoke_phase_diagnostics_exclude_unselected_application_values(tmp_path):
    from types import SimpleNamespace
    from time import monotonic
    import json
    from equipment_data_manager.ui.smoke import write_progress
    app=SimpleNamespace(job='dataset_create',worker=SimpleNamespace(busy=True),
        settings_worker=SimpleNamespace(busy=False),status='PRIVATE synthetic value',token='NEVER LOG')
    write_progress(tmp_path,dict(phase=46,started=monotonic(),private='DO NOT EXPORT'),app)
    result=json.loads((tmp_path/'smoke-progress.json').read_text())
    assert result['phase']==46 and result['job']=='dataset_create' and result['worker_busy']
    assert set(result)=={'stage','phase','elapsed_seconds','job','worker_busy','settings_busy'}
    assert 'PRIVATE' not in str(result) and 'NEVER' not in str(result)
