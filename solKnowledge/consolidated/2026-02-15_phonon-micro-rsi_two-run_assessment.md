# Phonon Micro-RSI Two-Run Assessment (2026-02-15)

## Purpose
Assess whether two same-day phonon micro-RSI runs are ready for SOL knowledge promotion and determine CANDIDATE vs PROMOTED status using only run-local summary/report artifacts.

## Sources
- Run 20260215-145110:
  - [data/phonon_micro_rsi/20260215-145110/summary.json](data/phonon_micro_rsi/20260215-145110/summary.json)
  - [data/phonon_micro_rsi/20260215-145110/report.md](data/phonon_micro_rsi/20260215-145110/report.md)
- Run 20260215-181946:
  - [data/phonon_micro_rsi/20260215-181946/summary.json](data/phonon_micro_rsi/20260215-181946/summary.json)
  - [data/phonon_micro_rsi/20260215-181946/report.md](data/phonon_micro_rsi/20260215-181946/report.md)

## Findings
- 20260215-145110 (24 sweeps): best boundary at damping 83.324361; strength 6000; mode drop 120; transition johannine grove -> grail; final state center 83.314248, half-window 0.190350, RSI shift 0.015.
- 20260215-181946 (100 sweeps): best boundary at damping 83.3193; strength 10000; mode drop 100; transition johannine grove -> johannine grove; final state center 83.328457, half-window 0.190145, RSI shift 0.01.
- Shared pattern: boundary location clusters near 83.32 and terminal window converges near 0.190.
- Limitation: only two runs, differing bounds/step/budget, no explicit controls or counterbalanced sessions in provided artifacts.

## Claim Implications
- Candidate claim: a local damping hotspot exists near 83.32 under the tested micro-RSI search regime.
- Candidate claim: adaptive window dynamics may converge toward ~0.19 in this operating neighborhood.
- Non-promoted: stable cross-mode transition behavior is not established (present in one run, absent in the other).
- Non-promoted: boundary strength magnitudes are not yet comparable enough for mechanism-level claims.

## Operator Caution
- Do not over-interpret boundary_strength as validated physics significance without detector/control verification.
- Do not treat one cross-mode transition as robust when another nearby run lacks it.
- Do not infer advisor efficacy from these artifacts alone; no explicit ablation is provided.

## Promotion Recommendation
- Run 20260215-145110: CANDIDATE (not PROMOTED).
- Run 20260215-181946: CANDIDATE (not PROMOTED).
- Overall: include in consolidated knowledge as provisional evidence only; defer promotion until replicated with controls and explicit falsification checks.

## Next Experiments
- Replicate both configs across fresh sessions/seeds with fixed detector definitions and identical search bounds.
- Add control/ablation: advisor off vs on, same sweep budget.
- Run narrow-window repeats around 83.32 with counterbalanced start centers and windows.
- Predefine promotion thresholds for transition consistency and boundary stability before next consolidation.
