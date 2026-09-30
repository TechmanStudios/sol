param(
  [string]$OutputDirectory = "$PSScriptRoot\production\audio"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

$segments = @(
  [ordered]@{
    id = "01-problem"
    title = "THE PROBLEM"
    capture = "01-opening.png"
    side = "right"
    text = "Teams often judge an agent migration from the final answer alone. That hides whether the workflow gained evidence, preserved constraints, or introduced contradictions. SOL Lens turns observable agent activity into an inspectable semantic comparison and asks a more useful question: did the candidate actually improve on the reference agent?"
    speech = "Teams often judge an agent migration from the final answer alone. That hides whether the workflow gained evidence, preserved constraints, or introduced contradictions. S O L Lens turns observable agent activity into an inspectable semantic comparison and asks a more useful question: did the candidate actually improve on the reference agent?"
  },
  [ordered]@{
    id = "02-identity"
    title = "WHAT SOL MEANS"
    capture = "01-opening.png"
    side = "left"
    text = "Here, SOL means Self-Organizing Logos, the research framework behind this project - not the GPT-5.6 Sol model name. The SOL Engine is the mathematical and experimental foundation. SOL Lens is the browser workbench applying a smaller deterministic profile to observable traces. Both repositories are linked here."
    speech = "Here, S O L means Self-Organizing Logos, the research framework behind this project - not the G P T five point six Sol model name. The S O L Engine is the mathematical and experimental foundation. S O L Lens is the browser workbench applying a smaller deterministic profile to observable traces. Both repositories are linked here."
  },
  [ordered]@{
    id = "03-examples"
    title = "START WITH EXAMPLES"
    capture = "02-gallery.png"
    side = "right"
    text = "Judges do not need to author JSON or understand Logons before trying the product. Seven built-in packets cover grounded answers, branching evidence, parallel tools, self-correction, multi-agent handoffs, conflicting sources, and program-scale work. Each is a deterministic teaching fixture that runs through the real validation and scoring path."
    speech = "Judges do not need to author J S O N or understand low-gons before trying the product. Seven built-in packets cover grounded answers, branching evidence, parallel tools, self-correction, multi-agent handoffs, conflicting sources, and program-scale work. Each is a deterministic teaching fixture that runs through the real validation and scoring path."
  },
  [ordered]@{
    id = "04-court"
    title = "READ THE SEMANTIC COURT"
    capture = "04-grounded-graph.png"
    side = "left"
    text = "Each Logon is one observable atomic unit: a request, tool result, check, contradiction, or output. Typed edges show how those units support, constrain, or challenge one another. SOL Lens replays the packet locally, scores evidence, coherence, and unresolved contradiction, then applies explicit gates to return PROMOTE, HOLD, or QUARANTINE."
    speech = "Each low-gon is one observable atomic unit: a request, tool result, check, contradiction, or output. Typed edges show how those units support, constrain, or challenge one another. S O L Lens replays the packet locally, scores evidence, coherence, and unresolved contradiction, then applies explicit gates to return promote, hold, or quarantine."
  },
  [ordered]@{
    id = "05-failure"
    title = "MAKE FAILURE VISIBLE"
    capture = "06-conflict-verdict.png"
    side = "left"
    text = "The conflicting-sources packet compares six evidence branches across one hundred twenty Logons. Contradiction rises from point zero nine in the reference trace to point two four in the candidate, moving the court from PROMOTE to QUARANTINE. A candidate can look productive while its observable evidence structure shows that it is not ready."
    speech = "The conflicting-sources packet compares six evidence branches across one hundred twenty low-gons. Contradiction rises from point zero nine in the reference trace to point two four in the candidate, moving the court from promote to quarantine. A candidate can look productive while its observable evidence structure shows that it is not ready."
  },
  [ordered]@{
    id = "06-proof"
    title = "EXPORT REPLAYABLE PROOF"
    capture = "06-conflict-verdict.png"
    side = "left"
    text = "Every verdict can be exported as a versioned proof packet containing the observable Logons, typed edges, metrics, and recomputed court result. There are no hidden-chain-of-thought claims, and the same packet can be independently validated and replayed."
    speech = "Every verdict can be exported as a versioned proof packet containing the observable low-gons, typed edges, metrics, and recomputed court result. There are no hidden chain-of-thought claims, and the same packet can be independently validated and replayed."
  },
  [ordered]@{
    id = "07-manifold-question"
    title = "MANIFOLD REPLAY"
    capture = "07-manifold-initial.png"
    side = "right"
    text = "The optional Manifold Replay asks a different question: how might semantic activity propagate through this observable graph?"
    speech = "The optional Manifold Replay asks a different question: how might semantic activity propagate through this observable graph?"
  },
  [ordered]@{
    id = "08-manifold-dynamics"
    title = "DETERMINISTIC DYNAMICS"
    capture = "08-manifold-step3.png"
    side = "right"
    text = "Each deterministic step updates dynamic density and pressure, computes mode-shaped conductance and edge flux, and applies damping. The telemetry makes graph dynamics inspectable without inventing missing events or exposing hidden reasoning. It is an experimental visualization layer: replay state stays separate from the packet and never changes the authoritative Trace Court verdict."
    speech = "Each deterministic step updates dynamic density and pressure, computes mode-shaped conductance and edge flux, and applies damping. The telemetry makes graph dynamics inspectable without inventing missing events or exposing hidden reasoning. It is an experimental visualization layer: replay state stays separate from the packet and never changes the authoritative Trace Court verdict."
  },
  [ordered]@{
    id = "09-close"
    title = "VISIBLE. DETERMINISTIC. REVIEWABLE."
    capture = "09-manifold-reset.png"
    side = "left"
    text = "SOL Lens was built during OpenAI Build Week with GPT-5.6 and Codex on top of the pre-existing SOL research program. The linked repositories provide the mathematics, experiments, tests, provenance, and application source. SOL Lens makes agent migration evidence visible, deterministic, and reviewable before a workflow reaches production."
    speech = "S O L Lens was built during Open A I Build Week with G P T five point six and Codex on top of the pre-existing S O L research program. The linked repositories provide the mathematics, experiments, tests, provenance, and application source. S O L Lens makes agent migration evidence visible, deterministic, and reviewable before a workflow reaches production."
  }
)

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice("Microsoft David Desktop")
$synth.Rate = 1
$synth.Volume = 100

foreach ($segment in $segments) {
  $audioPath = Join-Path $OutputDirectory ($segment.id + ".wav")
  $escaped = [System.Security.SecurityElement]::Escape($segment.speech)
  $ssml = "<speak version='1.0' xml:lang='en-US'><voice name='Microsoft David Desktop'><prosody pitch='+3%'>$escaped</prosody></voice></speak>"
  $synth.SetOutputToWaveFile($audioPath)
  $synth.SpeakSsml($ssml)
  $synth.SetOutputToNull()
  $segment.Remove("speech")
  $segment.audio = [System.IO.Path]::GetFileName($audioPath)
}

$synth.Dispose()
$timelinePath = Join-Path (Split-Path $OutputDirectory -Parent) "timeline.json"
$segments | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $timelinePath -Encoding UTF8
Write-Output "Generated $($segments.Count) narration segments with Microsoft David Desktop."
Write-Output $timelinePath
