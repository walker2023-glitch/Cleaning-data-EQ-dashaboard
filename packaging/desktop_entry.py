"""Windowed executable entry point; deliberately separate from the CLI."""

from equipment_data_manager.ui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
