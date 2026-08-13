$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($env:THRILLA_PYTHON) {
    $PythonBin = $env:THRILLA_PYTHON
} else {
    $PythonBin = "python"
}

& $PythonBin -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Thrilla requires Python 3.9 or newer."
}

if ($env:THRILLA_STATE_ROOT) {
    $StateRoot = $env:THRILLA_STATE_ROOT
} elseif ($env:THRILLA_HOME) {
    $StateRoot = $env:THRILLA_HOME
} else {
    $StateRoot = Join-Path $HOME ".thrilla-zilla"
}

if ($env:THRILLA_INSTALL_DIR) {
    $InstallDir = $env:THRILLA_INSTALL_DIR
} else {
    $InstallDir = Join-Path $env:LOCALAPPDATA "ThrillaZilla\bin"
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$Launcher = Join-Path $InstallDir "thrilla.cmd"

$Commit = (& git -C $ProjectRoot rev-parse --short=12 HEAD 2>$null)
if (-not $Commit) {
    $Commit = "local-source"
}

$Dirty = (& git -C $ProjectRoot status --porcelain 2>$null)
if ($Dirty) {
    $Commit = "$Commit-dirty"
}

$Timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")

if (Test-Path $Launcher) {
    $Backup = "$Launcher.pre-atomic-$Timestamp"
    Copy-Item -Force $Launcher $Backup
    Write-Host "Preserved existing launcher: $Backup"
}

$OldPythonPath = $env:PYTHONPATH
if ($OldPythonPath) {
    $env:PYTHONPATH = "$ProjectRoot;$OldPythonPath"
} else {
    $env:PYTHONPATH = $ProjectRoot
}

try {
    & $PythonBin -m thrilla release install `
        --project-root $ProjectRoot `
        --state-root $StateRoot `
        --commit $Commit `
        --timestamp $Timestamp `
        --launcher $Launcher `
        --launcher-platform windows

    if ($LASTEXITCODE -ne 0) {
        throw "Atomic Thrilla installation failed."
    }
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}

Write-Host ""
Write-Host "THRILLA-ZILLA ATOMIC INSTALL COMPLETE" -ForegroundColor Magenta
Write-Host "State:    $StateRoot" -ForegroundColor Cyan
Write-Host "Launcher: $Launcher" -ForegroundColor Cyan
Write-Host ""
Write-Host "Verify:"
Write-Host "  thrilla --version"
Write-Host "  thrilla release status --json"
Write-Host ""
Write-Host "Rollback:"
Write-Host "  thrilla release rollback"
