# Daytime Phonon RSI Runtime Cheat Sheet

## Purpose
Fast scheduling guide for daytime SOL phonon micro-RSI chains.

## Data Basis (observed)
From completed runs in `data/phonon_micro_rsi`:

- `20260215-145110`: 24 sweeps, 240 steps, runtime 436.57s (7.28 min)
- `20260215-181946`: 100 sweeps, 240 steps, runtime 3223.69s (53.73 min)
- `20260214-211730`: 100 sweeps, 300 steps, runtime 9744.79s (162.41 min, hybrid/advisor-heavy)

## Daytime Rule of Thumb (240-step profile)
Use this for daytime planning when running the lean chain style:

- Planning baseline: 0.54 min per sweep
- Quick optimistic: 0.40 min per sweep
- Safe conservative: 0.65 min per sweep

### Estimated Runtime by Sweep Count
| Sweeps | Optimistic (0.40 min/sweep) | Baseline (0.54 min/sweep) | Conservative (0.65 min/sweep) |
|---:|---:|---:|---:|
| 20 | 8 min | 11 min | 13 min |
| 24 | 10 min | 13 min | 16 min |
| 40 | 16 min | 22 min | 26 min |
| 60 | 24 min | 32 min | 39 min |
| 80 | 32 min | 43 min | 52 min |
| 100 | 40 min | 54 min | 65 min |

## Recommended Daytime Presets

### Quick Check (10–15 min)
- 20–24 sweeps
- 240 steps
- Use for: sanity checks, post-fix validation, rapid boundary drift checks

### Standard Midday Chain (~1 hour)
- 100 sweeps
- 240 steps
- Use for: stable boundary tracking without full hybrid long-form overhead

### Deep Daytime Pass (1–1.5 hours)
- 120 sweeps
- 240 steps
- Use for: higher confidence before handing off to overnight/hybrid runs

## Practical Scheduling Notes
- If advisor cadence is increased (more frequent LLM calls), runtime can rise materially.
- 300-step runs can be much slower than 240-step runs (see 20260214-211730).
- Keep a 10–20% buffer around estimates when scheduling tightly.

## Minimal Planning Formula
For daytime lean profile:

- Estimated minutes ≈ sweeps × 0.54
- Conservative minutes ≈ sweeps × 0.65

Examples:
- 50 sweeps ≈ 27 min baseline
- 100 sweeps ≈ 54 min baseline
- 120 sweeps ≈ 65 min baseline
