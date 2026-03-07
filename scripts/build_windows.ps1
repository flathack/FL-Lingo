$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pyinstallerExe = Join-Path $projectRoot ".venv\Scripts\pyinstaller.exe"
$legacyBuildDir = Join-Path $projectRoot "build\FLAtlas-Translator"
$legacyDistDir = Join-Path $projectRoot "dist\FLAtlas-Translator"

if (-not (Test-Path $pythonExe)) {
    throw "Python venv not found at $pythonExe"
}

if (-not (Test-Path $pyinstallerExe)) {
    & $pythonExe -m pip install pyinstaller PySide6
}

if (Test-Path $legacyBuildDir) {
    Remove-Item $legacyBuildDir -Recurse -Force
}

if (Test-Path $legacyDistDir) {
    Remove-Item $legacyDistDir -Recurse -Force
}

Set-Location $projectRoot
& $pyinstallerExe --noconfirm --clean "FL-Lingo.spec"
