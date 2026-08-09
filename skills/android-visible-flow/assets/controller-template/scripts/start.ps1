param(
    [string]$Config = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not $Config) {
    $Config = Join-Path $projectRoot 'config.json'
}
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw 'Runtime not found. Run setup.cmd first.'
}
if (-not (Test-Path -LiteralPath $Config)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot 'config.example.json') -Destination $Config
    throw "Created $Config. Edit session, price, and attendees, then run start.cmd again."
}

Push-Location $projectRoot
try {
    & $venvPython -m ticketflow --config $Config
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
