#!/usr/bin/env python3
"""
SOL Spectral Mode Atlas
========================

Full FFT decomposition of all 140 phonon modes at reference damping values.
Maps each mode's exact frequency, amplitude, phase, and coupling to other modes.

Identifies:
  - Which modes are harmonics of the heartbeat fundamental vs independent
  - Modal coupling (which nodes oscillate in phase vs anti-phase)
  - Spectral fingerprint of the lattice at different damping regimes

Runs at d = [0.2, 5.0, 20.0, 55.0, 79.5, 83.0] with 2000 steps for
high FFT resolution.
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
# Constants
# ---------------------------------------------------------------------------
DT = 0.12
C_PRESS = 0.1
MULTI_AGENT_INJECTIONS = [
    ("grail", 40.0),
    ("metatron", 35.0),
    ("pyramid", 30.0),
    ("christ", 25.0),
    ("light codes", 20.0),
]
HEARTBEAT_FREQ = 0.15 * 10 / (2 * math.pi)  # ~0.2387 Hz

ATLAS_DAMPS = [0.2, 5.0, 20.0, 55.0, 79.5, 83.0]
STEPS = 2000
SAMPLE_EVERY = 2  # sample rho every 2 steps for FFT


def load_graph_info():
    path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(path) as f:
        data = json.load(f)
    labels = {n["id"]: n["label"] for n in data["rawNodes"]}
    groups = {n["id"]: n.get("group", "bridge") for n in data["rawNodes"]}
    return labels, groups


def make_engine(damping, seed=42):
    engine = SOLEngine.from_default_graph(
        dt=DT, c_press=C_PRESS, damping=damping, rng_seed=seed
    )
    for label, amount in MULTI_AGENT_INJECTIONS:
        engine.inject(label, amount)
    return engine


def analyze_spectrum(rho_trace, dt_sample):
    """Analyze the FFT spectrum of a single node's rho trace."""
    n = len(rho_trace)
    if n < 4:
        return {"peak_freq": 0, "peak_power": 0, "harmonics": []}

    # Remove DC (mean) and apply Hanning window
    trace = rho_trace - np.mean(rho_trace)
    window = np.hanning(n)
    trace = trace * window

    fft_vals = np.fft.rfft(trace)
    power = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(n, d=dt_sample)

    # Skip DC bin
    power_no_dc = power[1:]
    freqs_no_dc = freqs[1:]

    if len(power_no_dc) == 0 or np.max(power_no_dc) < 1e-30:
        return {"peak_freq": 0, "peak_power": 0, "harmonics": [],
                "total_power": 0, "hb_fraction": 0}

    # Find peak frequency
    peak_idx = np.argmax(power_no_dc)
    peak_freq = freqs_no_dc[peak_idx]
    peak_power = power_no_dc[peak_idx]
    total_power = np.sum(power_no_dc)

    # Find all significant peaks (> 10% of max)
    threshold = peak_power * 0.1
    peak_mask = power_no_dc > threshold
    significant_freqs = freqs_no_dc[peak_mask]
    significant_powers = power_no_dc[peak_mask]

    # Classify each peak as heartbeat harmonic or independent
    harmonics = []
    for f, p in zip(significant_freqs, significant_powers):
        # Check if this frequency is a harmonic of heartbeat (including subharmonics)
        if HEARTBEAT_FREQ > 0:
            ratio = f / HEARTBEAT_FREQ
            nearest_int = round(ratio * 2) / 2  # check half-integer harmonics too
            if nearest_int > 0 and abs(ratio - nearest_int) < 0.1:
                harmonic_type = f"H{nearest_int:.1f}"
            else:
                harmonic_type = "independent"
        else:
            harmonic_type = "independent"
        harmonics.append({
            "freq": float(f),
            "power": float(p),
            "power_fraction": float(p / total_power),
            "type": harmonic_type,
        })

    # Heartbeat power fraction
    hb_band = np.abs(freqs_no_dc - HEARTBEAT_FREQ) < 0.05
    hb_fraction = float(np.sum(power_no_dc[hb_band]) / total_power) if total_power > 0 else 0

    return {
        "peak_freq": float(peak_freq),
        "peak_power": float(peak_power),
        "total_power": float(total_power),
        "hb_fraction": hb_fraction,
        "harmonics": sorted(harmonics, key=lambda x: -x["power"])[:5],
    }


def compute_modal_coupling(rho_arr, node_ids):
    """Compute phase coupling matrix between all node pairs."""
    n_nodes = rho_arr.shape[1]
    n_samples = rho_arr.shape[0]

    # Compute phase via analytic signal (Hilbert transform)
    from scipy.signal import hilbert
    phases = np.zeros((n_samples, n_nodes))
    amplitudes = np.zeros(n_nodes)

    for j in range(n_nodes):
        trace = rho_arr[:, j]
        trace_centered = trace - np.mean(trace)
        if np.std(trace_centered) > 1e-15:
            analytic = hilbert(trace_centered)
            phases[:, j] = np.angle(analytic)
            amplitudes[j] = np.mean(np.abs(analytic))

    # Phase locking value (PLV) for key node pairs
    # Only compute for high-amplitude nodes to keep output manageable
    amp_threshold = np.percentile(amplitudes[amplitudes > 0], 75) if np.any(amplitudes > 0) else 0
    active_indices = np.where(amplitudes > amp_threshold)[0]

    coupling_pairs = []
    for i in range(len(active_indices)):
        for j in range(i + 1, len(active_indices)):
            ai, aj = active_indices[i], active_indices[j]
            phase_diff = phases[:, ai] - phases[:, aj]
            plv = abs(np.mean(np.exp(1j * phase_diff)))
            if plv > 0.5:  # significant coupling
                coupling_pairs.append({
                    "node_a": int(node_ids[ai]),
                    "node_b": int(node_ids[aj]),
                    "plv": float(plv),
                    "amp_a": float(amplitudes[ai]),
                    "amp_b": float(amplitudes[aj]),
                })

    return sorted(coupling_pairs, key=lambda x: -x["plv"])[:20], amplitudes


def main():
    print("=" * 70)
    print("  SOL SPECTRAL MODE ATLAS")
    print("  Full FFT decomposition of 140 phonon modes")
    print("=" * 70)

    labels, groups = load_graph_info()
    t_total = time.time()

    all_results = {}

    for damp in ATLAS_DAMPS:
        print(f"\n{'─' * 70}")
        print(f"  DAMPING = {damp}")
        print(f"{'─' * 70}")

        engine = make_engine(damp)
        nodes = engine.physics.nodes
        n_nodes = len(nodes)
        node_ids = [n["id"] for n in nodes]

        # Collect high-resolution rho traces
        rho_samples = []
        for s in range(1, STEPS + 1):
            engine.step()
            if s % SAMPLE_EVERY == 0:
                rho_samples.append([n["rho"] for n in nodes])

        rho_arr = np.array(rho_samples)
        dt_sample = DT * SAMPLE_EVERY
        n_samples = rho_arr.shape[0]
        freq_resolution = 1.0 / (n_samples * dt_sample)

        print(f"  Samples: {n_samples}, dt_sample: {dt_sample:.3f}s, "
              f"freq_resolution: {freq_resolution:.4f} Hz")
        print(f"  Heartbeat frequency: {HEARTBEAT_FREQ:.4f} Hz")

        # Per-node spectral analysis
        node_spectra = {}
        heartbeat_nodes = []
        independent_nodes = []

        for j in range(n_nodes):
            trace = rho_arr[:, j]
            spec = analyze_spectrum(trace, dt_sample)
            nid = node_ids[j]
            node_spectra[nid] = spec

            if spec["total_power"] > 0:
                if spec["hb_fraction"] > 0.3:
                    heartbeat_nodes.append((nid, spec["hb_fraction"], spec["peak_freq"]))
                elif spec["peak_freq"] > 0:
                    independent_nodes.append((nid, spec["peak_freq"], spec["peak_power"]))

        # Sort by heartbeat fraction
        heartbeat_nodes.sort(key=lambda x: -x[1])
        independent_nodes.sort(key=lambda x: -x[2])

        print(f"\n  Heartbeat-locked nodes (>30% power at HB freq): {len(heartbeat_nodes)}")
        for nid, hb_frac, peak_f in heartbeat_nodes[:10]:
            print(f"    [{nid:3d}] {labels[nid]:<25} group={groups[nid]:<8} "
                  f"HB_frac={hb_frac:.3f}  peak_f={peak_f:.4f}")

        print(f"\n  Independent oscillators: {len(independent_nodes)}")
        for nid, peak_f, peak_p in independent_nodes[:10]:
            ratio = peak_f / HEARTBEAT_FREQ if HEARTBEAT_FREQ > 0 else 0
            print(f"    [{nid:3d}] {labels[nid]:<25} group={groups[nid]:<8} "
                  f"peak_f={peak_f:.4f}  HB_ratio={ratio:.2f}")

        # Global mass spectrum
        mass_signal = np.sum(rho_arr, axis=1)
        mass_spec = analyze_spectrum(mass_signal, dt_sample)
        print(f"\n  Global mass spectrum:")
        print(f"    Peak freq: {mass_spec['peak_freq']:.4f} Hz "
              f"(ratio to HB: {mass_spec['peak_freq']/HEARTBEAT_FREQ:.2f})")
        print(f"    HB fraction: {mass_spec['hb_fraction']:.3f}")
        if mass_spec["harmonics"]:
            print(f"    Top harmonics:")
            for h in mass_spec["harmonics"][:5]:
                print(f"      f={h['freq']:.4f}  power={h['power_fraction']:.3f}  "
                      f"type={h['type']}")

        # Modal coupling analysis
        print(f"\n  Computing modal coupling (PLV)...")
        try:
            coupling, amplitudes = compute_modal_coupling(rho_arr, node_ids)
            print(f"  Strongly coupled pairs (PLV > 0.5): {len(coupling)}")
            for cp in coupling[:10]:
                la = labels[cp["node_a"]]
                lb = labels[cp["node_b"]]
                print(f"    [{cp['node_a']:3d}] {la:<20} ↔ [{cp['node_b']:3d}] {lb:<20} "
                      f"PLV={cp['plv']:.3f}")

            # Amplitude distribution
            active_amps = amplitudes[amplitudes > 0]
            if len(active_amps) > 0:
                print(f"\n  Amplitude distribution (active modes):")
                print(f"    Mean: {np.mean(active_amps):.6e}")
                print(f"    Max:  {np.max(active_amps):.6e}")
                print(f"    Std:  {np.std(active_amps):.6e}")

                # Top amplitude nodes
                top_amp_idx = np.argsort(-amplitudes)[:5]
                print(f"    Top amplitude nodes:")
                for idx in top_amp_idx:
                    nid = node_ids[idx]
                    print(f"      [{nid:3d}] {labels[nid]:<25} amp={amplitudes[idx]:.6e}")

        except ImportError:
            print(f"  (scipy not available — skipping PLV coupling analysis)")
            coupling = []
            amplitudes = np.zeros(n_nodes)

        # Frequency histogram
        all_peak_freqs = [node_spectra[nid]["peak_freq"] for nid in node_ids
                         if node_spectra[nid]["peak_freq"] > 0]
        if all_peak_freqs:
            freq_arr = np.array(all_peak_freqs)
            bins = np.linspace(0, np.max(freq_arr) * 1.1, 20)
            hist, edges = np.histogram(freq_arr, bins=bins)
            print(f"\n  Frequency distribution ({len(all_peak_freqs)} active modes):")
            for k in range(len(hist)):
                if hist[k] > 0:
                    bar = "█" * hist[k]
                    print(f"    {edges[k]:.3f}-{edges[k+1]:.3f} Hz: {hist[k]:3d} {bar}")

        elapsed = time.time() - t_total
        print(f"\n  [{elapsed:.1f}s elapsed]")

        all_results[damp] = {
            "n_heartbeat_locked": len(heartbeat_nodes),
            "n_independent": len(independent_nodes),
            "mass_peak_freq": mass_spec["peak_freq"],
            "mass_hb_fraction": mass_spec["hb_fraction"],
            "mass_harmonics": mass_spec["harmonics"][:5],
            "top_heartbeat_nodes": [
                {"id": nid, "label": labels[nid], "group": groups[nid],
                 "hb_fraction": hb, "peak_freq": pf}
                for nid, hb, pf in heartbeat_nodes[:10]
            ],
            "top_independent_nodes": [
                {"id": nid, "label": labels[nid], "group": groups[nid],
                 "peak_freq": pf}
                for nid, pf, _ in independent_nodes[:10]
            ],
            "coupling_pairs": coupling[:10] if isinstance(coupling, list) else [],
            "freq_distribution": {
                "total_active": len(all_peak_freqs),
                "mean_freq": float(np.mean(all_peak_freqs)) if all_peak_freqs else 0,
                "std_freq": float(np.std(all_peak_freqs)) if all_peak_freqs else 0,
            },
        }

    total_time = time.time() - t_total

    # ===================================================================
    # Cross-damping comparison
    # ===================================================================
    print(f"\n{'=' * 70}")
    print(f"  SPECTRAL ATLAS — CROSS-DAMPING SUMMARY")
    print(f"{'=' * 70}")

    print(f"\n  {'Damping':>8} {'HB_locked':>10} {'Independent':>12} "
          f"{'Mass_HB%':>10} {'Mass_peak':>10} {'Mean_freq':>10}")
    print(f"  {'─' * 65}")
    for damp in ATLAS_DAMPS:
        r = all_results[damp]
        print(f"  {damp:8.1f} {r['n_heartbeat_locked']:10d} {r['n_independent']:12d} "
              f"{r['mass_hb_fraction']:10.3f} {r['mass_peak_freq']:10.4f} "
              f"{r['freq_distribution']['mean_freq']:10.4f}")

    print(f"\n  Total runtime: {total_time:.1f}s")

    # Save
    out_path = _SOL_ROOT / "data" / "spectral_mode_atlas.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runtime_sec": round(total_time, 2),
        "heartbeat_freq": HEARTBEAT_FREQ,
        "steps": STEPS,
        "sample_every": SAMPLE_EVERY,
        "atlas": {
            str(damp): r for damp, r in all_results.items()
        }
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_path}")


if __name__ == "__main__":
    main()
