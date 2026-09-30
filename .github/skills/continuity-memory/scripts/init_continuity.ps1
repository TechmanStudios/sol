Param(
  [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'

$tool = Join-Path $RepoRoot 'tools\continuity\continuity_cli.py'

if (-not (Test-Path $tool)) {
  throw "Missing continuity tool at $tool"
}

python $tool init
