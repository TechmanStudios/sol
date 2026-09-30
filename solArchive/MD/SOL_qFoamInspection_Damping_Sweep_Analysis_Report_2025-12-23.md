# SOL / qFoamInspection Damping Sweep Analysis Report (2025-12-23)

Date range covered (from chat context): 2025-12-21 → 2025-12-23
Date compiled: 2026-01-15

Scope: This report consolidates the full workstream from the referenced chat around **analyzing the SOL diagnostics damping sweep** (damp1→damp20) exported from the SOL Dashboard diagnostics recorder. It includes: (1) grounding the metrics in the dashboard’s physics implementation, (2) streaming analysis of large per-run CSV exports, (3) emergent-behavior detectors for late-time rebounds/oscillation-like behavior, (4) persistence of per-run outputs plus a cumulative `summary.csv`, and (5) cross-run comparison + interactive visualization artifacts.

---

## 1) Executive summary

The core goal of the chat was to investigate a set of 20 experimental runs where **only damping varied** (1–20) while all other settings were held constant (inject/query word “sirius”, belief/bias=0, pressure=5). The user suspected unexpected instability/flux behavior at higher damping and wanted systematic diagnostics, beginning with damp20.

Key outcomes:

- Confirmed the **exact dashboard definitions** of “Flux” and “Max|j|” and how damping is applied in the simulation.
- Built (and iteratively upgraded) a **streaming analyzer** capable of processing very large combined CSV diagnostics exports (~100MB) without loading them into memory.
- Added several **emergence/tail detectors** (rebounds, sign-change counts, tail volatility, peak counts) aimed at capturing late-time non-monotone behavior.
- Implemented **persistent artifacts**:
  - A per-run `dampX_analysis.txt` file for each run.
  - A cumulative `analysis_outputs/summary.csv` with one row per damp.
- Produced a **cross-run comparison table** (CSV + Markdown) and an **interactive HTML visualization** showing how the main metrics shift across damping.

High-level finding:

- There is a clear regime shift around **damp12→damp11→damp10**: below ~damp10, several “decay” timings hit the run end time (meaning the system **does not decay below ultra-small thresholds** like 1e-16 / 1e-19 within the recorded window), while tail oscillation metrics and rebound ratios rise sharply.

---

## 2) Workspace / dataset context

Primary workspace root used:

- `G:\docs\TechmanStudios\sol\`

Diagnostics dataset location:

- `G:\docs\TechmanStudios\sol\sol_diagnostics\qFoamInspection\`

Structure:

- `qFoamInspection/damp1/` … `qFoamInspection/damp20/`
  - Each folder contains the diagnostics export CSV (often `*_part001.csv`) plus a manifest CSV.

Practical constraint addressed in the chat:

- A single monolithic TXT export exceeded tool sync limits, so analysis pivoted to the **per-run CSV exports**.

---

## 3) Ground truth: dashboard physics + metric definitions

To avoid misinterpreting the exported numbers, we treated the dashboard implementation as authoritative and re-checked definitions in:

- `G:\docs\TechmanStudios\sol\sol_dashboard_test_original.html`

Key equations / implementation facts used in analysis:

- Pressure field:
  - $p_i = c \log(1+\rho_i)$ (with slider/parameter `pressureC = c`)
- Conductance:
  - $w_{ij}$ derived from base weight and a mode-field interaction term (with clipping)
- Flux on an edge:
  - $j_{ij} = w_{ij}(p_i - p_j)$
- Numerical smoothing / inertia on flux:
  - Implemented as a first-order blend toward the newly computed flux each tick.
- Damping implementation detail:
  - Density decays via a scaling factor of the form `rho *= (1 - damping * dt * 0.1)`.
  - This `*0.1` factor matters: the effective damping rate is not “damping” directly.

Dashboard HUD metrics mapped to CSV columns:

- “Flux” (HUD): corresponds to `totalFlux` in diagnostics (sum of |edge flux| per step).
- “Max|j|” (HUD): corresponds to `maxFluxAbs` in diagnostics (maximum |edge flux| per step).

---

## 4) Analysis tooling built/used

### 4.1 Streaming analyzer (large CSV-safe)

Primary script used throughout the run-by-run analysis:

- `G:\docs\TechmanStudios\sol\sol_diagnostics\qFoamInspection\analyze_diagnostics_run.py`

Core design:

- Uses streaming reads (`csv.DictReader`) to process combined diagnostics CSVs without loading entire tables into memory.
- Focuses primarily on the `sample` rows (time-series summary metrics), because that’s where `totalFlux` and `maxFluxAbs` live.

### 4.2 Core metrics extracted per run

For each `dampX` run, the analyzer computed and reported (at minimum):

- Sample count, duration, inferred dt
- `totalFlux` min/median/max
- `maxFluxAbs` min/median/max
- “last time above threshold” ladder for `totalFlux` (e.g., last>1, last>0.1, … last>1e-19)
- Largest single step-up in `totalFlux`
- Late-time “post-10s” peak summary

### 4.3 Emergent / tail detectors added

To better detect non-monotone “emergent” behavior (rebounds, oscillation-like wiggle, late surprises), we added detectors including:

- Sliding-window rebound after 10s
  - Maximum rise from a local minimum within a 2s window and within a 5s window
  - Reports both absolute Δ and ratio (max/min)
- Tail derivative sign-change counts after 10s
  - Count sign changes in $d/dt$ for `totalFlux` and for `maxFluxAbs`
  - A proxy for “wiggliness” / oscillation
- Tail volatility after 10s
  - Coefficient of variation (CV) for `totalFlux` and `maxFluxAbs`
- Tail peak counts after 10s
  - Counts local peaks above a relative prominence threshold

These detectors were intended to be simple, robust, and comparable across runs.

### 4.4 Persistence / reproducibility outputs

To enable later comparisons (rather than only terminal output), we added persistent outputs:

- Per-run textual output:
  - `qFoamInspection/analysis_outputs/dampX_analysis.txt`
- One-row-per-run summary table:
  - `qFoamInspection/analysis_outputs/summary.csv`

---

## 5) Chronological timeline of the chat work

### Phase A — Start at damp20, verify definitions, and pivot to CSV

- Began analysis at damp20 per user request.
- Located outputs in `qFoamInspection` and verified metric definitions against `sol_dashboard_test_original.html`.
- Hit an upload/sync constraint with a very large monolithic TXT export; pivoted to per-run CSV analysis.

### Phase B — Streaming analysis script + iterative detectors

- Built/used a streaming analysis approach suitable for ~100MB CSVs.
- Sequentially analyzed damp20 down through damp13.
- Added late-time / emergence detectors to capture potential rebounds and oscillation-like behavior.

### Phase C — Persistence added + backfilling outputs

- Added `analysis_outputs/` folder.
- Added `--out` to write full per-run analysis text.
- Added `--summary-csv` to append a single structured row per run.
- Backfilled and saved damp14–damp20 so those runs were persisted for later comparisons.

### Phase D — Run the suspected boundary region (damp12, damp11)

- Ran damp12 and damp11 with persistence enabled.
- Observed a large shift in threshold-decay timings and tail wiggle metrics between damp12 and damp11.

### Phase E — Batch-run damp10 down to damp1

- Executed a batch analysis for damp10→damp1.
- Confirmed all per-run outputs and the summary table were fully populated (damp1→damp20).

### Phase F — Cross-run comparison + visualization

- Generated a cross-run comparison table from `summary.csv`.
- Generated an interactive HTML dashboard (Plotly) for scanning trends quickly.

---

## 6) Key quantitative results (cross-run)

A compact cross-run table was generated and saved here:

- `qFoamInspection/analysis_outputs/cross_run_comparison.md`

The main values are reproduced below for convenience.

| damp | totalFlux_max | max|j|_max | last>1 (s) | last>1e-16 (s) | last>1e-19 (s) | tail signchg (flux) | tail signchg (|j|) | rebound2 ratio | rebound5 ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 148.0 | 8.096 | 10.48 | 48.27 | 55.89 | 56 | 0 | 1.112 | 1.102 |
| 19 | 168.9 | 8.150 | 9.097 | 47.29 | 54.92 | 62 | 0 | 1.166 | 1.132 |
| 18 | 172.3 | 8.301 | 9.979 | 47.57 | 55.25 | 48 | 0 | 1.206 | 1.235 |
| 17 | 162.4 | 8.559 | 9.997 | 48.71 | 56.50 | 24 | 0 | 1.317 | 1.035 |
| 16 | 167.1 | 8.706 | 9.118 | 46.85 | 54.29 | 32 | 0 | 1.092 | 1.179 |
| 15 | 173.0 | 8.850 | 8.544 | 46.35 | 53.85 | 51 | 6 | 1.431 | 1.486 |
| 14 | 180.2 | 8.990 | 9.595 | 48.09 | 55.70 | 74 | 30 | 1.815 | 1.634 |
| 13 | 187.7 | 9.128 | 9.738 | 49.90 | 57.46 | 161 | 58 | 1.775 | 2.071 |
| 12 | 210.2 | 9.139 | 9.457 | 53.88 | 61.34 | 215 | 148 | 2.370 | 2.887 |
| 11 | 219.2 | 9.268 | 10.94 | 74.86 | 82.46 | 354 | 252 | 3.104 | 2.366 |
| 10 | 229.4 | 9.552 | 11.69 | 113.6 | 118.3 | 536 | 461 | 2.060 | 2.071 |
| 9 | 219.0 | 9.762 | 12.44 | 116.4 | 116.4 | 688 | 600 | 2.088 | 2.290 |
| 8 | 227.3 | 10.02 | 12.90 | 117.0 | 117.0 | 719 | 743 | 2.232 | 2.541 |
| 7 | 235.2 | 10.27 | 15.81 | 118.2 | 118.2 | 813 | 786 | 2.130 | 2.389 |
| 6 | 242.7 | 10.50 | 18.95 | 116.1 | 116.1 | 893 | 877 | 2.246 | 2.439 |
| 5 | 249.9 | 10.73 | 23.57 | 115.3 | 115.3 | 903 | 891 | 2.142 | 2.619 |
| 4 | 257.0 | 10.95 | 36.24 | 116.9 | 116.9 | 894 | 861 | 3.037 | 2.545 |
| 3 | 264.0 | 11.16 | 82.16 | 115.4 | 115.4 | 890 | 809 | 3.802 | 4.211 |
| 2 | 271.9 | 11.37 | 122.1 | 122.1 | 122.1 | 787 | 480 | 4.968 | 4.968 |
| 1 | 325.9 | 11.65 | 120.6 | 120.6 | 120.6 | 780 | 465 | 7.015 | 7.015 |

### Interpretation of the “last>threshold” columns

- `last>1e-16` / `last>1e-19` near the run duration means **the run never decayed below that threshold**.
- This becomes especially apparent from damp10 downwards, where these values hit ~115–122s (the run end).

---

## 7) Observations and hypotheses discussed

### 7.1 Regime boundary near damp11–10

- damp12 still decays below 1e-19 within the run window (~61s).
- damp11 decays below 1e-19 later (~82s).
- damp10 and below appear to **not reach the ultra-low tail thresholds** within the recorded window (values land at/near the run end).

This supports the user’s intuition that something “qualitatively different” begins around the low-damping region.

### 7.2 Tail oscillation / instability proxies

Across damp20→damp1:

- Tail sign-change counts grow dramatically.
- Rebound ratios increase (notably at very low damping, e.g., damp1 rebound ratio ~7.0).

This is consistent with the interpretation that lower damping allows ongoing activity/oscillation rather than clean settling.

### 7.3 Peak magnitudes vs damping

Peak magnitudes trend upward as damping decreases:

- `totalFlux_max` highest at damp1.
- `max|j|_max` also highest at damp1.

---

## 8) Artifacts produced (files to include in research archive)

### Per-run analyses

- `qFoamInspection/analysis_outputs/damp1_analysis.txt` … `damp20_analysis.txt`

### Cumulative summary

- `qFoamInspection/analysis_outputs/summary.csv`

### Cross-run comparison outputs

- `qFoamInspection/analysis_outputs/cross_run_comparison.md`
- `qFoamInspection/analysis_outputs/cross_run_comparison.csv`

Generated by:

- `qFoamInspection/make_cross_run_table.py`

### Interactive visualization

- `qFoamInspection/analysis_outputs/cross_run_visualization.html`

Generated by:

- `qFoamInspection/make_cross_run_viz_html.py`

---

## 9) How to reproduce (commands)

All commands assume the SOL venv exists at `G:\docs\TechmanStudios\sol\.venv\`.

Analyze a single run and persist outputs:

- `G:/docs/TechmanStudios/sol/.venv/Scripts/python.exe G:/docs/TechmanStudios/sol/sol_diagnostics/qFoamInspection/analyze_diagnostics_run.py G:/docs/TechmanStudios/sol/sol_diagnostics/qFoamInspection/damp12/sol_diagnostics_20251221_214556_part001.csv --out G:/docs/TechmanStudios/sol/sol_diagnostics/qFoamInspection/analysis_outputs/damp12_analysis.txt --summary-csv G:/docs/TechmanStudios/sol/sol_diagnostics/qFoamInspection/analysis_outputs/summary.csv`

Generate the cross-run comparison table:

- `G:/docs/TechmanStudios/sol/.venv/Scripts/python.exe G:/docs/TechmanStudios/sol/sol_diagnostics/qFoamInspection/make_cross_run_table.py`

Generate the interactive visualization HTML:

- `G:/docs/TechmanStudios/sol/.venv/Scripts/python.exe G:/docs/TechmanStudios/sol/sol_diagnostics/qFoamInspection/make_cross_run_viz_html.py`

---

## 10) Notes on operational issues encountered

- Large single-file exports can exceed practical tooling limits; streaming analysis and per-run modularization were necessary.
- In-editor “quick snippet” style analysis was unreliable on multi-100MB files; dedicated scripts + direct Python execution was used for stability.
- When batch-running many damp values, some terminal output interleaving occurred, but the persisted artifacts in `analysis_outputs/` provide the authoritative record.

---

## 11) Suggested next follow-ups

- Add a simple **regime classifier** to the cross-run outputs (e.g., stable/transition/unstable) based on:
  - `last>1e-19`
  - tail sign-change counts
  - rebound ratios
- Plot additional indicators (if desired) from the `sample` table:
  - `activeCount`, `entropy`, `mass`, `maxRho`
- For deeper mechanistic insight, extend the analyzer to optionally ingest `edge_value` rows to diagnose whether late-time activity is driven by:
  - conductance re-growth
  - pressure re-separation
  - or a small subset of edges/nodes (“hot loop”) dominating the tail.
