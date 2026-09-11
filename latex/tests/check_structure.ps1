$ErrorActionPreference = 'Stop'
$checker = Join-Path $PSScriptRoot 'check_structure.py'
python $checker
exit $LASTEXITCODE
