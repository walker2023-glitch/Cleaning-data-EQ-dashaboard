"""Strict, local-only configuration. Loading never contacts Microsoft."""

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


class ConfigurationError(ValueError):
    """Invalid local configuration; messages must not include supplied values."""


@dataclass(frozen=True, repr=False)
class MicrosoftSettings:
    tenant_id: str = ""
    client_id: str = ""
    authority: str = ""
    scopes: tuple[str, ...] = ()


@dataclass(frozen=True, repr=False)
class SharePointSettings:
    site_id: str = ""
    drive_id: str = ""
    raw_folder_id: str = ""
    cleaned_folder_id: str = ""
    logs_folder_id: str = ""


@dataclass(frozen=True, repr=False)
class AppConfig:
    mode: str = "offline"
    microsoft: MicrosoftSettings = field(default_factory=MicrosoftSettings)
    sharepoint: SharePointSettings = field(default_factory=SharePointSettings)


def load_config(path: Path) -> AppConfig:
    """Require the documented shape and fail closed on unsupported settings.

    Empty identity/location fields are intentional in M0. This validates shape,
    not tenant registration, Graph permissions, or the existence of folders.
    """
    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)
    except (OSError, ValueError):
        raise ConfigurationError("Cannot read a valid TOML configuration.") from None

    shapes = {
        "app": {"mode"},
        "microsoft": {"tenant_id", "client_id", "authority", "scopes"},
        "sharepoint": {
            "site_id", "drive_id", "raw_folder_id", "cleaned_folder_id", "logs_folder_id"
        },
    }
    if set(data) != set(shapes):
        raise ConfigurationError("Expected only app, microsoft and sharepoint tables.")
    for section, keys in shapes.items():
        table = data[section]
        if not isinstance(table, dict) or set(table) != keys:
            raise ConfigurationError("Configuration fields do not match the template.")
        for key, value in table.items():
            if section == "microsoft" and key == "scopes":
                if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                    raise ConfigurationError("Scopes must be a list of strings.")
            elif not isinstance(value, str):
                raise ConfigurationError("Configuration values must be strings.")
    if data["app"]["mode"] != "offline":
        raise ConfigurationError("Only offline mode is supported in M0.")
    microsoft = data["microsoft"].copy()
    microsoft["scopes"] = tuple(microsoft["scopes"])
    return AppConfig(
        microsoft=MicrosoftSettings(**microsoft),
        sharepoint=SharePointSettings(**data["sharepoint"]),
    )
