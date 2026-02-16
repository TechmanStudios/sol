#!/usr/bin/env python3
"""
SOL Phonon Micro-Sweep RSI Chain

Runs chained critical-zone micro-sweeps where each sweep updates the next
center/window using an RSI-style signal derived from prior sweep outcomes.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import basin_phonon_sweep as bps


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_rsi(series: list[float], period: int = 5) -> float | None:
    if len(series) < period + 1:
        return None
    window = series[-(period + 1):]
    deltas = [window[i] - window[i - 1] for i in range(1, len(window))]
    gains = [max(0.0, d) for d in deltas]
    losses = [max(0.0, -d) for d in deltas]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def damping_grid(center: float, half_window: float, step: float, dmin: float, dmax: float) -> list[float]:
    start = clamp(center - half_window, dmin, dmax)
    end = clamp(center + half_window, dmin, dmax)
    n = int(round((end - start) / step)) + 1
    values = [round(start + i * step, 6) for i in range(n)]
    if values and values[-1] < end:
        values.append(round(end, 6))
    return sorted(set(values))


def inject_path_lazy(directory: Path) -> None:
    d = str(directory)
    if d not in sys.path:
        sys.path.insert(0, d)


def try_get_llm_client(verbose: bool = False):
    try:
        sol_root = Path(__file__).resolve().parent
        inject_path_lazy(sol_root / "tools" / "sol-llm")
        from client import SolLLM
        if not SolLLM.is_available():
            return None
        return SolLLM(verbose=verbose)
    except Exception:
        return None


def coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def summarize_boundary(sweep_records: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(sweep_records, key=lambda x: x["damping"])
    if len(ordered) < 2:
        single = ordered[0]
        return {
            "boundary_damping": single["damping"],
            "boundary_strength": 0.0,
            "mode_drop": 0.0,
            "transition_from": single["final_basin_label"],
            "transition_to": single["final_basin_label"],
        }

    gradients: list[dict[str, Any]] = []
    for i in range(1, len(ordered)):
        prev_row = ordered[i - 1]
        row = ordered[i]
        dd = row["damping"] - prev_row["damping"]
        if dd <= 0:
            continue
        mode_drop = float(prev_row["n_phonon_modes"] - row["n_phonon_modes"])
        boundary_strength = abs(mode_drop) / dd
        gradients.append(
            {
                "left": prev_row,
                "right": row,
                "boundary_damping": round((prev_row["damping"] + row["damping"]) / 2.0, 6),
                "boundary_strength": boundary_strength,
                "mode_drop": mode_drop,
            }
        )

    best = max(gradients, key=lambda x: x["boundary_strength"])
    return {
        "boundary_damping": best["boundary_damping"],
        "boundary_strength": best["boundary_strength"],
        "mode_drop": best["mode_drop"],
        "transition_from": best["left"]["final_basin_label"],
        "transition_to": best["right"]["final_basin_label"],
    }


def run_trial(damping: float, labels: dict[int, str], injection_ids: set[int]) -> dict[str, Any]:
    trial = bps.run_phonon_trial(damping)
    coherence = bps.compute_phase_coherence(trial["rho_traces"], trial["node_ids"], injection_ids)
    spectral = bps.compute_spectral_energy(trial["rho_traces"])
    n_modes = bps.count_active_phonon_modes(trial["rho_traces"])
    final = trial["final_metrics"]
    basin = final.get("rhoMaxId")
    return {
        "damping": damping,
        "final_basin": basin,
        "final_basin_label": labels.get(basin, "None") if basin is not None else "None",
        "n_phonon_modes": int(n_modes),
        "phase_coherence": float(coherence),
        "heartbeat_power_ratio": float(spectral["heartbeat_power_ratio"]),
        "final_entropy": float(final.get("entropy", 0.0)),
        "final_maxrho": float(final.get("maxRho", 0.0)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run chained phonon micro-sweeps with RSI-style adaptation.")
    parser.add_argument("--sweeps", type=int, default=40)
    parser.add_argument("--steps", type=int, default=350)
    parser.add_argument("--center", type=float, default=83.323376)
    parser.add_argument("--half-window", type=float, default=0.10)
    parser.add_argument("--step", type=float, default=0.01)
    parser.add_argument("--damping-min", type=float, default=82.8)
    parser.add_argument("--damping-max", type=float, default=83.6)
    parser.add_argument("--rsi-period", type=int, default=4)
    parser.add_argument("--rsi-shift", type=float, default=0.02)
    parser.add_argument("--window-decay", type=float, default=0.9)
    parser.add_argument("--window-growth", type=float, default=1.08)
    parser.add_argument("--window-min", type=float, default=0.08)
    parser.add_argument("--window-max", type=float, default=0.35)
    parser.add_argument("--llm-advisor-every-sweeps", type=int, default=20)
    parser.add_argument("--llm-advisor-lookback", type=int, default=10)
    parser.add_argument("--llm-advisor-max-center-offset", type=float, default=0.01)
    parser.add_argument("--llm-advisor-min-window-scale", type=float, default=0.9)
    parser.add_argument("--llm-advisor-max-window-scale", type=float, default=1.1)
    parser.add_argument("--llm-advisor-max-rsi-shift", type=float, default=0.03)
    parser.add_argument("--llm-advisor-verbose", action="store_true")
    parser.add_argument("--endgame-rsi-threshold", type=float, default=85.0)
    parser.add_argument("--endgame-rsi-streak", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path("data") / "phonon_micro_rsi" / run_ts
    out_dir.mkdir(parents=True, exist_ok=True)

    labels, _groups = bps.load_graph_info()
    tmp_engine = bps.SOLEngine.from_default_graph()
    injection_ids: set[int] = set()
    for label, _amount in bps.MULTI_AGENT_INJECTIONS:
        for n in tmp_engine.physics.nodes:
            if n["label"].lower() == label.lower():
                injection_ids.add(n["id"])
                break

    bps.STEPS = int(args.steps)
    center = float(args.center)
    half_window = float(args.half_window)
    current_rsi_shift = abs(float(args.rsi_shift))
    boundary_history: list[float] = []
    boundary_rsi_history: list[float] = []
    fitness_history: list[float] = []
    sweep_summaries: list[dict[str, Any]] = []

    llm_client = None
    llm_enabled = args.llm_advisor_every_sweeps > 0
    if llm_enabled:
        llm_client = try_get_llm_client(verbose=args.llm_advisor_verbose)
        if llm_client is None:
            print("llm_advisor=unavailable; continuing numeric-only loop")
            llm_enabled = False

    llm_advice_path = out_dir / "llm_advice.jsonl"

    t0 = time.time()

    for sweep_idx in range(1, args.sweeps + 1):
        damp_values = damping_grid(
            center=center,
            half_window=half_window,
            step=args.step,
            dmin=args.damping_min,
            dmax=args.damping_max,
        )

        sweep_records = [run_trial(d, labels, injection_ids) for d in damp_values]
        boundary = summarize_boundary(sweep_records)
        boundary_d = float(boundary["boundary_damping"])
        boundary_strength = float(boundary["boundary_strength"])

        boundary_history.append(boundary_d)
        fitness_history.append(boundary_strength)

        boundary_rsi = compute_rsi(boundary_history, period=max(2, args.rsi_period))
        if boundary_rsi is not None:
            boundary_rsi_history.append(float(boundary_rsi))

        rsi_bias = 0.0
        if boundary_rsi is not None:
            if boundary_rsi > 70.0:
                rsi_bias = current_rsi_shift
            elif boundary_rsi < 30.0:
                rsi_bias = -current_rsi_shift

        next_center = clamp(boundary_d + rsi_bias, args.damping_min, args.damping_max)

        if len(fitness_history) > 1 and fitness_history[-1] > fitness_history[-2] * 1.05:
            next_window = half_window * args.window_decay
        else:
            next_window = half_window * args.window_growth

        endgame_forced_contraction = False
        if args.endgame_rsi_streak > 0 and len(boundary_rsi_history) >= args.endgame_rsi_streak:
            recent_rsi = boundary_rsi_history[-args.endgame_rsi_streak:]
            if all(r >= args.endgame_rsi_threshold for r in recent_rsi):
                next_window = half_window * args.window_decay
                endgame_forced_contraction = True

        next_window = clamp(next_window, args.window_min, args.window_max)

        llm_advice: dict[str, Any] | None = None
        if llm_enabled and llm_client is not None and sweep_idx % args.llm_advisor_every_sweeps == 0:
            lookback = max(1, int(args.llm_advisor_lookback))
            recent = sweep_summaries[-lookback:]
            compact_recent = [
                {
                    "sweep": row["sweep"],
                    "boundary_damping": row["boundary_damping"],
                    "boundary_strength": row["boundary_strength"],
                    "mode_drop": row["mode_drop"],
                    "boundary_rsi": row["boundary_rsi"],
                    "center_out": row["center_out"],
                    "half_window_out": row["half_window_out"],
                }
                for row in recent
            ]
            system = (
                "You are a bounded numeric advisor for a deterministic physics sweep controller. "
                "Prioritize stability and reproducibility. Suggest only small bounded nudges."
            )
            user = (
                "Return a JSON object with fields: "
                "apply_advice (bool), center_offset (float), window_scale (float), "
                "rsi_shift (float), reason (str).\n"
                "Rules: center_offset within +/-max_center_offset, "
                "window_scale in [min_window_scale, max_window_scale], "
                "rsi_shift in [0, max_rsi_shift].\n"
                "State:\n"
                f"- sweep_index: {sweep_idx}\n"
                f"- total_sweeps: {args.sweeps}\n"
                f"- damping_bounds: [{args.damping_min}, {args.damping_max}]\n"
                f"- current_center_candidate: {next_center}\n"
                f"- current_half_window_candidate: {next_window}\n"
                f"- current_rsi_shift: {current_rsi_shift}\n"
                f"- max_center_offset: {args.llm_advisor_max_center_offset}\n"
                f"- min_window_scale: {args.llm_advisor_min_window_scale}\n"
                f"- max_window_scale: {args.llm_advisor_max_window_scale}\n"
                f"- max_rsi_shift: {args.llm_advisor_max_rsi_shift}\n"
                "- recent_history_json:\n"
                f"{json.dumps(compact_recent)}"
            )
            schema = {
                "apply_advice": "bool",
                "center_offset": "float",
                "window_scale": "float",
                "rsi_shift": "float",
                "reason": "str",
            }
            response = llm_client.complete_json(
                user,
                system=system,
                schema=schema,
                task="reflection",
            )

            llm_advice = {
                "sweep": sweep_idx,
                "success": bool(response.success),
                "model": response.model,
                "role": response.role,
                "latency_sec": response.latency_sec,
                "error": response.error,
                "applied": False,
            }

            if response.success and isinstance(response.parsed, dict):
                parsed = response.parsed
                apply_flag = bool(parsed.get("apply_advice", True))
                center_offset = clamp(
                    coerce_float(parsed.get("center_offset"), 0.0),
                    -abs(args.llm_advisor_max_center_offset),
                    abs(args.llm_advisor_max_center_offset),
                )
                window_scale = clamp(
                    coerce_float(parsed.get("window_scale"), 1.0),
                    args.llm_advisor_min_window_scale,
                    args.llm_advisor_max_window_scale,
                )
                advised_rsi_shift = clamp(
                    abs(coerce_float(parsed.get("rsi_shift"), current_rsi_shift)),
                    0.0,
                    abs(args.llm_advisor_max_rsi_shift),
                )
                if apply_flag:
                    next_center = clamp(next_center + center_offset, args.damping_min, args.damping_max)
                    next_window = clamp(next_window * window_scale, args.window_min, args.window_max)
                    current_rsi_shift = advised_rsi_shift
                    llm_advice["applied"] = True
                llm_advice["parsed"] = {
                    "apply_advice": apply_flag,
                    "center_offset": center_offset,
                    "window_scale": window_scale,
                    "rsi_shift": advised_rsi_shift,
                    "reason": str(parsed.get("reason", ""))[:240],
                }

            with open(llm_advice_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(llm_advice) + "\n")

        sweep_summary = {
            "sweep": sweep_idx,
            "center_in": center,
            "half_window_in": half_window,
            "n_damping_samples": len(damp_values),
            "boundary_damping": boundary_d,
            "boundary_strength": boundary_strength,
            "mode_drop": boundary["mode_drop"],
            "transition_from": boundary["transition_from"],
            "transition_to": boundary["transition_to"],
            "boundary_rsi": boundary_rsi,
            "rsi_bias": rsi_bias,
            "rsi_shift": current_rsi_shift,
            "endgame_forced_contraction": endgame_forced_contraction,
            "center_out": next_center,
            "half_window_out": next_window,
            "mean_modes": statistics.mean(r["n_phonon_modes"] for r in sweep_records),
            "min_modes": min(r["n_phonon_modes"] for r in sweep_records),
            "max_modes": max(r["n_phonon_modes"] for r in sweep_records),
            "llm_advice": llm_advice,
            "records": sweep_records,
        }
        sweep_summaries.append(sweep_summary)

        print(
            f"sweep={sweep_idx:02d} center={center:.4f} -> {next_center:.4f} "
            f"window={half_window:.4f} -> {next_window:.4f} "
            f"boundary={boundary_d:.4f} strength={boundary_strength:.2f} rsi={boundary_rsi}"
        )

        center = next_center
        half_window = next_window

    runtime_sec = round(time.time() - t0, 2)

    top = max(sweep_summaries, key=lambda x: x["boundary_strength"])
    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "runtime_sec": runtime_sec,
        "config": {
            "sweeps": args.sweeps,
            "steps": args.steps,
            "start_center": args.center,
            "start_half_window": args.half_window,
            "damping_min": args.damping_min,
            "damping_max": args.damping_max,
            "step": args.step,
            "rsi_period": args.rsi_period,
            "rsi_shift": args.rsi_shift,
            "llm_advisor_every_sweeps": args.llm_advisor_every_sweeps,
            "llm_advisor_lookback": args.llm_advisor_lookback,
            "llm_advisor_max_center_offset": args.llm_advisor_max_center_offset,
            "llm_advisor_min_window_scale": args.llm_advisor_min_window_scale,
            "llm_advisor_max_window_scale": args.llm_advisor_max_window_scale,
            "llm_advisor_max_rsi_shift": args.llm_advisor_max_rsi_shift,
        },
        "best_boundary": {
            "sweep": top["sweep"],
            "boundary_damping": top["boundary_damping"],
            "boundary_strength": top["boundary_strength"],
            "mode_drop": top["mode_drop"],
            "transition_from": top["transition_from"],
            "transition_to": top["transition_to"],
        },
        "final_state": {
            "center": center,
            "half_window": half_window,
            "rsi_shift": current_rsi_shift,
            "latest_rsi": sweep_summaries[-1]["boundary_rsi"] if sweep_summaries else None,
        },
    }

    with open(out_dir / "sweeps.jsonl", "w", encoding="utf-8") as f:
        for row in sweep_summaries:
            f.write(json.dumps(row) + "\n")

    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    report_lines = [
        "# Phonon Micro-Sweep RSI Chain",
        "",
        f"- Runtime (sec): {runtime_sec}",
        f"- Sweeps: {args.sweeps}",
        f"- Start center/window: {args.center} / {args.half_window}",
        f"- Damping bounds: [{args.damping_min}, {args.damping_max}]",
        f"- LLM advisor cadence: every {args.llm_advisor_every_sweeps} sweeps",
        "",
        "## Best Boundary",
        f"- Sweep: {summary['best_boundary']['sweep']}",
        f"- Damping: {summary['best_boundary']['boundary_damping']}",
        f"- Strength: {summary['best_boundary']['boundary_strength']:.4f}",
        f"- Mode drop: {summary['best_boundary']['mode_drop']:.4f}",
        f"- Transition: {summary['best_boundary']['transition_from']} -> {summary['best_boundary']['transition_to']}",
        "",
        "## Final Adaptive State",
        f"- Center: {summary['final_state']['center']}",
        f"- Half-window: {summary['final_state']['half_window']}",
        f"- RSI shift: {summary['final_state']['rsi_shift']}",
        f"- Latest RSI: {summary['final_state']['latest_rsi']}",
        "",
        "## Artifacts",
        "- sweeps.jsonl",
        "- summary.json",
        "- llm_advice.jsonl (when advisor enabled)",
    ]
    (out_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"saved={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
