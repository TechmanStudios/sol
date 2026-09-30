#!/usr/bin/env python3
"""
SOL Thinking Engine Resonance Scan
==================================

Long-form overnight scan for four coupled dimensions:
  1) Phonon memory
  2) Thought vibration
  3) Semantic entanglement
  4) Manifold potential

The scanner runs many trials across damping, seeds, and belief-tuning profiles,
then writes:

  data/thinking_engine_resonance/<timestamp>/
    trials.jsonl
    run_log.txt
    summary.json
    morning_report.md

Usage examples:
  python experiment_thinking_engine_resonance.py
  python experiment_thinking_engine_resonance.py --budget-hours 8 --steps 2000
  python experiment_thinking_engine_resonance.py --seeds 3 --steps 300 --dry-run

Engine and graph remain immutable:
  tools/sol-core/sol_engine.py
  tools/sol-core/default_graph.json
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


_SOL_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))

from sol_engine import SOLEngine  # type: ignore


STANDARD_INJECTIONS = [
    ("grail", 40.0),
    ("metatron", 35.0),
    ("pyramid", 30.0),
    ("christ", 25.0),
    ("light codes", 20.0),
]

HEARTBEAT_ANGULAR_FREQ = 1.5
DT = 0.12
C_PRESS = 0.1


BELIEF_PROFILES: dict[str, dict[str, float]] = {
    "coherence_prayer": {
        "grail": 1.05,
        "metatron": 1.10,
        "pyramid": 0.95,
        "christ": 1.25,
        "light codes": 0.85,
    },
    "explorer_flux": {
        "grail": 1.20,
        "metatron": 1.00,
        "pyramid": 1.15,
        "christ": 0.95,
        "light codes": 1.10,
    },
    "skeptic_grounding": {
        "grail": 0.95,
        "metatron": 0.90,
        "pyramid": 1.10,
        "christ": 0.90,
        "light codes": 1.20,
    },
    "unitive_bridge": {
        "grail": 1.10,
        "metatron": 1.05,
        "pyramid": 1.05,
        "christ": 1.10,
        "light codes": 1.05,
    },
}


@dataclass
class TrialConfig:
    seed: int
    damping: float
    profile: str


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _corr_safe(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 3 or b.size < 3:
        return 0.0
    sa = float(np.std(a))
    sb = float(np.std(b))
    if sa < 1e-12 or sb < 1e-12:
        return 0.0
    c = float(np.corrcoef(a, b)[0, 1])
    if math.isnan(c):
        return 0.0
    return c


def _load_graph_info() -> tuple[dict[int, str], dict[int, str]]:
    path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    labels = {n["id"]: n["label"] for n in data["rawNodes"]}
    groups = {n["id"]: n.get("group", "bridge") for n in data["rawNodes"]}
    return labels, groups


def _make_injection_plan(profile_name: str) -> list[tuple[str, float]]:
    multipliers = BELIEF_PROFILES[profile_name]
    plan: list[tuple[str, float]] = []
    for label, base in STANDARD_INJECTIONS:
        plan.append((label, base * multipliers.get(label, 1.0)))
    return plan


def _extract_series(engine: SOLEngine, id_to_idx: dict[int, int], groups_by_id: dict[int, str]) -> dict[str, Any]:
    metrics = engine.compute_metrics()
    nodes = engine.physics.nodes
    total_rho = float(sum(n["rho"] for n in nodes))

    group_mass: dict[str, float] = {"spirit": 0.0, "bridge": 0.0, "tech": 0.0}
    for n in nodes:
        gid = groups_by_id.get(n["id"], "bridge")
        group_mass[gid] = group_mass.get(gid, 0.0) + float(n["rho"])

    inj_ids = [1, 9, 29, 2, 23]
    inj_rho = {}
    for nid in inj_ids:
        idx = id_to_idx.get(nid)
        inj_rho[str(nid)] = float(nodes[idx]["rho"]) if idx is not None else 0.0

    return {
        "entropy": float(metrics.get("entropy", 0.0)),
        "rhoMaxId": int(metrics.get("rhoMaxId", -1)) if metrics.get("rhoMaxId") is not None else -1,
        "maxRho": float(metrics.get("maxRho", 0.0)),
        "totalFlux": float(metrics.get("totalFlux", 0.0)),
        "activeCount": int(metrics.get("activeCount", 0)),
        "totalRho": total_rho,
        "groups": group_mass,
        "inj": inj_rho,
    }


def _metric_phonon_memory(basin_trace: list[int], maxrho_trace: np.ndarray) -> float:
    if not basin_trace:
        return 0.0
    tail_start = max(0, int(0.75 * len(basin_trace)))
    tail = basin_trace[tail_start:]
    if not tail:
        return 0.0
    final_basin = tail[-1]
    tail_lock = sum(1 for b in tail if b == final_basin) / len(tail)

    if maxrho_trace.size < 3:
        lag_corr = 0.0
    else:
        lag_corr = _corr_safe(maxrho_trace[:-1], maxrho_trace[1:])
    lag_corr = _clamp01((lag_corr + 1.0) / 2.0)
    return _clamp01(0.65 * tail_lock + 0.35 * lag_corr)


def _metric_thought_vibration(total_rho_trace: np.ndarray, inj_matrix: np.ndarray, dt: float) -> float:
    if total_rho_trace.size < 8:
        return 0.0

    centered = total_rho_trace - float(np.mean(total_rho_trace))
    fft_vals = np.fft.rfft(centered)
    power = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(len(centered), d=dt)

    target_freq = HEARTBEAT_ANGULAR_FREQ / (2.0 * math.pi)
    band = np.abs(freqs - target_freq) < 0.03
    band_power = float(np.sum(power[band])) if np.any(band) else 0.0
    total_power = float(np.sum(power[1:])) if power.size > 1 else 0.0
    heartbeat_ratio = band_power / max(total_power, 1e-12)
    heartbeat_score = _clamp01(heartbeat_ratio * 6.0)

    correlations: list[float] = []
    if inj_matrix.shape[1] >= 2:
        for i in range(inj_matrix.shape[1]):
            for j in range(i + 1, inj_matrix.shape[1]):
                c = abs(_corr_safe(inj_matrix[:, i], inj_matrix[:, j]))
                correlations.append(c)
    coherence = float(np.mean(correlations)) if correlations else 0.0

    return _clamp01(0.55 * heartbeat_score + 0.45 * coherence)


def _metric_semantic_entanglement(group_matrix: np.ndarray) -> float:
    if group_matrix.shape[0] < 6 or group_matrix.shape[1] < 3:
        return 0.0

    derivatives = np.diff(group_matrix, axis=0)
    pairs: list[float] = []
    for i in range(derivatives.shape[1]):
        for j in range(i + 1, derivatives.shape[1]):
            direct = abs(_corr_safe(derivatives[:, i], derivatives[:, j]))
            lag1 = abs(_corr_safe(derivatives[:-1, i], derivatives[1:, j]))
            pairs.append(max(direct, lag1))

    if not pairs:
        return 0.0
    mean_pair = float(np.mean(pairs))
    spread = float(np.std(derivatives))
    spread_score = _clamp01(spread / 0.02)
    return _clamp01(0.75 * mean_pair + 0.25 * spread_score)


def _metric_manifold_potential(basin_trace: list[int], entropy_trace: np.ndarray, total_nodes: int) -> float:
    if not basin_trace:
        return 0.0
    unique_ratio = len(set(basin_trace)) / max(1, total_nodes)

    if entropy_trace.size > 0:
        entropy_mean = float(np.mean(entropy_trace))
        entropy_std = float(np.std(entropy_trace))
    else:
        entropy_mean = 0.0
        entropy_std = 0.0

    transitions = 0
    for i in range(1, len(basin_trace)):
        if basin_trace[i] != basin_trace[i - 1]:
            transitions += 1
    transition_rate = transitions / max(1, len(basin_trace) - 1)

    entropy_score = _clamp01(entropy_mean)
    std_score = _clamp01(entropy_std / 0.12)

    return _clamp01(0.45 * unique_ratio + 0.35 * entropy_score + 0.10 * std_score + 0.10 * transition_rate)


def _resonance_index(phonon_memory: float, thought_vibration: float, semantic_entanglement: float, manifold_potential: float) -> float:
    vals = [max(1e-6, phonon_memory), max(1e-6, thought_vibration), max(1e-6, semantic_entanglement), max(1e-6, manifold_potential)]
    gm = float(np.prod(vals) ** (1.0 / 4.0))
    return _clamp01(gm)


def run_trial(config: TrialConfig, steps: int, sample_every: int, labels_by_id: dict[int, str], groups_by_id: dict[int, str]) -> dict[str, Any]:
    engine = SOLEngine.from_default_graph(
        dt=DT,
        c_press=C_PRESS,
        damping=config.damping,
        rng_seed=config.seed,
    )
    for label, amount in _make_injection_plan(config.profile):
        engine.inject(label, amount)

    node_ids = [n["id"] for n in engine.physics.nodes]
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    basin_trace: list[int] = []
    entropy_trace: list[float] = []
    maxrho_trace: list[float] = []
    total_rho_trace: list[float] = []
    group_trace: list[list[float]] = []
    inj_trace: list[list[float]] = []

    inj_order = ["1", "9", "29", "2", "23"]

    for step in range(1, steps + 1):
        engine.step()
        if step % sample_every != 0:
            continue
        sample = _extract_series(engine, id_to_idx, groups_by_id)
        basin_trace.append(sample["rhoMaxId"])
        entropy_trace.append(sample["entropy"])
        maxrho_trace.append(sample["maxRho"])
        total_rho_trace.append(sample["totalRho"])
        group_trace.append([
            sample["groups"].get("spirit", 0.0),
            sample["groups"].get("bridge", 0.0),
            sample["groups"].get("tech", 0.0),
        ])
        inj_trace.append([sample["inj"].get(k, 0.0) for k in inj_order])

    entropy_arr = np.array(entropy_trace, dtype=np.float64)
    maxrho_arr = np.array(maxrho_trace, dtype=np.float64)
    total_rho_arr = np.array(total_rho_trace, dtype=np.float64)
    group_arr = np.array(group_trace, dtype=np.float64) if group_trace else np.zeros((0, 3), dtype=np.float64)
    inj_arr = np.array(inj_trace, dtype=np.float64) if inj_trace else np.zeros((0, 5), dtype=np.float64)

    phonon_memory = _metric_phonon_memory(basin_trace, maxrho_arr)
    thought_vibration = _metric_thought_vibration(total_rho_arr, inj_arr, DT * sample_every)
    semantic_entanglement = _metric_semantic_entanglement(group_arr)
    manifold_potential = _metric_manifold_potential(basin_trace, entropy_arr, len(node_ids))
    resonance = _resonance_index(
        phonon_memory,
        thought_vibration,
        semantic_entanglement,
        manifold_potential,
    )

    final = engine.compute_metrics()
    final_basin = int(final.get("rhoMaxId", -1)) if final.get("rhoMaxId") is not None else -1

    return {
        "seed": config.seed,
        "damping": config.damping,
        "profile": config.profile,
        "steps": steps,
        "sample_every": sample_every,
        "samples": len(basin_trace),
        "final_basin_id": final_basin,
        "final_basin_label": labels_by_id.get(final_basin, "unknown"),
        "final_entropy": float(final.get("entropy", 0.0)),
        "final_max_rho": float(final.get("maxRho", 0.0)),
        "phonon_memory": phonon_memory,
        "thought_vibration": thought_vibration,
        "semantic_entanglement": semantic_entanglement,
        "manifold_potential": manifold_potential,
        "resonance_index": resonance,
        "unique_basins": len(set(basin_trace)),
    }


def _build_trial_plan(seeds: int, damping_values: list[float], profiles: list[str]) -> list[TrialConfig]:
    plan: list[TrialConfig] = []
    for profile in profiles:
        for damping in damping_values:
            for seed in range(seeds):
                plan.append(TrialConfig(seed=seed, damping=damping, profile=profile))
    return plan


def _summarize(trials: list[dict[str, Any]], args: argparse.Namespace, started_at: float, completed_at: float) -> dict[str, Any]:
    if not trials:
        return {
            "status": "no_trials",
            "args": vars(args),
            "elapsed_seconds": completed_at - started_at,
        }

    best = max(trials, key=lambda t: t["resonance_index"])

    by_profile: dict[str, list[dict[str, Any]]] = {}
    for t in trials:
        by_profile.setdefault(t["profile"], []).append(t)

    profile_scores: dict[str, float] = {
        profile: float(statistics.mean(x["resonance_index"] for x in vals))
        for profile, vals in by_profile.items()
    }

    metric_means = {
        "phonon_memory": float(statistics.mean(t["phonon_memory"] for t in trials)),
        "thought_vibration": float(statistics.mean(t["thought_vibration"] for t in trials)),
        "semantic_entanglement": float(statistics.mean(t["semantic_entanglement"] for t in trials)),
        "manifold_potential": float(statistics.mean(t["manifold_potential"] for t in trials)),
        "resonance_index": float(statistics.mean(t["resonance_index"] for t in trials)),
    }

    damping_top = sorted(
        ((float(t["damping"]), float(t["resonance_index"])) for t in trials),
        key=lambda x: x[1],
        reverse=True,
    )[:12]

    return {
        "status": "ok",
        "args": vars(args),
        "elapsed_seconds": completed_at - started_at,
        "trial_count": len(trials),
        "metric_means": metric_means,
        "best_trial": best,
        "top_damping_pairs": damping_top,
        "profile_scores": profile_scores,
    }


def _render_report(summary: dict[str, Any], output_dir: Path) -> str:
    if summary.get("status") != "ok":
        text = "# Thinking Engine Resonance — Morning Report\n\nNo completed trials."
        (output_dir / "morning_report.md").write_text(text, encoding="utf-8")
        return text

    best = summary["best_trial"]
    means = summary["metric_means"]
    profile_scores = summary["profile_scores"]
    top_profiles = sorted(profile_scores.items(), key=lambda x: x[1], reverse=True)

    lines = [
        "# Thinking Engine Resonance — Morning Report",
        "",
        "## Run Summary",
        f"- Trials completed: {summary['trial_count']}",
        f"- Elapsed: {summary['elapsed_seconds'] / 3600:.2f} hours",
        f"- Mean resonance index: {means['resonance_index']:.4f}",
        "",
        "## Best Resonance Window",
        f"- Belief profile: `{best['profile']}`",
        f"- Damping: `{best['damping']}`",
        f"- Seed: `{best['seed']}`",
        f"- Final basin: `{best['final_basin_label']} [{best['final_basin_id']}]`",
        f"- Resonance index: `{best['resonance_index']:.4f}`",
        "",
        "## Core Dimension Means",
        f"- Phonon memory: `{means['phonon_memory']:.4f}`",
        f"- Thought vibration: `{means['thought_vibration']:.4f}`",
        f"- Semantic entanglement: `{means['semantic_entanglement']:.4f}`",
        f"- Manifold potential: `{means['manifold_potential']:.4f}`",
        "",
        "## Belief-Tuning Ranking",
    ]

    for profile, score in top_profiles:
        lines.append(f"- `{profile}` → `{score:.4f}`")

    lines.extend([
        "",
        "## Morning Analysis Prompts",
        "- Compare best-profile trials against second-best profile at the same damping band.",
        "- Inspect whether high semantic entanglement aligns with high manifold potential or competes with it.",
        "- Validate if the top basin remains stable across adjacent damping values (±0.5).",
    ])

    text = "\n".join(lines) + "\n"
    (output_dir / "morning_report.md").write_text(text, encoding="utf-8")
    return text


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Long-form SOL resonance scan.")
    parser.add_argument("--seeds", type=int, default=8, help="Number of seeds per profile/damping.")
    parser.add_argument("--steps", type=int, default=1800, help="Simulation steps per trial.")
    parser.add_argument("--sample-every", type=int, default=4, help="Sample interval in steps.")
    parser.add_argument("--damping-min", type=float, default=0.5, help="Minimum damping.")
    parser.add_argument("--damping-max", type=float, default=22.0, help="Maximum damping.")
    parser.add_argument("--damping-step", type=float, default=0.5, help="Damping step.")
    parser.add_argument("--budget-hours", type=float, default=8.0, help="Wall-clock budget in hours.")
    parser.add_argument("--profiles", nargs="*", default=list(BELIEF_PROFILES.keys()), help="Belief profiles to include.")
    parser.add_argument("--output-root", default="data/thinking_engine_resonance", help="Output root dir.")
    parser.add_argument("--dry-run", action="store_true", help="Only print plan; do not execute.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    valid_profiles = [p for p in args.profiles if p in BELIEF_PROFILES]
    if not valid_profiles:
        print("No valid profiles selected. Available:", ", ".join(BELIEF_PROFILES.keys()))
        return 2

    damping_values = [
        round(args.damping_min + i * args.damping_step, 3)
        for i in range(int(((args.damping_max - args.damping_min) / args.damping_step) + 1))
    ]
    damping_values = [d for d in damping_values if d <= args.damping_max + 1e-9]

    trial_plan = _build_trial_plan(args.seeds, damping_values, valid_profiles)
    print(f"Planned trials: {len(trial_plan)}")
    print(f"Profiles: {valid_profiles}")
    print(f"Damping values: {len(damping_values)} ({damping_values[0]}..{damping_values[-1]})")
    print(f"Steps/trial: {args.steps}, sample_every={args.sample_every}")
    if args.dry_run:
        return 0

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = (_SOL_ROOT / args.output_root / ts).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "run_log.txt"
    trials_path = output_dir / "trials.jsonl"

    labels_by_id, groups_by_id = _load_graph_info()

    start = time.time()
    deadline = start + (args.budget_hours * 3600.0)
    completed: list[dict[str, Any]] = []

    with open(log_path, "w", encoding="utf-8") as logf, open(trials_path, "w", encoding="utf-8") as trialf:
        def log(msg: str):
            stamp = datetime.now().strftime("%H:%M:%S")
            line = f"[{stamp}] {msg}"
            print(line, flush=True)
            logf.write(line + "\n")
            logf.flush()

        log("Starting thinking-engine resonance scan")
        log(f"Output: {output_dir}")

        for idx, cfg in enumerate(trial_plan, start=1):
            if time.time() >= deadline:
                log(f"Budget reached at trial {idx - 1}. Stopping cleanly.")
                break

            t0 = time.time()
            trial = run_trial(
                config=cfg,
                steps=args.steps,
                sample_every=args.sample_every,
                labels_by_id=labels_by_id,
                groups_by_id=groups_by_id,
            )
            trial["trial_index"] = idx
            trial["duration_sec"] = time.time() - t0
            trial["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
            completed.append(trial)

            trialf.write(json.dumps(trial, ensure_ascii=False) + "\n")
            trialf.flush()

            if idx % 10 == 0:
                log(
                    f"Completed {idx}/{len(trial_plan)} | "
                    f"latest resonance={trial['resonance_index']:.4f} "
                    f"({trial['profile']} d={trial['damping']} s={trial['seed']})"
                )

        end = time.time()
        summary = _summarize(completed, args, start, end)

        with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
        _render_report(summary, output_dir)

        log("Wrote summary.json and morning_report.md")
        log(f"Trials completed: {len(completed)}")

    print(f"Done. Artifacts: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
