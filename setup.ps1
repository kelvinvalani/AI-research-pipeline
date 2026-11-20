<#
.SYNOPSIS
    One-step, zero-Python setup script for AI Research Pipeline (Windows).
.DESCRIPTION
    Works on a fresh machine with NO Python installed:
      1. Installs `uv` if missing (standalone binary, no Python required).
      2. Runs `uv sync --extra all --extra dev` (automatically downloads Python 3.11+
         and installs NumPy, SciPy, Matplotlib, SymPy, Z3, PyPDF, pytest, ruff, mypy).
      3. Runs `uv run rpipe doctor` to verify everything is ready.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== AI Research Pipeline — One-Step Setup ===" -ForegroundColor Cyan
Write-Host ""

function Find-Uv {
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:USERPROFILE\.local\bin\uv.exe",
        "$env:USERPROFILE\.cargo\bin\uv.exe",
        "$env:LOCALAPPDATA\Programs\uv\uv.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$uvBin = Find-Uv
if (-not $uvBin) {
    Write-Host "[..] `uv` not found — installing uv (no Python required)..." -ForegroundColor Yellow
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
    $uvBin = Find-Uv
    if (-not $uvBin) {
        throw "Installed uv, but could not find uv.exe yet. Reopen your terminal and run .\setup.ps1 again."
    }
}
Write-Host "[ok] Using uv: $uvBin" -ForegroundColor Green

Write-Host ""
Write-Host "[..] Installing Python 3.11+ (if needed) and syncing math/physics libraries..." -ForegroundColor Yellow
& $uvBin sync --extra all --extra dev
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "[..] Running environment health check (rpipe doctor)..." -ForegroundColor Yellow
& $uvBin run rpipe doctor
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== Setup Complete! ===" -ForegroundColor Green
Write-Host "You do not need to run terminal commands manually from here."
Write-Host "Just drop any papers into inbox/ and describe your research idea in your AI chat."
