# SOL Initiatory Exploration — Phonon Lattice Map (2026-02-14)

## Purpose
First-pass mapping of the SOL phonon lattice across representative damping regimes, using existing `basin_phonon_sweep.py` metrics and multi-agent injection defaults.

## Inputs
- Engine script: `basin_phonon_sweep.py`
- Graph: `tools/sol-core/default_graph.json`
- Injection protocol (default):
  - grail: 40.0
  - metatron: 35.0
  - pyramid: 30.0
  - christ: 25.0
  - light codes: 20.0
- Steps per trial: 1000
- Damping samples: `[0.2, 1.0, 3.5, 5.0, 10.0, 20.0, 40.0, 55.0, 75.0, 79.5, 83.0, 83.5]`

## Outputs
- Data artifact: `data/initiatory_phonon_lattice_map_2026-02-14.json`
- Runtime: `52.98s`

## Core Results
| Damping | Final basin | Modes | Coherence | Heartbeat power |
|---|---|---:|---:|---:|
| 0.2 | maia nartoomid [14] | 140 | 0.965 | 0.035 |
| 1.0 | earth star [5] | 140 | 0.979 | 0.049 |
| 3.5 | mystery school [89] | 140 | 0.992 | 0.103 |
| 5.0 | pyramid [29] | 140 | 0.995 | 0.132 |
| 10.0 | pyramid [29] | 140 | 0.998 | 0.220 |
| 20.0 | pyramid [29] | 140 | 0.999 | 0.342 |
| 40.0 | christic [22] | 140 | 1.000 | 0.409 |
| 55.0 | numis'om [7] | 140 | 1.000 | 0.396 |
| 75.0 | numis'om [7] | 140 | 0.999 | 0.350 |
| 79.5 | christ [2] | 140 | 1.000 | 0.053 |
| 83.0 | christ [2] | 133 | 1.000 | 0.049 |
| 83.5 | metatron [9] | 5 | 0.607 | 0.418 |

## Interpretation (Initiatory)
- A clear basin succession appears as damping increases: bridge-heavy attractors → spirit attractors → terminal metatron lock.
- All 140 phonon modes survive through most of the sampled range, then collapse sharply in the critical boundary region (`83.0 → 83.5`).
- Coherence generally rises with damping until the extinction boundary, where coherence drops with the modal collapse.
- Heartbeat power concentrates strongly in mid/high damping before critical collapse.

## Minimal Replay Recipe
1. Ensure environment uses `G:/docs/TechmanStudios/sol/.venv/Scripts/python.exe`.
2. Run `python basin_phonon_sweep.py` for full sweep artifacts.
3. For this initiatory map profile, sample the 12 damping values listed above and save to `data/initiatory_phonon_lattice_map_2026-02-14.json`.

## Suggested Next Step
Perform a focused boundary micro-sweep at `d=82.8 → 83.6` with step `0.01` to map exact extinction onset and first post-collapse basin lock with higher precision.
