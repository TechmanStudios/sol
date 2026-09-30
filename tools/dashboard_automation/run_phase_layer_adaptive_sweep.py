"""Adaptive phase-layer sweep (coarse scan + automatic refinement).

Goal
----
Run a wide damping scan (coarse) and then automatically bracket/refine around
any detected transition bands (anomalies) in the same invocation.

This script is designed to:
- Start at damping=0 and scan up to a user-provided max (default 20).
- Use interleaved ordering (chunked) to reduce session drift.
- Keep invariants explicit (dt/steps/press/etc).
- Bypass the UI damping slider (damping is passed directly to physics.step by
  the injected sweep harness).

Outputs
-------
Creates a batch directory under solData/testResults/phase_layers/ and writes:
- command_queue/ + command_done/ + command_results/
- downloaded *_summary_*.csv and *_trace_*.csv
- phase_layer/phase_layer_trace_*.{csv,md}
- compare/ cognitive-load plots and tables
- adaptive_summary.md describing what was refined and why

Example
-------
python tools/dashboard_automation/run_phase_layer_adaptive_sweep.py \
  --damp-min 0 --damp-max 20 --coarse-step 1.0 --coarse-runs 10 \
  --refine-step 0.1 --refine-span 1.0 --refine-runs 20 \
  --budget 1200 --steps 3000
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _parse_int_list(s: str) -> list[int]:
    s = (s or "").strip()
    if not s:
        return []
    out: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


def _arange_inclusive(lo: float, hi: float, step: float) -> list[float]:
    if step <= 0:
        raise ValueError("step must be > 0")
    out: list[float] = []
    x = float(lo)
    # Use a tolerance so we include hi when it lands close.
    tol = abs(step) * 1e-9 + 1e-12
    while x <= hi + tol:
        out.append(float(x))
        x += step
    # Clamp last value to hi if close.
    if out and abs(out[-1] - hi) <= tol:
        out[-1] = float(hi)
    return out


def _stem(prefix: str, damping: float, chunk: int) -> str:
    # Use 12 significant digits to keep filenames stable but informative.
    return f"{prefix}_d{damping:.12g}_c{chunk:02d}".replace(".", "p")


def _run_py(script: Path, args: list[str]) -> None:
    import subprocess

    subprocess.check_call([sys.executable, str(script), *args])


def _mk_batch(root: Path) -> dict[str, Path]:
    q = root / "command_queue"
    done = root / "command_done"
    results = root / "command_results"
    q.mkdir(parents=True, exist_ok=True)
    done.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    return {"root": root, "queue": q, "done": done, "results": results}


def _make_command(
    *,
    dashboard: str,
    out_prefix: str,
    runs: int,
    timeout_s: float,
    params: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "sol.dashboard.sweep.v1",
        "dashboard": dashboard,
        "outPrefix": out_prefix,
        "runs": int(runs),
        "timeoutS": float(timeout_s),
        "params": params,
        "meta": meta,
    }


@dataclass
class Boundary:
    d0: float
    d1: float
    score: float
    reason: str


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _read_agg_csv(path: Path) -> list[dict[str, str]]:
    import csv

    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({k: (v or "") for k, v in row.items()})
    return rows


def _pick_boundaries(
    agg_rows: list[dict[str, str]],
    *,
    pass_jump_threshold: float,
    score_threshold: float,
) -> list[Boundary]:
    # Expect agg rows sorted by damping.
    out: list[Boundary] = []

    def get(row: dict[str, str], key: str) -> float:
        return _safe_float(row.get(key))

    for i in range(1, len(agg_rows)):
        a = agg_rows[i - 1]
        b = agg_rows[i]
        d0 = get(a, "damping")
        d1 = get(b, "damping")
        if not (math.isfinite(d0) and math.isfinite(d1)):
            continue

        p0 = get(a, "budgetPassRate")
        p1 = get(b, "budgetPassRate")
        dp = abs(p1 - p0) if (math.isfinite(p0) and math.isfinite(p1)) else 0.0

        peak0 = get(a, "peakPMax_mean")
        peak1 = get(b, "peakPMax_mean")
        dpeak = abs(peak1 - peak0) if (math.isfinite(peak0) and math.isfinite(peak1)) else 0.0

        fs0 = get(a, "failStep_mean")
        fs1 = get(b, "failStep_mean")
        dfs = abs(fs1 - fs0) if (math.isfinite(fs0) and math.isfinite(fs1)) else 0.0

        # Simple composite score; tuneable but intentionally conservative.
        score = (5.0 * dp) + (dpeak / 5.0) + (dfs / 200.0)

        reasons: list[str] = []
        if dp >= pass_jump_threshold:
            reasons.append(f"passJump={dp:.3f}")
        if score >= score_threshold:
            reasons.append(f"score={score:.3f}")

        if reasons:
            out.append(Boundary(d0=d0, d1=d1, score=score, reason=",".join(reasons)))

    # Prefer highest scores first.
    out.sort(key=lambda b: b.score, reverse=True)
    return out


def _merge_windows(windows: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not windows:
        return []
    ws = sorted([(min(a, b), max(a, b)) for a, b in windows])
    merged: list[tuple[float, float]] = [ws[0]]
    for a, b in ws[1:]:
        pa, pb = merged[-1]
        if a <= pb:
            merged[-1] = (pa, max(pb, b))
        else:
            merged.append((a, b))
    return merged


def _window_points(lo: float, hi: float, step: float, *, clamp_lo: float, clamp_hi: float) -> list[float]:
    lo2 = max(clamp_lo, float(lo))
    hi2 = min(clamp_hi, float(hi))
    if hi2 < lo2:
        return []
    pts = _arange_inclusive(lo2, hi2, step)
    # Deduplicate rounding artifacts.
    out: list[float] = []
    seen: set[str] = set()
    for x in pts:
        k = f"{x:.12g}"
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()

    ap.add_argument("--dashboard", default="sol_dashboard_v3_7_2.html")

    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--dt", type=float, default=0.12)
    ap.add_argument("--press-slider", type=float, default=200.0)
    ap.add_argument("--mode", default="multiAgentTrain")

    ap.add_argument("--scenario", default="distributed")
    ap.add_argument("--agent-target-ids", default="64,82,79,12,13,14")
    ap.add_argument("--probe-ids", default="64,82,79")
    ap.add_argument("--agent-count", type=int, default=6)
    ap.add_argument("--targets-per-pulse", type=int, default=3)
    ap.add_argument("--pulse-step", type=int, default=100)
    ap.add_argument("--pulse-every", type=int, default=4)
    ap.add_argument("--target-id", type=int, default=64)
    ap.add_argument("--inject-amount", type=float, default=1.0)

    ap.add_argument("--budget", type=int, default=1200)
    ap.add_argument("--c-bandwidth-tol", type=float, default=0.02)
    ap.add_argument("--include-pure-c", action="store_true")

    ap.add_argument("--damp-min", type=float, default=0.0)
    ap.add_argument("--damp-max", type=float, default=20.0)

    ap.add_argument("--coarse-step", type=float, default=1.0)
    ap.add_argument("--coarse-runs", type=int, default=10)
    ap.add_argument("--coarse-chunk", type=int, default=5)

    ap.add_argument("--timeout-s", type=float, default=1200.0)

    ap.add_argument("--refine-step", type=float, default=0.1)
    ap.add_argument(
        "--refine-span",
        type=float,
        default=1.0,
        help="Width of each refine window (in damping units) centered on detected boundaries.",
    )
    ap.add_argument("--refine-runs", type=int, default=20)
    ap.add_argument("--refine-chunk", type=int, default=5)
    ap.add_argument("--max-refine-windows", type=int, default=3)

    ap.add_argument("--pass-jump-threshold", type=float, default=0.1)
    ap.add_argument("--score-threshold", type=float, default=1.0)

    ap.add_argument(
        "--plateau-eps",
        type=float,
        default=0.0001,
        help="Plateau epsilon forwarded to the phase-layer analyzer for the final combined report.",
    )

    ap.add_argument("--out-root", default="", help="Optional output folder (absolute or relative).")

    args = ap.parse_args()

    if args.damp_max < args.damp_min:
        raise SystemExit("--damp-max must be >= --damp-min")

    if args.coarse_runs <= 0 or args.coarse_chunk <= 0:
        raise SystemExit("--coarse-runs and --coarse-chunk must be > 0")
    if args.coarse_runs % args.coarse_chunk != 0:
        raise SystemExit("--coarse-runs must be divisible by --coarse-chunk")

    if args.refine_runs <= 0 or args.refine_chunk <= 0:
        raise SystemExit("--refine-runs and --refine-chunk must be > 0")
    if args.refine_runs % args.refine_chunk != 0:
        raise SystemExit("--refine-runs must be divisible by --refine-chunk")

    sol_root = Path(__file__).resolve().parents[2]
    tools_dir = sol_root / "tools" / "dashboard_automation"
    run_script = tools_dir / "run_dashboard_sweep.py"
    analyze_script = tools_dir / "analyze_cognitive_load_sweep.py"
    compare_script = tools_dir / "analyze_cognitive_load_compare.py"
    phase_script = tools_dir / "analyze_phase_layer_traces.py"

    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
    if args.out_root:
        out_root = Path(args.out_root).resolve()
    else:
        out_root = (sol_root / "solData" / "testResults" / "phase_layers" / f"adaptive_{stamp}").resolve()

    out_root.mkdir(parents=True, exist_ok=True)
    paths = _mk_batch(out_root)

    probe_ids = _parse_int_list(str(args.probe_ids))
    agent_targets_all = _parse_int_list(str(args.agent_target_ids))
    agent_count = min(int(args.agent_count), len(agent_targets_all))
    agent_targets = agent_targets_all[:agent_count]

    targets_per_pulse = min(int(args.targets_per_pulse), agent_count)
    pulse_every = int(args.pulse_every)
    inject_amount = float(args.inject_amount)
    approx_rate = inject_amount * float(targets_per_pulse) / float(max(1, pulse_every))

    common_params = {
        "steps": int(args.steps),
        "dts": [float(args.dt)],
        "modes": [str(args.mode)],
        "pressSliderVal": float(args.press_slider),
        "injectAmount": float(inject_amount),
        "targetId": int(args.target_id),
        "targetIds": agent_targets,
        "targetsPerPulse": int(targets_per_pulse),
        "pulseStep": int(args.pulse_step),
        "pulseEvery": int(pulse_every),
        "pulseCount": 0,
        "probeIds": probe_ids,
        "traceEvery": 50,
        "progressEvery": 250,
        "adaptiveTrace": True,
        "guardrail": {"type": "none"},
    }

    def run_queue() -> None:
        _run_py(
            run_script,
            [
                "--firefox-dev",
                "--headless",
                "--download-dir",
                str(out_root),
                "--run-command-dir",
                str(paths["queue"]),
                "--command-done-dir",
                str(paths["done"]),
                "--command-results-dir",
                str(paths["results"]),
                "--timeout-s",
                str(float(args.timeout_s)),
                "--auto",
                "--browser-retries",
                "2",
            ],
        )

    def run_analyses() -> None:
        _run_py(analyze_script, ["--batch-dir", str(out_root), "--download-dir", str(out_root)])

        compare_out = out_root / "compare"
        compare_args = [
            "--batch-dirs",
            str(out_root),
            "--out-dir",
            str(compare_out),
            "--x-axis",
            "damping",
            "--series-by",
            "scenario",
            "--reco-budget",
            str(int(args.budget)),
            "--c-bandwidth-tol",
            str(float(args.c_bandwidth_tol)),
        ]
        if bool(args.include_pure_c):
            compare_args.append("--include-pure-c")
        _run_py(compare_script, compare_args)

        _run_py(
            phase_script,
            [
                "--batch-dir",
                str(out_root),
                "--budget",
                str(int(args.budget)),
                "--report-digits",
                "12",
                "--agg-digits",
                "9",
                "--plateau-eps",
                str(float(args.plateau_eps)),
            ],
        )

    cmd_i = 0

    def enqueue_phase(*, phase: str, dampings: list[float], runs_per_point: int, chunk_size: int) -> None:
        nonlocal cmd_i
        if not dampings:
            return
        chunks = runs_per_point // chunk_size
        queue = paths["queue"]

        for chunk in range(1, chunks + 1):
            for d in dampings:
                cmd_i += 1
                params = dict(common_params)
                params["dampings"] = [float(d)]

                out_prefix = f"phaseLayer_{phase}_{_stem('damp', float(d), chunk)}"
                meta = {
                    "phase": "PHASE_LAYER",
                    "kind": "phaseLayer.adaptive.v1",
                    "scanPhase": phase,
                    "scenario": str(args.scenario),
                    "knob": "damping",
                    "damping": float(d),
                    "chunk": int(chunk),
                    "chunkSize": int(chunk_size),
                    "runsPerPoint": int(runs_per_point),
                    "approxInjectRate": float(approx_rate),
                    "injectAmount": float(inject_amount),
                    "agentCount": int(agent_count),
                    "targetsPerPulse": int(targets_per_pulse),
                    "pulseEvery": int(pulse_every),
                    "dt": float(args.dt),
                    "steps": int(args.steps),
                    "pressSliderVal": float(args.press_slider),
                    "budget": int(args.budget),
                    "dampingSourceRequired": "physics.step",
                }

                cmd = _make_command(
                    dashboard=str(args.dashboard),
                    out_prefix=out_prefix,
                    runs=int(chunk_size),
                    timeout_s=float(args.timeout_s),
                    params=params,
                    meta=meta,
                )

                stem = f"cmd_{cmd_i:05d}_{phase}_{_stem('damp', float(d), chunk)}"
                _write_json(queue / f"{stem}.json", cmd)

    # -----------------
    # Phase 1: coarse
    # -----------------
    coarse_dampings = _arange_inclusive(float(args.damp_min), float(args.damp_max), float(args.coarse_step))
    enqueue_phase(phase="coarse", dampings=coarse_dampings, runs_per_point=int(args.coarse_runs), chunk_size=int(args.coarse_chunk))
    run_queue()
    run_analyses()

    # Detect boundaries from current aggregates.
    agg_path = out_root / "phase_layer" / "phase_layer_trace_agg.csv"
    if not agg_path.exists():
        raise SystemExit(f"Expected aggregates at: {agg_path}")

    agg_rows = _read_agg_csv(agg_path)
    # Sort by numeric damping for robustness.
    agg_rows.sort(key=lambda r: _safe_float(r.get("damping")))

    boundaries = _pick_boundaries(
        agg_rows,
        pass_jump_threshold=float(args.pass_jump_threshold),
        score_threshold=float(args.score_threshold),
    )

    # Choose windows around the top-N boundaries.
    chosen = boundaries[: max(0, int(args.max_refine_windows))]
    half = float(args.refine_span) / 2.0
    windows = _merge_windows([(0.5 * (b.d0 + b.d1) - half, 0.5 * (b.d0 + b.d1) + half) for b in chosen])

    refine_dampings: list[float] = []
    for lo, hi in windows:
        refine_dampings.extend(
            _window_points(
                lo,
                hi,
                float(args.refine_step),
                clamp_lo=float(args.damp_min),
                clamp_hi=float(args.damp_max),
            )
        )

    # Deduplicate and keep sorted.
    refine_dampings = sorted({f"{d:.12g}": d for d in refine_dampings}.values())

    # -----------------
    # Phase 2: refine
    # -----------------
    if refine_dampings:
        enqueue_phase(
            phase="refine",
            dampings=refine_dampings,
            runs_per_point=int(args.refine_runs),
            chunk_size=int(args.refine_chunk),
        )
        run_queue()
        run_analyses()

    # Write an adaptive summary.
    lines: list[str] = []
    lines.append("# Adaptive phase-layer sweep summary")
    lines.append("")
    lines.append(f"Batch: `{out_root}`")
    lines.append("")
    lines.append("## Coarse scan")
    lines.append("")
    lines.append(f"- Range: {float(args.damp_min)} to {float(args.damp_max)}")
    lines.append(f"- Step: {float(args.coarse_step)}")
    lines.append(f"- Runs/point: {int(args.coarse_runs)} (chunk={int(args.coarse_chunk)})")
    lines.append("")

    lines.append("## Detected boundaries")
    lines.append("")
    if not boundaries:
        lines.append("- None detected (under current thresholds).")
    else:
        for b in boundaries[:10]:
            lines.append(f"- {b.d0:.12g} -> {b.d1:.12g} (score={b.score:.3f}; {b.reason})")
    lines.append("")

    lines.append("## Refine pass")
    lines.append("")
    if not refine_dampings:
        lines.append("- No refine points scheduled.")
    else:
        lines.append(f"- Windows: {len(windows)}")
        for lo, hi in windows:
            lines.append(f"  - [{lo:.12g}, {hi:.12g}]")
        lines.append(f"- Step: {float(args.refine_step)}")
        lines.append(f"- Runs/point: {int(args.refine_runs)} (chunk={int(args.refine_chunk)})")
        lines.append(f"- Points: {len(refine_dampings)}")
    lines.append("")

    lines.append("## Key outputs")
    lines.append("")
    lines.append(f"- Phase-layer report: `{out_root / 'phase_layer' / 'phase_layer_trace_report.md'}`")
    lines.append(f"- Phase-layer aggregates: `{out_root / 'phase_layer' / 'phase_layer_trace_agg.csv'}`")
    lines.append(f"- Compare report: `{out_root / 'compare' / 'cognitive_load_compare.md'}`")

    (out_root / "adaptive_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Adaptive sweep complete. Root: {out_root}")
    print(f"Summary: {out_root / 'adaptive_summary.md'}")
    print(f"Phase-layer report: {out_root / 'phase_layer' / 'phase_layer_trace_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
