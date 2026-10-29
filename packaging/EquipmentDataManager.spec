# Build on Windows with: uv run --frozen --all-extras pyinstaller --noconfirm packaging/EquipmentDataManager.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent
# M1's version identity hashes these source bytes at runtime. PyInstaller normally
# keeps only bytecode, so explicitly retain the unmodified vendored .py resources.
data = collect_data_files("customtkinter")
data += collect_data_files("equipment_data_manager", includes=["resources/samples/*.csv", "resources/samples/*.xlsx", "resources/guides/*.md"])
data += collect_data_files("equipment_data_manager.processing._legacy", include_py_files=True)
analysis = Analysis(
    [str(root / "packaging/desktop_entry.py")], pathex=[str(root / "src")],
    binaries=[], datas=data, hiddenimports=["openpyxl"], hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=[], noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, [], exclude_binaries=True, name="EquipmentDataManager",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=True,
)
collection = COLLECT(executable, analysis.binaries, analysis.datas,
                     strip=False, upx=False, name="EquipmentDataManager")
