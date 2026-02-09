---
name: SOL Phase Layers: Mass Jump Observatory
description: Protocol to characterize the rho/mass jump at the damping boundary as a phase-layer phenomenon (probability, kinetics, and scaling).
model: GPT-5.2
---

# SOL Phase Layers — Mass Jump Observatory (Protocol)

## Identity
- seriesName: phaseLayers_massJump_observatory
- intendedRunIDs: [TBD]
- dashboardVersion: sol_dashboard_v3_7_2.html (current default runner)
- harnessSchema: sol.dashboard.sweep.v1
- baselineModeUsed: baseline restore (current JS harness; recorded in traces as `baselineSource`)

## Question (one sentence)
What *actually* changes at the damping boundary where the semantic mass/ρ and pressure spikes jump—does it represent a deterministic threshold, a probabilistic nucleation event, hysteresis, or multiple stacked phase layers?

## Invariants (must remain fixed)
- dt: 0.12
- pressC / pressSliderVal: 20 / 200
- mode: multiAgentTrain
- scenario: distributed
- inject pattern: injectAmount=1.0, pulseEvery=4, pulseStep=100, targetsPerPulse=3, agentCount=6
- probeIds: 64,82,79
- detectorWindows: [N/A — use existing peak/trace metrics]
- repsPerCell: 20 (increase to 50–200 only if estimating small probabilities)
- sessionCondition: same harness + same baseline handling across all compared conditions

## Knobs (independent variables)
Primary knob:
- damping (fine grid around the boundary)

Secondary knobs (for phase-layer mapping; use one at a time):
- approxInjectRate via pulseEvery or injectAmount
- dt (time discretization sensitivity)
- baseline handling (only if we intentionally change it and treat it as a knob)

## Protocol (step-by-step)
1) **Lock a reference bracket**
   - Use the current best bracket from replication runs (e.g., 1.869131165–1.86913117).

2) **Measure transition probability curve (not just max/min)**
   - Choose 5–9 dampings spanning below/inside/above bracket.
   - Run `N` replicates per damping.
   - Compute pass-rate for a runtime budget (e.g., failStep ≥ 1200) and also distributions of `peakPMax`, `peakMeanP`, and `peakRhoSum` (where available).

3) **Measure phase-layer kinetics using traces**
   - For each replicate, analyze the trace to extract:
     - jump timing proxy (first crossing of midpoint between early/late ρ in trace window)
     - max d(ρ)/d(step) proxy
     - relationship between the jump proxy and peak stress (`peakPMax`).
   - Use `tools/dashboard_automation/analyze_phase_layer_traces.py` to produce the audit tables.

4) **Scale test (do phase layers move?)**
   - Repeat step (2) for one modified load level (e.g., injectAmount=1.1 or pulseEvery=3) while holding everything else fixed.
   - Compare how the bracket and pass-rate curve shift.

5) **(Optional) Hysteresis**
   - If we can disable baseline restore or run a true up-sweep/down-sweep in a single session without resets, perform matched up/down scans and estimate hysteresis width.
   - Otherwise, treat this as a later dashboard/harness capability upgrade.

## Controls (required)
- baseline control:
  - Keep baseline handling identical across all conditions in a run series.
  - If baseline handling changes, treat it explicitly as a knob.
- damping precision control:
  - The dashboard UI damping slider has `step=0.1` and will snap values (e.g., 1.869131155 → 1.9).
  - For sub-0.1 damping studies, use the automation harness path that passes damping directly into `physics.step(...)` (not the slider).
- order counterbalance (AB/BA):
  - Randomize or interleave damping points to avoid time/session drift mimicking a boundary.
- detector window shift check:
  - Repeat with `traceEvery` and `progressEvery` tweaked (if feasible) to ensure we aren’t manufacturing a “jump” by sampling.
- cross-session repeat:
  - Re-run one below and one above point in a fresh session to ensure stability.

## Expected Outputs (exports)
- Batch outputs under `solData/testResults/.../`
- Trace/summary CSVs produced by the dashboard harness per run
- Phase-layer derived outputs:
  - `phase_layer/phase_layer_trace_runs.csv`
  - `phase_layer/phase_layer_trace_agg.csv`
  - `phase_layer/phase_layer_trace_report.md`

## Success Criteria
- We can describe the boundary as one of:
  - deterministic threshold (tight, consistent crossing), or
  - probabilistic transition (pass-rate changes with damping), or
  - hysteretic (up vs down differs), or
  - multi-layered (multiple distinct jumps).
- We can point to *which* metrics jump (ρ mass, pressure spikes, failStep) and how they co-vary.

## Falsifiers
- Pass-rate and peak distributions are identical across “below” and “above” dampings while only the max/min changes (suggests we’re selecting artifacts).
- The jump disappears or moves wildly under small sampling changes (traceEvery/progressEvery), implying measurement artifact.
- The phenomenon only occurs when baseline handling differs.

## Notes / Risks
- detector clipping risk: peaks may be censored by trace sampling; use summary peaks where possible.
- session drift risk: if not interleaved, time can masquerade as damping.
- file size risk: large N with traces can grow fast; prefer focused points for N≫20.
