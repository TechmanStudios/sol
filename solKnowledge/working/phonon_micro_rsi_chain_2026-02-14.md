# SOL Phonon Micro-Sweep RSI Chain (2026-02-14)

## Goal
Run 10 micro-sweeps in the critical damping zone with RSI-style recursion so each sweep is influenced by the prior sweep outcome.

## Command
`G:/docs/TechmanStudios/sol/.venv/Scripts/python.exe experiment_phonon_micro_rsi.py --sweeps 10 --steps 300 --center 83.2 --half-window 0.2 --step 0.02 --damping-min 82.8 --damping-max 83.6 --rsi-period 4 --rsi-shift 0.02`

## Run Output
- Run directory: `data/phonon_micro_rsi/20260214-195758`
- Runtime: `288.7s`

## Best Boundary Found
- Sweep: `2`
- Boundary damping: `83.324`
- Boundary strength: `6000.0`
- Mode drop: `120`
- Transition: `christos -> metatron`

## Adaptive Chain Behavior
- Starting center/window: `83.2 / 0.2`
- Final center/window: `83.323118 / 0.2498755783880542`
- Latest boundary RSI: `42.8045`

## Artifacts
- `data/phonon_micro_rsi/20260214-195758/summary.json`
- `data/phonon_micro_rsi/20260214-195758/sweeps.jsonl`
- `data/phonon_micro_rsi/20260214-195758/report.md`

## Notes
This run confirms the extinction boundary remains tightly centered around `d≈83.32` under recursive, RSI-influenced retargeting. The loop converged near that boundary rather than drifting to the interval edges.
