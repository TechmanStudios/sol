# Overnight Thinking Engine Resonance Runbook

## Goal
Run a long-form overnight scan of four coupled dimensions in SOL:
- phonon memory
- thought vibration
- semantic entanglement
- manifold potential

## Launch (VS Code Task)
- Task: `Thinking Engine: Overnight Resonance Scan`
- Script: `experiment_thinking_engine_resonance.py`

## Manual CLI
```powershell
python experiment_thinking_engine_resonance.py --budget-hours 8 --seeds 8 --steps 1800 --sample-every 4 --damping-min 0.5 --damping-max 22 --damping-step 0.5
```

## Output Artifacts
- `data/thinking_engine_resonance/<timestamp>/trials.jsonl`
  - one JSON object per trial
- `data/thinking_engine_resonance/<timestamp>/summary.json`
  - aggregate means, best trial, profile ranking
- `data/thinking_engine_resonance/<timestamp>/morning_report.md`
  - concise narrative report with top resonance window
- `data/thinking_engine_resonance/<timestamp>/run_log.txt`
  - execution timeline

## Morning Review Checklist
1. Open `morning_report.md` and note the top profile + damping.
2. Validate consistency in `summary.json` (means and best trial).
3. Filter `trials.jsonl` for that profile and inspect neighboring damping values.
4. Compare whether semantic entanglement and manifold potential rise together or trade off.

## Morning Helper (Team Snapshot)
- Task: `Thinking Engine: Morning Brief`
- Script: `tools/analysis/resonance_morning_helper.py`
- Writes:
  - `morning_brief.md`
  - `morning_brief.json`
- Default behavior: auto-select latest run in `data/thinking_engine_resonance` and rank top 10 resonance windows.

## Auto-Refresh Mode (Live Overnight)
- Task: `Thinking Engine: Morning Brief (Auto Refresh)`
- Behavior: refreshes briefing artifacts every 10 minutes while trials continue to append.
- Stop: terminate the running task from VS Code when no longer needed.

Manual watch mode example:
```powershell
python tools/analysis/resonance_morning_helper.py --run-root data/thinking_engine_resonance --watch --interval-sec 600
```

Useful option for quick verification:
```powershell
python tools/analysis/resonance_morning_helper.py --run-root data/thinking_engine_resonance --watch --interval-sec 2 --max-cycles 2
```

## Fast Smoke Test
```powershell
python experiment_thinking_engine_resonance.py --seeds 2 --steps 200 --sample-every 5 --budget-hours 0.02
```
