#!/usr/bin/env python3
"""
Resonance Morning Helper
========================

Generates a concise team briefing from resonance scan artifacts.

Input:
  data/thinking_engine_resonance/<timestamp>/trials.jsonl

Outputs (written inside the selected run directory):
  - morning_brief.md
  - morning_brief.json

Works with both completed and in-progress runs.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _find_latest_run(root: Path) -> Path:
    if not root.exists():
        raise FileNotFoundError(f"Run root does not exist: {root}")
    runs = [p for p in root.iterdir() if p.is_dir()]
    if not runs:
        raise FileNotFoundError(f"No run directories found under: {root}")
    runs.sort(key=lambda p: p.name)
    return runs[-1]


def _read_trials(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Trials file not found: {path}")

    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _top_trials(rows: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    scored = sorted(rows, key=lambda r: _safe_float(r.get("resonance_index"), 0.0), reverse=True)
    return scored[:top_n]


def _profile_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_profile: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        profile = str(r.get("profile", "unknown"))
        by_profile.setdefault(profile, []).append(r)

    out: list[dict[str, Any]] = []
    for profile, entries in by_profile.items():
        vals = [_safe_float(e.get("resonance_index"), 0.0) for e in entries]
        top = max(entries, key=lambda e: _safe_float(e.get("resonance_index"), 0.0))
        out.append(
            {
                "profile": profile,
                "trials": len(entries),
                "mean_resonance": statistics.mean(vals) if vals else 0.0,
                "best_resonance": _safe_float(top.get("resonance_index"), 0.0),
                "best_damping": _safe_float(top.get("damping"), 0.0),
                "best_seed": int(top.get("seed", -1)),
            }
        )
    out.sort(key=lambda x: x["mean_resonance"], reverse=True)
    return out


def _damping_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_damping: dict[float, list[float]] = {}
    for r in rows:
        damping = _safe_float(r.get("damping"), 0.0)
        score = _safe_float(r.get("resonance_index"), 0.0)
        by_damping.setdefault(damping, []).append(score)

    out: list[dict[str, Any]] = []
    for damping, vals in by_damping.items():
        out.append(
            {
                "damping": damping,
                "trials": len(vals),
                "mean_resonance": statistics.mean(vals) if vals else 0.0,
                "max_resonance": max(vals) if vals else 0.0,
            }
        )
    out.sort(key=lambda x: x["mean_resonance"], reverse=True)
    return out


def _build_summary(rows: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    if not rows:
        return {
            "status": "no_trials",
            "trial_count": 0,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    top = _top_trials(rows, top_n)
    profile = _profile_table(rows)
    damping = _damping_table(rows)

    metric_means = {
        "resonance_index": statistics.mean(_safe_float(r.get("resonance_index"), 0.0) for r in rows),
        "phonon_memory": statistics.mean(_safe_float(r.get("phonon_memory"), 0.0) for r in rows),
        "thought_vibration": statistics.mean(_safe_float(r.get("thought_vibration"), 0.0) for r in rows),
        "semantic_entanglement": statistics.mean(_safe_float(r.get("semantic_entanglement"), 0.0) for r in rows),
        "manifold_potential": statistics.mean(_safe_float(r.get("manifold_potential"), 0.0) for r in rows),
    }

    return {
        "status": "ok",
        "trial_count": len(rows),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "metric_means": metric_means,
        "top_trials": top,
        "profile_ranking": profile,
        "damping_ranking": damping[:12],
    }


def _render_markdown(summary: dict[str, Any]) -> str:
    if summary.get("status") != "ok":
        return "# Resonance Morning Brief\n\nNo trials available yet.\n"

    means = summary["metric_means"]
    top_trials = summary["top_trials"]
    profiles = summary["profile_ranking"]
    damping = summary["damping_ranking"]

    lines = [
        "# Resonance Morning Brief",
        "",
        "## Snapshot",
        f"- Generated UTC: {summary['generated_at_utc']}",
        f"- Trials observed: {summary['trial_count']}",
        f"- Mean resonance index: {means['resonance_index']:.4f}",
        "",
        "## Mean Dimension Scores",
        f"- Phonon memory: {means['phonon_memory']:.4f}",
        f"- Thought vibration: {means['thought_vibration']:.4f}",
        f"- Semantic entanglement: {means['semantic_entanglement']:.4f}",
        f"- Manifold potential: {means['manifold_potential']:.4f}",
        "",
        "## Top Resonance Windows",
    ]

    for i, trial in enumerate(top_trials, start=1):
        lines.append(
            f"- #{i}: profile={trial.get('profile')} damping={trial.get('damping')} seed={trial.get('seed')} "
            f"resonance={_safe_float(trial.get('resonance_index')):.4f} basin={trial.get('final_basin_label')}[{trial.get('final_basin_id')}]"
        )

    lines.append("")
    lines.append("## Profile Ranking")
    for row in profiles:
        lines.append(
            f"- {row['profile']}: mean={row['mean_resonance']:.4f} best={row['best_resonance']:.4f} "
            f"at d={row['best_damping']} seed={row['best_seed']} (n={row['trials']})"
        )

    lines.append("")
    lines.append("## Damping Ranking (Top 12 by mean)")
    for row in damping:
        lines.append(
            f"- d={row['damping']}: mean={row['mean_resonance']:.4f} max={row['max_resonance']:.4f} (n={row['trials']})"
        )

    lines.extend(
        [
            "",
            "## Team Next Actions",
            "- Lock the top 3 damping windows and run a focused seed expansion around each.",
            "- Compare top profile against runner-up at identical damping to isolate belief-profile lift.",
            "- Flag windows where semantic entanglement rises while manifold potential falls for follow-up probes.",
            "",
        ]
    )

    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a morning brief for resonance runs.")
    parser.add_argument(
        "--run-root",
        default="data/thinking_engine_resonance",
        help="Root directory containing timestamped resonance runs.",
    )
    parser.add_argument(
        "--run-dir",
        default="",
        help="Optional explicit run directory. If omitted, latest under --run-root is used.",
    )
    parser.add_argument("--top-n", type=int, default=10, help="Number of top windows to include.")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously refresh outputs while new trials arrive.",
    )
    parser.add_argument(
        "--interval-sec",
        type=float,
        default=600.0,
        help="Refresh interval in seconds when --watch is enabled (default 600 = 10 min).",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=0,
        help="Optional max refresh cycles in watch mode (0 = run until interrupted).",
    )
    return parser.parse_args()


def _refresh_once(run_dir: Path, top_n: int) -> int:
    trials = _read_trials(run_dir / "trials.jsonl")
    summary = _build_summary(trials, max(1, top_n))
    brief_md = _render_markdown(summary)

    out_md = run_dir / "morning_brief.md"
    out_json = run_dir / "morning_brief.json"
    out_md.write_text(brief_md, encoding="utf-8")
    out_json.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print(f"Run directory: {run_dir}")
    print(f"Trials parsed: {len(trials)}")
    print(f"Wrote: {out_md}")
    print(f"Wrote: {out_json}")
    return len(trials)


def main() -> int:
    args = _parse_args()

    root = Path(args.run_root)
    run_dir = Path(args.run_dir) if args.run_dir else _find_latest_run(root)
    run_dir = run_dir.resolve()

    if not args.watch:
        _refresh_once(run_dir, args.top_n)
        return 0

    interval = max(1.0, float(args.interval_sec))
    trials_path = run_dir / "trials.jsonl"
    print(f"Watch mode enabled: interval={interval:.1f}s run_dir={run_dir}")

    last_size = -1
    cycles = 0
    while True:
        try:
            current_size = trials_path.stat().st_size if trials_path.exists() else -1
            if current_size != last_size:
                count = _refresh_once(run_dir, args.top_n)
                now = datetime.now().strftime("%H:%M:%S")
                print(f"[{now}] Refreshed morning brief (trials={count}, bytes={current_size})")
                last_size = current_size
            else:
                now = datetime.now().strftime("%H:%M:%S")
                print(f"[{now}] No new trial data; keeping previous brief")
        except KeyboardInterrupt:
            print("Watch mode interrupted by user")
            return 0
        except Exception as exc:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] Refresh warning: {exc}")

        cycles += 1
        if args.max_cycles > 0 and cycles >= args.max_cycles:
            print(f"Reached max cycles ({args.max_cycles}). Exiting watch mode.")
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
