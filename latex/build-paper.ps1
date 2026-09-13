$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
    foreach ($tool in @('xelatex', 'biber')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            throw "Required command '$tool' was not found in PATH."
        }
    }

    $tex = '\def\printeditionenabled{}\input{main.tex}'
    & xelatex -jobname=main_print -interaction=nonstopmode -halt-on-error $tex
    if ($LASTEXITCODE -ne 0) { throw "XeLaTeX failed (exit code $LASTEXITCODE)." }
    & biber main_print
    if ($LASTEXITCODE -ne 0) { throw "Biber failed (exit code $LASTEXITCODE)." }
    for ($pass = 1; $pass -le 2; $pass++) {
        & xelatex -jobname=main_print -interaction=nonstopmode -halt-on-error $tex
        if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass $pass failed (exit code $LASTEXITCODE)." }
    }
}
finally {
    Pop-Location
}
