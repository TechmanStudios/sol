# Phase 2 Focused Resonance Runbook

## Goal
Use Phase 1 findings to run a tighter scan that:
- targets top damping bands
- expands top profiles with controlled perturbations
- reduces redundant seed sweeps

## Entry Point
- Script: `experiment_thinking_engine_resonance_phase2.py`
- VS Code Task: `Thinking Engine: Phase 2 Focused Resonance`

## Default Strategy
- Read latest Phase 1 run in `data/thinking_engine_resonance`
- Select top damping centers (default 4)
- Build focused damping grid around each center (`±0.5`, step `0.25`)
- Select top profiles (default 2)
- Create profile variants:
  - baseline
  - coherence_boost
  - bridge_lift
  - tech_harmonic
- Use `seeds=1` by default (Phase 1 showed no seed variance)

## Output Artifacts
`data/thinking_engine_resonance_phase2/<timestamp>/`
- `phase2_plan.json`
- `trials.jsonl`
- `summary.json`
- `phase2_report.md`
- `run_log.txt`

## Manual CLI
```powershell
python experiment_thinking_engine_resonance_phase2.py --phase1-root data/thinking_engine_resonance --top-damping-count 4 --top-profile-count 2 --focus-window 0.5 --focus-step 0.25 --seeds 1 --steps 2400 --sample-every 4 --budget-hours 6
```

## Fast Smoke Test
```powershell
python experiment_thinking_engine_resonance_phase2.py --phase1-root data/thinking_engine_resonance --top-damping-count 2 --top-profile-count 1 --focus-window 0.25 --focus-step 0.25 --seeds 1 --steps 300 --budget-hours 0.03
```

## Morning Review
1. Open `phase2_report.md` first.
2. Check `phase1_reference` deltas in `summary.json`.
3. If `delta_mean_resonance` is positive, keep narrowing around best damping cells.
4. If `manifold_potential` remains low, add exploratory perturbation variants before Phase 3.
