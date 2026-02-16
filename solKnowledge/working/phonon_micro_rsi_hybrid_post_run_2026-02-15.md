# Phonon Micro-RSI Hybrid Run — Post-Run Cycle (2026-02-15)

## Run Identity
- Run folder: `data/phonon_micro_rsi/20260214-211730`
- Method: deterministic numeric RSI loop + bounded LLM advisor every 10 sweeps
- Status: complete

## Final Outcome
- Runtime: `9744.79 sec` (~2h 42m)
- Sweeps: `100`
- Best boundary:
  - sweep: `2`
  - damping: `83.323376`
  - boundary strength: `6000.0`
  - mode drop: `120`
  - transition: `christos -> grail`
- Final adaptive state:
  - center: `83.340124`
  - half-window: `0.35` (at configured max)
  - RSI shift: `0.02`
  - latest RSI: `100.0`

## LLM Advisor Reliability (from `llm_advice.jsonl`)
- Advisor checkpoints expected: `10` (sweeps 10..100)
- Total entries: `10`
- Successful responses: `9` (90%)
- Failed responses: `1` (timeout at sweep 20)
- Applied adjustments: `7`
- Fallback model-role usage: `3`
- Latency profile:
  - average: `120.47s`
  - min: `15.29s`
  - max: `226.97s`
- Final checkpoint (sweep 100): success via `primary`

## Interpretation
- Hybrid mode stayed numerically stable while tolerating intermittent API instability.
- The dominant transition remained sharp and early (sweep 2), indicating the critical boundary is robust under this controller.
- Late-run saturation (`latest RSI = 100`, half-window at max) suggests the controller spent the tail phase in a high-momentum regime rather than tightening around a narrow attractor.

## Recommendations (Next Phase)
1. **Phase 2 focused refinement around boundary**
   - center seed: `83.323376`
   - half-window seed: `0.10`
   - step: `0.01`
   - sweeps: `40`
2. **Reduce advisor cadence for efficiency**
   - move from every `10` sweeps to every `20` sweeps unless instability is detected.
3. **Tighten endgame convergence rule**
   - if RSI > 85 for 3+ checkpoints, force window contraction (override growth) to avoid max-window drift.

## Artifact Checklist
- `data/phonon_micro_rsi/20260214-211730/summary.json`
- `data/phonon_micro_rsi/20260214-211730/report.md`
- `data/phonon_micro_rsi/20260214-211730/sweeps.jsonl`
- `data/phonon_micro_rsi/20260214-211730/llm_advice.jsonl`
