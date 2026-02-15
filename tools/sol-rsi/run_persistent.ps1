<#
.SYNOPSIS
    Launch SOL RSI in persistent mode with .env auto-loading.

.DESCRIPTION
    One-liner to start an unattended persistent RSI session.
    Loads .env for GITHUB_TOKEN, sets encoding, runs with budget.

.PARAMETER Cycles
    Number of RSI cycles to run (default: 10).

.PARAMETER BudgetHours
    Maximum runtime in hours (default: 8).

.PARAMETER BudgetDollars
    Maximum LLM spend in USD (default: 1.0).

.PARAMETER DryRun
    If set, only evaluate + plan (no execution).

.EXAMPLE
    .\run_persistent.ps1
    .\run_persistent.ps1 -Cycles 20 -BudgetHours 12 -BudgetDollars 2.0
    .\run_persistent.ps1 -DryRun
#>
param(
    [int]$Cycles = 10,
    [double]$BudgetHours = 8.0,
    [double]$BudgetDollars = 1.0,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Resolve paths relative to this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SolRoot = (Resolve-Path "$ScriptDir\..\..").Path
$EnvFile = Join-Path $SolRoot ".env"
$VenvPython = Join-Path $SolRoot ".venv\Scripts\python.exe"
$Engine = Join-Path $SolRoot "tools\sol-rsi\rsi_engine.py"
$LogDir = Join-Path $SolRoot "data\rsi"

# Load .env if it exists
if (Test-Path $EnvFile) {
    Write-Host "[*] Loading .env from $EnvFile"
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line -split "=", 2
            $key = $parts[0].Trim()
            $val = $parts[1].Trim()
            [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
} else {
    Write-Host "[!] No .env found at $EnvFile - token must be set manually"
}

# Verify token
if (-not $env:GITHUB_TOKEN) {
    Write-Host "[ERROR] GITHUB_TOKEN not set. Create .env or set manually."
    exit 1
}
Write-Host "[*] GITHUB_TOKEN loaded (length=$($env:GITHUB_TOKEN.Length))"

# Set encoding
$env:PYTHONIOENCODING = "utf-8"

# Build log filename
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogDir "persistent_${timestamp}.log"

# Build args
$args = @(
    "-u", $Engine,
    "--mode", "persistent",
    "--cycles", $Cycles,
    "--budget-hours", $BudgetHours,
    "--budget-dollars", $BudgetDollars
)
if ($DryRun) { $args += "--dry-run" }

Write-Host ""
Write-Host "========================================"
Write-Host "  SOL RSI - Persistent Mode"
Write-Host "  Cycles:  $Cycles"
Write-Host "  Budget:  ${BudgetHours}h / $BudgetDollars USD"
Write-Host "  Log:     $LogFile"
Write-Host "========================================"
Write-Host ""

# Run
& $VenvPython @args 2>&1 | Tee-Object -FilePath $LogFile
