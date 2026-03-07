$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pyinstallerExe = Join-Path $projectRoot ".venv\Scripts\pyinstaller.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python venv not found at $pythonExe"
}

if (-not (Test-Path $pyinstallerExe)) {
    & $pythonExe -m pip install pyinstaller PySide6
}

Set-Location $projectRoot
& $pyinstallerExe --noconfirm --clean "FLAtlas-Translator.spec"

