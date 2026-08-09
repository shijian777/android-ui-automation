$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython)) {
    python -m venv (Join-Path $projectRoot '.venv')
}

& $venvPython -m pip install -e "$projectRoot[dev]"

Write-Host 'Environment ready. Copy config.example.json to config.json and edit it.'
