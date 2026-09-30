Param(
  [string]$RepoRoot = (Get-Location).Path,
  [string]$Title,
  [string]$Tags,
  [string]$Note
)

$ErrorActionPreference = 'Stop'

$helper = Join-Path $RepoRoot 'tools\continuity\continuity_end_of_chat.ps1'

if (-not (Test-Path $helper)) {
  throw "Missing helper script at $helper"
}

powershell -ExecutionPolicy Bypass -File $helper -RepoRoot $RepoRoot -Title $Title -Tags $Tags -Note $Note
