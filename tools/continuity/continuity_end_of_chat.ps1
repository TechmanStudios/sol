Param(
  [string]$Title,
  [string]$Tags,
  [string]$Note,
  [string]$Source = 'vscode-chat',
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'

$tool = Join-Path $RepoRoot 'tools\continuity\continuity_cli.py'

if (-not (Test-Path $tool)) {
  throw "Missing continuity tool at $tool"
}

if (-not $Title) {
  $Title = Read-Host 'Session note title'
}

if (-not $Tags) {
  $Tags = Read-Host 'Tags (comma-separated, optional)'
}

if (-not $Note) {
  Write-Host ''
  Write-Host 'Enter note text. Finish with a single dot (.) on its own line.'
  Write-Host ''

  $lines = New-Object System.Collections.Generic.List[string]
  while ($true) {
    $line = Read-Host
    if ($line -eq '.') { break }
    $lines.Add($line)
  }

  $Note = ($lines -join "`n").Trim()
}

# Ensure files exist.
python $tool init | Out-Null

# Pipe note via STDIN (CLI reads STDIN when --note is omitted).
$Note | python $tool add --title $Title --tags $Tags --source $Source
