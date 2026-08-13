$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Thrilla requires Python 3.9 or newer."
}

$env:PYTHONPATH = "$ProjectRoot;$env:PYTHONPATH"
python -m compileall -q "$ProjectRoot\thrilla"
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }
python -m unittest discover -s "$ProjectRoot\tests" -q
if ($LASTEXITCODE -ne 0) { throw "Thrilla tests failed." }

$InstallDir = Join-Path $env:LOCALAPPDATA "ThrillaZilla\bin"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$Launcher = Join-Path $InstallDir "thrilla.cmd"
$Contents = "@echo off`r`nset `"PYTHONPATH=$ProjectRoot;%PYTHONPATH%`"`r`npython -m thrilla %*`r`n"
Set-Content -Path $Launcher -Value $Contents -Encoding ASCII

Write-Host ""
Write-Host "THRILLA-ZILLA INSTALLED" -ForegroundColor Magenta
Write-Host "Launcher: $Launcher" -ForegroundColor Cyan
Write-Host "Add that folder to PATH, or run the launcher directly."

