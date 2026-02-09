Param(
  [string]$Source = 'vscode-task',
  [string]$Tags = 'continuity,auto',
  [int]$RefreshLimit = 200,
  [ValidateSet('auto','always','never')]
  [string]$ClipboardMode = 'auto',
  [int]$ClipboardMaxChars = 20000,
  [switch]$NoRefresh,
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'

$tool = Join-Path $RepoRoot 'tools\continuity\continuity_cli.py'

if (-not (Test-Path $tool)) {
  throw "Missing continuity tool at $tool"
}

function Try-RunGit([string[]]$GitArgs) {
  try {
    $git = Get-Command git -ErrorAction Stop
    $out = & $git @GitArgs 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return ($out | Out-String).Trim()
  } catch {
    return $null
  }
}

function Try-GetClipboardText() {
  try {
    $t = Get-Clipboard -Raw -TextFormatType Text -ErrorAction Stop
    if ($null -eq $t) { return $null }
    $s = ($t | Out-String)
    if (-not $s) { return $null }
    return $s.TrimEnd()
  } catch {
    return $null
  }
}

# Ensure memory files exist.
python $tool init | Out-Null

$tsLocal = (Get-Date -Format 'yyyy-MM-dd HH:mm').ToString().Trim()
$title = "Auto note $tsLocal"

$branch = Try-RunGit @('rev-parse','--abbrev-ref','HEAD')
$status = Try-RunGit @('status','--porcelain')

$changedCount = 0
$changedPreview = ''
if ($status) {
  $lines = $status -split "`r?`n" | Where-Object { $_ -and $_.Trim().Length -gt 0 }
  $changedCount = $lines.Count
  $changedPreview = ($lines | Select-Object -First 15) -join "`n"
}

$noteLines = New-Object System.Collections.Generic.List[string]
$noteLines.Add("Auto-captured end-of-chat note.")
$noteLines.Add("")
$noteLines.Add("Repo: $RepoRoot")
if ($branch) { $noteLines.Add("Git branch: $branch") }
$noteLines.Add("Time (local): $tsLocal")
if ($changedCount -gt 0) {
  $noteLines.Add("")
  $noteLines.Add("Git status (first 15 / $changedCount):")
  $noteLines.Add($changedPreview)
}

$clip = Try-GetClipboardText
$includeClipboard = $false
if ($ClipboardMode -eq 'always') {
  $includeClipboard = ($null -ne $clip -and $clip.Length -gt 0)
} elseif ($ClipboardMode -eq 'auto') {
  if ($null -ne $clip) {
    $lineCount = ($clip -split "`r?`n").Count
    if ($clip.Length -ge 500 -and $lineCount -ge 6) { $includeClipboard = $true }
  }
}

if ($includeClipboard) {
  $noteLines.Add("")
  $noteLines.Add("Chat transcript (from clipboard):")

  $transcriptDir = Join-Path $RepoRoot 'knowledge\continuity\chat_transcripts'
  New-Item -ItemType Directory -Force -Path $transcriptDir | Out-Null
  $transcriptPath = Join-Path $transcriptDir ("chat_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.txt')

  if ($clip.Length -gt $ClipboardMaxChars) {
    Set-Content -Path $transcriptPath -Value $clip -Encoding utf8
    $noteLines.Add("- Saved full transcript: $transcriptPath")
    $noteLines.Add("- Included preview (first $ClipboardMaxChars chars):")
    $noteLines.Add($clip.Substring(0, $ClipboardMaxChars))
  } else {
    $noteLines.Add($clip)
  }
}

$note = ($noteLines -join "`n").Trim()

python $tool add --title $title --tags $Tags --source $Source --note $note

if (-not $NoRefresh) {
  python $tool refresh --limit $RefreshLimit --snapshot | Out-Null
}
