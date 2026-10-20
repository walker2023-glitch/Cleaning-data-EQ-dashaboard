"""Offline diagnostics only; no processing or network operations in M0."""

import argparse
from pathlib import Path

from equipment_data_manager import __version__
from equipment_data_manager.config import ConfigurationError, load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Equipment Data Manager M0 (offline)")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--check-config", type=Path, metavar="PATH")
    args = parser.parse_args(argv)
    if args.check_config is not None:
        try:
            load_config(args.check_config)
        except ConfigurationError as exc:
            # Exceptions contain categories only, never config values.
            parser.exit(2, f"Configuration error: {exc}\n")
        print("Configuration valid for M0 offline mode; Microsoft access is disabled.")
    else:
        print("Equipment Data Manager M0: offline scaffold; processing is not enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
