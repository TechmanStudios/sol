#!/usr/bin/env python3
"""
SOL Thinking Engine Resonance — Phase 2 Focused Scan
====================================================

Phase 2 objectives:
  1) Focus compute on top damping bands discovered in Phase 1.
  2) Expand profile search via controlled belief perturbations.
  3) Reduce redundant seed sweeps (default seeds=1) for higher signal efficiency.

Inputs:
  - Phase 1 artifact directory (latest by default):
    data/thinking_engine_resonance/<timestamp>/
      morning_brief.json (preferred) or summary.json (fallback)

Outputs:
  data/thinking_engine_resonance_phase2/<timestamp>/
    phase2_plan.json
    trials.jsonl
    summary.json
    phase2_report.md
    run_log.txt
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import experiment_thinking_engine_resonance as phase1


_SOL_ROOT = Path(__file__).resolve().parent


def _latest_run(root: Path) -> Path:
    runs = [p for p in root.iterdir() if p.is_dir()]
    if not runs:
        raise FileNotFoundError(f"No run directories found under {root}")
    runs.sort(key=lambda p: p.name)
    return runs[-1]


def _load_phase1_context(run_dir: Path) -> dict[str, Any]:
    brief_path = run_dir / "morning_brief.json"
    summary_path = run_dir / "summary.json"
    if brief_path.exists():
        return json.loads(brief_path.read_text(encoding="utf-8"))
    if summary_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Neither morning_brief.json nor summary.json found in {run_dir}")


def _extract_top_profiles(ctx: dict[str, Any], count: int) -> list[str]:
    ranked = ctx.get("profile_ranking")
    if isinstance(ranked, list) and ranked:
        names = [str(x.get("profile")) for x in ranked if isinstance(x, dict) and x.get("profile")]
        return names[:count]

    scores = ctx.get("profile_scores")
    if isinstance(scores, dict) and scores:
        names = [k for k, _ in sorted(scores.items(), key=lambda kv: float(kv[1]), reverse=True)]
        return names[:count]

    return list(phase1.BELIEF_PROFILES.keys())[:count]


def _extract_top_dampings(ctx: dict[str, Any], count: int) -> list[float]:
    ranked = ctx.get("damping_ranking")
    if isinstance(ranked, list) and ranked:
        vals = []
        for row in ranked:
            if isinstance(row, dict) and "damping" in row:
                vals.append(float(row["damping"]))
        if vals:
            return vals[:count]

    pairs = ctx.get("top_damping_pairs")
    if isinstance(pairs, list) and pairs:
        vals = []
        for p in pairs:
            if isinstance(p, list) and p:
                vals.append(float(p[0]))
        if vals:
            out: list[float] = []
            for d in vals:
                if d not in out:
                    out.append(d)
            return out[:count]

    best_trial = ctx.get("best_trial", {})
    if isinstance(best_trial, dict) and "damping" in best_trial:
        return [float(best_trial["damping"])]
    return [5.0]


def _build_focused_damping_grid(
    top_dampings: list[float],
    half_window: float,
    step: float,
    dmin: float,
    dmax: float,
) -> list[float]:
    values: set[float] = set()
    n = int(round((2.0 * half_window) / step))
    for center in top_dampings:
        for i in range(n + 1):
            d = center - half_window + i * step
            if dmin <= d <= dmax:
                values.add(round(d, 3))
    return sorted(values)


def _variant_specs() -> list[tuple[str, dict[str, float]]]:
    return [
        (
            "baseline",
            {
                "grail": 1.00,
                "metatron": 1.00,
                "pyramid": 1.00,
                "christ": 1.00,
                "light codes": 1.00,
            },
        ),
        (
            "coherence_boost",
            {
                "grail": 1.00,
                "metatron": 1.08,
                "pyramid": 1.00,
                "christ": 1.10,
                "light codes": 0.96,
            },
        ),
        (
            "bridge_lift",
            {
                "grail": 1.10,
                "metatron": 1.00,
                "pyramid": 1.10,
                "christ": 1.00,
                "light codes": 1.00,
            },
        ),
        (
            "tech_harmonic",
            {
                "grail": 1.00,
                "metatron": 1.00,
                "pyramid": 1.00,
                "christ": 1.00,
                "light codes": 1.14,
            },
        ),
        (
            "christic_focus",
            {
                "grail": 0.98,
                "metatron": 1.04,
                "pyramid": 0.98,
                "christ": 1.18,
                "light codes": 0.94,
            },
        ),
        (
            "exploration_flux",
            {
                "grail": 1.12,
                "metatron": 0.96,
                "pyramid": 1.12,
                "christ": 0.96,
                "light codes": 1.08,
            },
        ),
    ]


def _compose_profile(base_name: str, variant_name: str, variant_mult: dict[str, float]) -> tuple[str, dict[str, float]]:
    base = phase1.BELIEF_PROFILES[base_name]
    merged = {}
    for label, v in base.items():
        merged[label] = float(v) * float(variant_mult.get(label, 1.0))
    new_name = f"{base_name}__{variant_name}"
    return new_name, merged


def _summarize_phase2(trials: list[dict[str, Any]], phase1_ctx: dict[str, Any], args: argparse.Namespace, started_at: float, ended_at: float) -> dict[str, Any]:
    if not trials:
        return {
            "status": "no_trials",
            "phase1_run_dir": args.phase1_run_dir,
            "elapsed_seconds": ended_at - started_at,
            "args": vars(args),
        }

    best = max(trials, key=lambda t: float(t["resonance_index"]))
    means = {
        "resonance_index": float(statistics.mean(float(t["resonance_index"]) for t in trials)),
        "phonon_memory": float(statistics.mean(float(t["phonon_memory"]) for t in trials)),
        "thought_vibration": float(statistics.mean(float(t["thought_vibration"]) for t in trials)),
        "semantic_entanglement": float(statistics.mean(float(t["semantic_entanglement"]) for t in trials)),
        "manifold_potential": float(statistics.mean(float(t["manifold_potential"]) for t in trials)),
    }

    phase1_mean = float(phase1_ctx.get("metric_means", {}).get("resonance_index", 0.0))

    if isinstance(phase1_ctx.get("best_trial"), dict):
        phase1_best = float(phase1_ctx.get("best_trial", {}).get("resonance_index", 0.0))
    else:
        top_trials = phase1_ctx.get("top_trials", [])
        if isinstance(top_trials, list) and top_trials:
            phase1_best = max(float(t.get("resonance_index", 0.0)) for t in top_trials if isinstance(t, dict))
        else:
            phase1_best = 0.0

    by_profile: dict[str, list[float]] = {}
    for t in trials:
        by_profile.setdefault(str(t["profile"]), []).append(float(t["resonance_index"]))
    profile_rank = [
        {"profile": k, "mean_resonance": float(statistics.mean(v)), "best_resonance": float(max(v)), "n": len(v)}
        for k, v in by_profile.items()
    ]
    profile_rank.sort(key=lambda x: x["mean_resonance"], reverse=True)

    by_damping: dict[float, list[float]] = {}
    for t in trials:
        by_damping.setdefault(float(t["damping"]), []).append(float(t["resonance_index"]))
    damping_rank = [
        {"damping": d, "mean_resonance": float(statistics.mean(v)), "best_resonance": float(max(v)), "n": len(v)}
        for d, v in by_damping.items()
    ]
    damping_rank.sort(key=lambda x: x["mean_resonance"], reverse=True)

    return {
        "status": "ok",
        "phase1_run_dir": args.phase1_run_dir,
        "elapsed_seconds": ended_at - started_at,
        "trial_count": len(trials),
        "metric_means": means,
        "best_trial": best,
        "phase1_reference": {
            "mean_resonance": phase1_mean,
            "best_resonance": phase1_best,
            "delta_mean_resonance": means["resonance_index"] - phase1_mean,
            "delta_best_resonance": float(best["resonance_index"]) - phase1_best,
        },
        "profile_ranking": profile_rank,
        "damping_ranking": damping_rank[:20],
        "args": vars(args),
    }


def _render_phase2_report(summary: dict[str, Any], output_dir: Path):
    if summary.get("status") != "ok":
        (output_dir / "phase2_report.md").write_text("# Phase 2 Resonance Report\n\nNo trials completed.\n", encoding="utf-8")
        return

    best = summary["best_trial"]
    means = summary["metric_means"]
    ref = summary["phase1_reference"]
    pr = summary["profile_ranking"][:8]
    dr = summary["damping_ranking"][:10]

    lines = [
        "# Phase 2 Resonance Report",
        "",
        "## Summary",
        f"- Trials completed: {summary['trial_count']}",
        f"- Elapsed: {summary['elapsed_seconds'] / 3600:.2f} hours",
        f"- Mean resonance: {means['resonance_index']:.4f}",
        f"- Δ mean vs Phase 1: {ref['delta_mean_resonance']:+.4f}",
        "",
        "## Best Window",
        f"- Profile: `{best['profile']}`",
        f"- Damping: `{best['damping']}`",
        f"- Resonance: `{best['resonance_index']:.4f}`",
        f"- Final basin: `{best['final_basin_label']} [{best['final_basin_id']}]`",
        f"- Δ best vs Phase 1: {ref['delta_best_resonance']:+.4f}",
        "",
        "## Dimension Means",
        f"- Phonon memory: {means['phonon_memory']:.4f}",
        f"- Thought vibration: {means['thought_vibration']:.4f}",
        f"- Semantic entanglement: {means['semantic_entanglement']:.4f}",
        f"- Manifold potential: {means['manifold_potential']:.4f}",
        "",
        "## Profile Ranking",
    ]

    for row in pr:
        lines.append(f"- {row['profile']}: mean={row['mean_resonance']:.4f} best={row['best_resonance']:.4f} (n={row['n']})")

    lines.extend(["", "## Damping Ranking", ])
    for row in dr:
        lines.append(f"- d={row['damping']}: mean={row['mean_resonance']:.4f} best={row['best_resonance']:.4f} (n={row['n']})")

    (output_dir / "phase2_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 2 focused resonance scan")
    p.add_argument("--phase1-root", default="data/thinking_engine_resonance", help="Root containing Phase 1 run folders")
    p.add_argument("--phase1-run-dir", default="", help="Optional explicit Phase 1 run directory")
    p.add_argument("--top-damping-count", type=int, default=4, help="How many top Phase 1 damping centers to use")
    p.add_argument("--top-profile-count", type=int, default=2, help="How many top Phase 1 profiles to seed")
    p.add_argument("--focus-window", type=float, default=0.5, help="Half-window around each top damping center")
    p.add_argument("--focus-step", type=float, default=0.25, help="Damping step inside focused windows")
    p.add_argument("--damping-min", type=float, default=0.25)
    p.add_argument("--damping-max", type=float, default=22.0)
    p.add_argument("--seeds", type=int, default=1, help="Seed count per condition (default 1 for efficiency)")
    p.add_argument("--steps", type=int, default=2400)
    p.add_argument("--sample-every", type=int, default=4)
    p.add_argument("--budget-hours", type=float, default=6.0)
    p.add_argument("--output-root", default="data/thinking_engine_resonance_phase2")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    phase1_root = (_SOL_ROOT / args.phase1_root).resolve()
    phase1_dir = Path(args.phase1_run_dir).resolve() if args.phase1_run_dir else _latest_run(phase1_root)
    args.phase1_run_dir = str(phase1_dir)

    ctx = _load_phase1_context(phase1_dir)
    top_profiles = _extract_top_profiles(ctx, max(1, args.top_profile_count))
    top_dampings = _extract_top_dampings(ctx, max(1, args.top_damping_count))
    focused_damping = _build_focused_damping_grid(
        top_dampings,
        half_window=max(0.0, float(args.focus_window)),
        step=max(0.05, float(args.focus_step)),
        dmin=float(args.damping_min),
        dmax=float(args.damping_max),
    )

    phase2_profiles: dict[str, dict[str, float]] = {}
    for base_name in top_profiles:
        if base_name not in phase1.BELIEF_PROFILES:
            continue
        for variant_name, variant_mult in _variant_specs():
            new_name, new_profile = _compose_profile(base_name, variant_name, variant_mult)
            phase2_profiles[new_name] = new_profile

    if not phase2_profiles:
        raise RuntimeError("No Phase 2 profiles were generated from Phase 1 context")
    if not focused_damping:
        raise RuntimeError("Focused damping grid is empty")

    for k, v in phase2_profiles.items():
        phase1.BELIEF_PROFILES[k] = v

    trial_plan = phase1._build_trial_plan(args.seeds, focused_damping, sorted(phase2_profiles.keys()))
    print(f"Phase 1 source: {phase1_dir}")
    print(f"Top phase1 profiles: {top_profiles}")
    print(f"Top phase1 damping centers: {top_dampings}")
    print(f"Focused damping points: {len(focused_damping)}")
    print(f"Phase2 profile variants: {len(phase2_profiles)}")
    print(f"Planned trials: {len(trial_plan)}")
    if args.dry_run:
        return 0

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = (_SOL_ROOT / args.output_root / ts).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    plan = {
        "phase1_run_dir": str(phase1_dir),
        "top_profiles": top_profiles,
        "top_damping_centers": top_dampings,
        "focused_damping": focused_damping,
        "phase2_profiles": phase2_profiles,
        "args": vars(args),
    }
    (output_dir / "phase2_plan.json").write_text(json.dumps(plan, indent=2, default=str), encoding="utf-8")

    labels_by_id, groups_by_id = phase1._load_graph_info()
    start = time.time()
    deadline = start + float(args.budget_hours) * 3600.0
    trials: list[dict[str, Any]] = []

    log_path = output_dir / "run_log.txt"
    trials_path = output_dir / "trials.jsonl"

    with open(log_path, "w", encoding="utf-8") as logf, open(trials_path, "w", encoding="utf-8") as trialf:
        def log(msg: str):
            stamp = datetime.now().strftime("%H:%M:%S")
            line = f"[{stamp}] {msg}"
            print(line, flush=True)
            logf.write(line + "\n")
            logf.flush()

        log("Starting Phase 2 focused resonance scan")
        log(f"Output: {output_dir}")

        for idx, cfg in enumerate(trial_plan, start=1):
            if time.time() >= deadline:
                log(f"Budget reached at trial {idx - 1}; stopping")
                break

            t0 = time.time()
            t = phase1.run_trial(
                config=cfg,
                steps=args.steps,
                sample_every=args.sample_every,
                labels_by_id=labels_by_id,
                groups_by_id=groups_by_id,
            )
            t["trial_index"] = idx
            t["duration_sec"] = time.time() - t0
            t["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
            trials.append(t)
            trialf.write(json.dumps(t, ensure_ascii=False) + "\n")

            if idx % 10 == 0:
                log(f"Completed {idx}/{len(trial_plan)} | resonance={t['resonance_index']:.4f} ({t['profile']} d={t['damping']})")

        end = time.time()
        summary = _summarize_phase2(trials, ctx, args, start, end)
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        _render_phase2_report(summary, output_dir)
        log("Wrote summary.json and phase2_report.md")
        log(f"Trials completed: {len(trials)}")

    print(f"Done. Artifacts: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
