$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
    foreach ($tool in @('xelatex', 'biber')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            throw "Required command '$tool' was not found in PATH."
        }
    }

    & xelatex -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX failed (exit code $LASTEXITCODE)." }

    & biber main
    if ($LASTEXITCODE -ne 0) { throw "Biber failed (exit code $LASTEXITCODE)." }

    for ($pass = 1; $pass -le 2; $pass++) {
        & xelatex -interaction=nonstopmode -halt-on-error main.tex
        if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass $pass after Biber failed (exit code $LASTEXITCODE)." }
    }
}
catch {
    Write-Error $_
    exit 1
}
finally {
    Pop-Location
}
