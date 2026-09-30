#!/usr/bin/env python3
"""
SOL Phonon / Faraday Wave Damping Sweep
=========================================

High-resolution damping sweep from 0→20, with multi-agent injection
pattern, tracking:

  1. Basin dominance (which node holds rhoMax)
  2. Temporal oscillation amplitude per node (phonon signature)
  3. Phase coherence across nodes (standing wave detection)
  4. Entropy trajectory (order ↔ disorder transitions)
  5. Active node count (Faraday instability threshold)

Injection Pattern: "Multi-Agent Swarm"
  Simulates 5 AI agents each focused on a different manifold concept,
  injecting simultaneously — like 5 resonant frequencies exciting
  the lattice at once.

Physics Rationale:
  - Phonons = collective oscillation modes of the 140-node lattice
  - Faraday waves = parametric patterns from heartbeat (ω=0.15) driving
  - Damping controls which phonon modes survive → information capacity
  - Critical damping thresholds = Faraday instability boundaries
  - Information carrier = surviving phonon spectrum, not raw rho
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

_SOL_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))

from sol_engine import SOLEngine


# ---------------------------------------------------------------------------
# Multi-Agent Injection Pattern
# ---------------------------------------------------------------------------
# 5 agents, each focused on a different semantic domain:
#   Agent 1: "grail" (id=1, bridge) — quest/seeking
#   Agent 2: "metatron" (id=9, spirit) — angelic structure
#   Agent 3: "pyramid" (id=29, bridge) — geometry/sacred architecture
#   Agent 4: "christ" (id=2, spirit) — christic consciousness
#   Agent 5: "light codes" (id=23, tech) — the sole tech node
#
# Injection amounts vary to simulate different agent "attention weights":
MULTI_AGENT_INJECTIONS = [
    ("grail", 40.0),          # Agent 1: strong focus
    ("metatron", 35.0),       # Agent 2: moderate-strong
    ("pyramid", 30.0),        # Agent 3: moderate
    ("christ", 25.0),         # Agent 4: moderate-light
    ("light codes", 20.0),    # Agent 5: lighter — the tech bridge
]


# ---------------------------------------------------------------------------
# Engine Constants
# ---------------------------------------------------------------------------
DT = 0.12
C_PRESS = 0.1          # hold constant — isolate damping effects
RNG_SEED = 42
STEPS = 1000           # enough for ~28 heartbeat cycles (period ≈ 35 steps)
SAMPLE_INTERVAL = 1    # capture EVERY step for phonon analysis

# Heartbeat period: cos(1.5 * t) → period = 2π/1.5 ≈ 4.189 time units
# At dt=0.12: ~35 steps per heartbeat cycle
HEARTBEAT_PERIOD_STEPS = round(2 * math.pi / (0.15 * 10 * DT))

# Damping sweep range — configurable
# Sweep 1 (default):  0 → 20 at 0.1 resolution  → basin_phonon_sweep.json
# Sweep 2 (extended): 20 → 84 at 0.25 resolution → basin_phonon_sweep_ext.json
DAMP_MIN = 0.0
DAMP_MAX = 20.0
DAMP_STEP = 0.1
DAMP_VALUES = [round(DAMP_MIN + i * DAMP_STEP, 2)
               for i in range(int((DAMP_MAX - DAMP_MIN) / DAMP_STEP) + 1)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_graph_info():
    """Return (labels, groups) dicts from default graph."""
    graph_path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(graph_path) as f:
        data = json.load(f)
    labels = {n["id"]: n["label"] for n in data["rawNodes"]}
    groups = {n["id"]: n.get("group", "bridge") for n in data["rawNodes"]}
    return labels, groups


def run_phonon_trial(damping: float) -> dict:
    """
    Run one trial at a specific damping value, capturing per-step
    node states for phonon analysis.

    Returns:
        {
            "damping": float,
            "rho_traces": ndarray (steps × nodes),  # temporal rho for each node
            "entropy_trace": list,                   # per-step entropy
            "flux_trace": list,                      # per-step total flux
            "active_trace": list,                    # per-step active count
            "basin_trace": list,                     # per-step rhoMaxId
            "maxrho_trace": list,                    # per-step maxRho
            "final_metrics": dict,
        }
    """
    engine = SOLEngine.from_default_graph(
        dt=DT, c_press=C_PRESS, damping=damping, rng_seed=RNG_SEED
    )

    # Multi-agent injection
    for label, amount in MULTI_AGENT_INJECTIONS:
        engine.inject(label, amount)

    n_nodes = len(engine.physics.nodes)
    node_ids = [n["id"] for n in engine.physics.nodes]

    # Pre-allocate traces
    rho_traces = np.zeros((STEPS, n_nodes), dtype=np.float64)
    entropy_trace = []
    flux_trace = []
    active_trace = []
    basin_trace = []
    maxrho_trace = []

    for s in range(STEPS):
        step_result = engine.step()  # returns {"totalFlux": ..., "activeCount": ...}
        metrics = engine.compute_metrics()

        # Capture full node state
        for j, node in enumerate(engine.physics.nodes):
            rho_traces[s, j] = node["rho"]

        entropy_trace.append(metrics["entropy"])
        flux_trace.append(metrics["totalFlux"])
        active_trace.append(metrics["activeCount"])
        basin_trace.append(metrics["rhoMaxId"])
        maxrho_trace.append(metrics["maxRho"])

    return {
        "damping": damping,
        "rho_traces": rho_traces,
        "entropy_trace": entropy_trace,
        "flux_trace": flux_trace,
        "active_trace": active_trace,
        "basin_trace": basin_trace,
        "maxrho_trace": maxrho_trace,
        "final_metrics": engine.compute_metrics(),
        "node_ids": node_ids,
    }


# ---------------------------------------------------------------------------
# Phonon Analysis Functions
# ---------------------------------------------------------------------------

def compute_oscillation_amplitude(rho_traces: np.ndarray) -> np.ndarray:
    """
    For each node, compute the RMS oscillation amplitude over time.
    This captures the strength of the phonon mode at each node.

    High amplitude = node participates in collective oscillation = phonon carrier
    Low amplitude = node is damped out / silent
    """
    # Detrend: subtract rolling mean to isolate oscillations
    window = HEARTBEAT_PERIOD_STEPS
    if window < 2:
        window = 2
    n_steps, n_nodes = rho_traces.shape
    amplitudes = np.zeros(n_nodes)

    for j in range(n_nodes):
        trace = rho_traces[:, j]
        if np.max(trace) < 1e-12:
            continue
        # Compute oscillation as deviation from local mean
        # Use chunks of 1 heartbeat period
        osc_power = 0.0
        n_chunks = 0
        for start in range(0, n_steps - window, window):
            chunk = trace[start:start + window]
            mean_val = np.mean(chunk)
            if mean_val > 1e-12:
                osc_power += np.std(chunk) / mean_val  # coefficient of variation
                n_chunks += 1
        if n_chunks > 0:
            amplitudes[j] = osc_power / n_chunks

    return amplitudes


def compute_phase_coherence(rho_traces: np.ndarray,
                            node_ids: list,
                            injection_ids: set) -> float:
    """
    Measure phase coherence between injected nodes.
    High coherence = standing wave (Faraday pattern)
    Low coherence = incoherent oscillations

    Uses normalized cross-correlation between injection site traces.
    """
    # Get traces for injection nodes
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    inj_indices = [id_to_idx[nid] for nid in injection_ids if nid in id_to_idx]

    if len(inj_indices) < 2:
        return 0.0

    # Pairwise cross-correlation at zero lag
    correlations = []
    for i in range(len(inj_indices)):
        for j in range(i + 1, len(inj_indices)):
            t1 = rho_traces[:, inj_indices[i]]
            t2 = rho_traces[:, inj_indices[j]]
            s1, s2 = np.std(t1), np.std(t2)
            if s1 > 1e-12 and s2 > 1e-12:
                corr = np.corrcoef(t1, t2)[0, 1]
                if not np.isnan(corr):
                    correlations.append(abs(corr))

    return float(np.mean(correlations)) if correlations else 0.0


def compute_spectral_energy(rho_traces: np.ndarray) -> dict:
    """
    FFT of the global mass signal to find dominant frequencies.
    Peaks at heartbeat frequency / subharmonics = Faraday modes.
    """
    # Global mass signal = sum of all node rho per step
    mass_signal = np.sum(rho_traces, axis=1)

    if np.max(np.abs(mass_signal)) < 1e-15:
        return {"dominant_freq": 0.0, "spectral_entropy": 0.0,
                "heartbeat_power_ratio": 0.0}

    # FFT
    fft_vals = np.fft.rfft(mass_signal)
    power = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(len(mass_signal), d=DT)

    # Skip DC component
    power_no_dc = power[1:]
    freqs_no_dc = freqs[1:]

    if len(power_no_dc) == 0 or np.sum(power_no_dc) < 1e-15:
        return {"dominant_freq": 0.0, "spectral_entropy": 0.0,
                "heartbeat_power_ratio": 0.0}

    # Dominant frequency
    dom_idx = np.argmax(power_no_dc)
    dominant_freq = float(freqs_no_dc[dom_idx])

    # Spectral entropy (flatness of spectrum)
    p_norm = power_no_dc / np.sum(power_no_dc)
    p_norm = p_norm[p_norm > 1e-15]
    spectral_entropy = float(-np.sum(p_norm * np.log2(p_norm)) / np.log2(len(p_norm)))

    # Heartbeat frequency and its power
    heartbeat_freq = 0.15 * 10 / (2 * math.pi)  # ω/(2π) = 1.5/(2π) ≈ 0.239 Hz
    # Find power near heartbeat freq and its subharmonic (ω/2)
    heartbeat_band = np.abs(freqs_no_dc - heartbeat_freq) < 0.05
    subharmonic_band = np.abs(freqs_no_dc - heartbeat_freq / 2) < 0.05
    faraday_power = float(np.sum(power_no_dc[heartbeat_band | subharmonic_band]))
    total_power = float(np.sum(power_no_dc))
    heartbeat_power_ratio = faraday_power / total_power if total_power > 0 else 0.0

    return {
        "dominant_freq": dominant_freq,
        "spectral_entropy": spectral_entropy,
        "heartbeat_power_ratio": heartbeat_power_ratio,
    }


def count_active_phonon_modes(rho_traces: np.ndarray,
                               threshold: float = 0.01) -> int:
    """
    Count how many nodes have significant oscillation amplitude.
    = number of surviving phonon modes.
    """
    amplitudes = compute_oscillation_amplitude(rho_traces)
    return int(np.sum(amplitudes > threshold))


# ---------------------------------------------------------------------------
# Main Sweep
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  SOL PHONON / FARADAY WAVE DAMPING SWEEP")
    print(f"  Damping: {DAMP_MIN} → {DAMP_MAX}  |  Resolution: {DAMP_STEP}")
    print(f"  {len(DAMP_VALUES)} trials × {STEPS} steps = "
          f"{len(DAMP_VALUES) * STEPS:,} total engine steps")
    print(f"  Multi-agent injection: {len(MULTI_AGENT_INJECTIONS)} agents")
    print(f"  Heartbeat period: ~{HEARTBEAT_PERIOD_STEPS} steps")
    print("=" * 70)

    labels, groups = load_graph_info()

    # Resolve injection node IDs
    engine_tmp = SOLEngine.from_default_graph()
    injection_ids = set()
    for lbl, _ in MULTI_AGENT_INJECTIONS:
        for n in engine_tmp.physics.nodes:
            if n["label"].lower() == lbl.lower():
                injection_ids.add(n["id"])
                break
    del engine_tmp
    print(f"  Injection nodes: {sorted(injection_ids)}")
    for nid in sorted(injection_ids):
        print(f"    [{nid:3d}] {labels[nid]:<25} ({groups[nid]})")

    t_start = time.time()

    # ---- Sweep Results ----
    sweep_data = []
    phase_transitions = []   # damping values where basin changes
    prev_basin = None

    for i, damp in enumerate(DAMP_VALUES):
        trial = run_phonon_trial(damp)

        # Phonon analysis
        osc_amplitudes = compute_oscillation_amplitude(trial["rho_traces"])
        coherence = compute_phase_coherence(
            trial["rho_traces"], trial["node_ids"], injection_ids)
        spectral = compute_spectral_energy(trial["rho_traces"])
        n_modes = count_active_phonon_modes(trial["rho_traces"])

        # Top oscillating nodes
        top_osc_idx = np.argsort(osc_amplitudes)[-5:][::-1]
        top_osc = [(trial["node_ids"][j], float(osc_amplitudes[j]))
                    for j in top_osc_idx if osc_amplitudes[j] > 0]

        # Basin
        final_basin = trial["final_metrics"]["rhoMaxId"]
        final_maxrho = trial["final_metrics"]["maxRho"]
        final_entropy = trial["final_metrics"]["entropy"]
        final_mass = trial["final_metrics"]["mass"]
        final_active = trial["final_metrics"]["activeCount"]

        # Detect phase transitions
        if prev_basin is not None and final_basin != prev_basin:
            phase_transitions.append({
                "damping": damp,
                "from_basin": prev_basin,
                "from_label": labels.get(prev_basin, "?"),
                "to_basin": final_basin,
                "to_label": labels.get(final_basin, "?") if final_basin else "None",
            })
        prev_basin = final_basin

        record = {
            "damping": damp,
            "final_basin": final_basin,
            "final_basin_label": labels.get(final_basin, "?") if final_basin else "None",
            "final_maxrho": final_maxrho,
            "final_entropy": final_entropy,
            "final_mass": final_mass,
            "final_active": final_active,
            "n_phonon_modes": n_modes,
            "phase_coherence": coherence,
            "dominant_freq": spectral["dominant_freq"],
            "spectral_entropy": spectral["spectral_entropy"],
            "heartbeat_power_ratio": spectral["heartbeat_power_ratio"],
            "top_oscillators": top_osc,
            "mean_osc_amplitude": float(np.mean(osc_amplitudes)),
            "max_osc_amplitude": float(np.max(osc_amplitudes)),
        }
        sweep_data.append(record)

        # Progress
        if (i + 1) % 20 == 0 or i == 0 or i == len(DAMP_VALUES) - 1:
            basin_str = (f"[{final_basin:3d}] {labels.get(final_basin, '?')}"
                         if final_basin else "[None]")
            elapsed = time.time() - t_start
            eta = elapsed / (i + 1) * (len(DAMP_VALUES) - i - 1)
            print(f"  d={damp:5.1f}  basin={basin_str:<30} "
                  f"modes={n_modes:3d}  coh={coherence:.3f}  "
                  f"maxRho={final_maxrho:.4f}  "
                  f"HB_pwr={spectral['heartbeat_power_ratio']:.3f}  "
                  f"[{elapsed:.0f}s, ETA {eta:.0f}s]")

    total_time = time.time() - t_start

    # ================================================================
    # REPORT
    # ================================================================
    print("\n" + "=" * 70)
    print("  PHONON / FARADAY SWEEP RESULTS")
    print("=" * 70)
    print(f"\nTotal runtime: {total_time:.1f}s")
    print(f"Trials: {len(DAMP_VALUES)}  |  Steps/trial: {STEPS}")

    # ---- Phase Transitions ----
    print(f"\n{'─' * 50}")
    print(f"PHASE TRANSITIONS (Faraday instability boundaries)")
    print(f"{'─' * 50}")
    if phase_transitions:
        for pt in phase_transitions:
            print(f"  damping = {pt['damping']:5.1f}: "
                  f"[{pt['from_basin']}] {pt['from_label']} → "
                  f"[{pt['to_basin']}] {pt['to_label']}")
    else:
        print("  No phase transitions detected")

    # ---- Basin Landscape ----
    print(f"\n{'─' * 50}")
    print(f"BASIN LANDSCAPE across damping range")
    print(f"{'─' * 50}")
    basin_ranges = defaultdict(list)
    for r in sweep_data:
        key = r["final_basin"]
        basin_ranges[key].append(r["damping"])
    for bid, damps in sorted(basin_ranges.items(),
                              key=lambda x: min(x[1])):
        lbl = labels.get(bid, "?") if bid else "None"
        print(f"  [{bid if bid else '-':>3}] {lbl:<25} "
              f"damping {min(damps):5.1f} → {max(damps):5.1f} "
              f"({len(damps)} regimes)")

    # ---- Phonon Mode Count vs Damping ----
    print(f"\n{'─' * 50}")
    print(f"PHONON MODE SURVIVAL (active oscillation modes)")
    print(f"{'─' * 50}")
    # Sample at intervals
    for r in sweep_data:
        d = r["damping"]
        if d % 1.0 == 0 or d in (0.1, 0.2, 0.5):
            bar = "█" * min(r["n_phonon_modes"], 70)
            print(f"  d={d:5.1f}  modes={r['n_phonon_modes']:3d}  {bar}")

    # ---- Faraday Power (heartbeat resonance) ----
    print(f"\n{'─' * 50}")
    print(f"FARADAY WAVE POWER (heartbeat resonance ratio)")
    print(f"{'─' * 50}")
    for r in sweep_data:
        d = r["damping"]
        if d % 1.0 == 0 or d in (0.1, 0.2, 0.5):
            pwr = r["heartbeat_power_ratio"]
            bar_len = int(pwr * 50)
            bar = "▓" * bar_len
            print(f"  d={d:5.1f}  HB_power={pwr:.4f}  {bar}")

    # ---- Phase Coherence ----
    print(f"\n{'─' * 50}")
    print(f"PHASE COHERENCE (standing wave signature)")
    print(f"{'─' * 50}")
    for r in sweep_data:
        d = r["damping"]
        if d % 1.0 == 0 or d in (0.1, 0.2, 0.5):
            coh = r["phase_coherence"]
            bar_len = int(coh * 50)
            bar = "░" * bar_len
            print(f"  d={d:5.1f}  coherence={coh:.4f}  {bar}")

    # ---- Critical Thresholds ----
    print(f"\n{'─' * 50}")
    print(f"CRITICAL THRESHOLDS SUMMARY")
    print(f"{'─' * 50}")

    # Find max phonon modes
    max_modes_rec = max(sweep_data, key=lambda x: x["n_phonon_modes"])
    print(f"  Peak phonon modes:     d={max_modes_rec['damping']:5.1f} "
          f"({max_modes_rec['n_phonon_modes']} modes)")

    # Find max coherence
    max_coh_rec = max(sweep_data, key=lambda x: x["phase_coherence"])
    print(f"  Peak coherence:        d={max_coh_rec['damping']:5.1f} "
          f"(coherence={max_coh_rec['phase_coherence']:.4f})")

    # Find max Faraday power
    max_faraday = max(sweep_data, key=lambda x: x["heartbeat_power_ratio"])
    print(f"  Peak Faraday power:    d={max_faraday['damping']:5.1f} "
          f"(HB_ratio={max_faraday['heartbeat_power_ratio']:.4f})")

    # Find max mean oscillation amplitude
    max_osc = max(sweep_data, key=lambda x: x["mean_osc_amplitude"])
    print(f"  Peak mean oscillation: d={max_osc['damping']:5.1f} "
          f"(amp={max_osc['mean_osc_amplitude']:.6f})")

    # Damping value where modes drop below 50% of peak
    peak_modes = max_modes_rec["n_phonon_modes"]
    half_modes = [r for r in sweep_data
                  if r["n_phonon_modes"] <= peak_modes * 0.5]
    if half_modes:
        mode_halflife = half_modes[0]["damping"]
        print(f"  Mode half-life:        d={mode_halflife:5.1f} "
              f"(modes drop below {peak_modes // 2})")

    # Damping where all modes die
    dead_modes = [r for r in sweep_data if r["n_phonon_modes"] == 0]
    if dead_modes:
        mode_death = dead_modes[0]["damping"]
        print(f"  Mode extinction:       d={mode_death:5.1f} "
              f"(all phonon modes silenced)")

    # ---- Top Oscillators Summary ----
    print(f"\n{'─' * 50}")
    print(f"TOP PHONON CARRIERS (most oscillatory nodes)")
    print(f"{'─' * 50}")
    # Aggregate across all damping values
    osc_totals = defaultdict(float)
    osc_counts = defaultdict(int)
    for r in sweep_data:
        for nid, amp in r["top_oscillators"]:
            osc_totals[nid] += amp
            osc_counts[nid] += 1
    if osc_totals:
        sorted_osc = sorted(osc_totals.items(), key=lambda x: -x[1])[:15]
        for nid, total_amp in sorted_osc:
            avg_amp = total_amp / osc_counts[nid]
            print(f"  [{nid:3d}] {labels.get(nid, '?'):<25} "
                  f"group={groups.get(nid, '?'):<7} "
                  f"avg_amp={avg_amp:.4f}  appearances={osc_counts[nid]}")

    # ---- Save Results ----
    out_path = _SOL_ROOT / "data" / "basin_phonon_sweep.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert for JSON serialization
    serializable = []
    for r in sweep_data:
        s = dict(r)
        s["top_oscillators"] = [(int(nid), float(amp))
                                 for nid, amp in r["top_oscillators"]]
        serializable.append(s)

    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runtime_sec": round(total_time, 2),
        "config": {
            "damp_range": [DAMP_MIN, DAMP_MAX],
            "damp_step": DAMP_STEP,
            "n_trials": len(DAMP_VALUES),
            "steps_per_trial": STEPS,
            "c_press": C_PRESS,
            "dt": DT,
            "heartbeat_omega": 0.15,
            "heartbeat_period_steps": HEARTBEAT_PERIOD_STEPS,
            "injection_pattern": [
                {"label": lbl, "amount": amt}
                for lbl, amt in MULTI_AGENT_INJECTIONS
            ],
        },
        "phase_transitions": phase_transitions,
        "sweep_data": serializable,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
