from pathlib import Path

import pytest

from equipment_data_manager.__main__ import main
from equipment_data_manager.config import ConfigurationError, load_config

TEMPLATE = Path(__file__).resolve().parents[1] / "config.example.toml"


def test_template_loads_without_credentials():
    config = load_config(TEMPLATE)
    assert config.mode == "offline"
    assert config.microsoft.tenant_id == ""
    assert config.microsoft.client_id == ""
    assert config.microsoft.scopes == ()
    assert config.sharepoint.site_id == ""


@pytest.mark.parametrize(
    "old,new",
    [
        ('mode = "offline"', 'mode = "live"'),
        ('mode = "offline"', 'mode = true'),
        ('scopes = []', 'scopes = "synthetic"'),
        ('scopes = []', 'scopes = [1]'),
        ('client_id = ""', 'client_id = 42'),
        ('client_id = ""', 'client_id = ""\nclient_secret = "SYNTHETIC_SECRET"'),
        ('[app]', '[unexpected]'),
        ('site_id = ""\n', ''),
    ],
)
def test_invalid_or_unsafe_configuration_is_rejected(tmp_path, old, new):
    path = tmp_path / "config.toml"
    path.write_text(TEMPLATE.read_text().replace(old, new), encoding="utf-8")
    with pytest.raises(ConfigurationError) as exc:
        load_config(path)
    assert "SYNTHETIC_SECRET" not in str(exc.value)


@pytest.mark.parametrize("contents", [None, 'bad = "SYNTHETIC_SECRET', ""])
def test_config_cli_fails_without_exposing_values(tmp_path, capsys, contents):
    path = tmp_path / "config.toml"
    if contents is not None:
        path.write_text(contents, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--check-config", str(path)])
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "Configuration error" in output.err
    assert "SYNTHETIC_SECRET" not in output.err
