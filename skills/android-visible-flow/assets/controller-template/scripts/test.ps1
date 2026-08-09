$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    & $venvPython -m pytest (Join-Path $projectRoot 'tests') -q
}
else {
    $env:PYTHONPATH = Join-Path $projectRoot 'src'
    python -m unittest discover -s (Join-Path $projectRoot 'tests') -v
}
