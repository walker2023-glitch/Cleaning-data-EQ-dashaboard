$ErrorActionPreference = "Stop"
if (-not $IsWindows -and $env:OS -ne "Windows_NT") {
    throw "Build the Windows executable on Windows. Cross-compilation is not supported."
}
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    uv sync --frozen --all-extras
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
    uv run --frozen --all-extras pyinstaller --noconfirm packaging/EquipmentDataManager.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
    Copy-Item docs/user_guide.md dist/EquipmentDataManager/START_HERE.md
    Compress-Archive -Path dist/EquipmentDataManager -DestinationPath dist/EquipmentDataManager_v0.2.0_win64.zip -Force
    Get-FileHash dist/EquipmentDataManager_v0.2.0_win64.zip -Algorithm SHA256 |
        Format-List | Out-File dist/EquipmentDataManager_v0.2.0_win64.sha256.txt
} finally {
    Pop-Location
}
