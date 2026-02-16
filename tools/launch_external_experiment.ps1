<#
.SYNOPSIS
    Launch any Sol experiment command in a new external PowerShell window.

.DESCRIPTION
    Opens a separate watchable terminal window (outside VS Code) and runs
    the provided command from the Sol root directory.

.PARAMETER Command
    Command line to execute in the external window.

.PARAMETER SolRoot
    Sol workspace root path. Defaults based on this script location.

.PARAMETER Inline
    If set, run in the current terminal instead of opening a new window.

.EXAMPLE
    .\launch_external_experiment.ps1 -Command "tools/sol-rsi/run_persistent.ps1 -Cycles 6 -BudgetHours 6"

.EXAMPLE
    .\launch_external_experiment.ps1 -Command "G:/docs/TechmanStudios/sol/.venv/Scripts/python.exe tools/sol-rsi/rsi_engine.py --mode cron --cycles 1"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Command,
    [string]$SolRoot = "",
    [switch]$Inline
)

$ErrorActionPreference = "Stop"

if (-not $SolRoot) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $SolRoot = (Resolve-Path "$ScriptDir\..").Path
}

$fullCmd = "Set-Location '$SolRoot'; $Command"

if ($Inline) {
    Invoke-Expression $fullCmd
} else {
    Start-Process powershell -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy',
        'Bypass',
        '-Command',
        $fullCmd
    ) | Out-Null
    Write-Host "[*] External watch window launched."
}
