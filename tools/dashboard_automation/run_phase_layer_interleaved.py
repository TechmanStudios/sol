"""Run an interleaved phase-layer experiment around a damping boundary.

Goal
----
Estimate a transition probability curve (pass-rate vs damping for a step budget)
while minimizing session drift by interleaving conditions.

Strategy
--------
Instead of running all repeats for one damping at once, we run in chunks and
cycle through dampings:
  for chunk in 1..K:
    for damping in dampings:
      run <chunk_size> repeats

This approximates an AB/BA style order control without requiring mid-run
parameter changes inside the dashboard harness.

Outputs
-------
Under the batch directory, this script will run:
- run_dashboard_sweep.py (headless Firefox) to execute commands
- analyze_cognitive_load_sweep.py to produce cognitive_load_readout.csv/md
- analyze_cognitive_load_compare.py to produce plots/tables vs damping
- analyze_phase_layer_traces.py to produce phase_layer/* trace-derived tables

Example
-------
python tools/dashboard_automation/run_phase_layer_interleaved.py \
  --dampings "1.869131155,1.86913116,1.869131165,1.8691311675,1.86913117,1.869131175,1.86913118" \
  --runs-per-point 100 --chunk-size 10 --budget 1200
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
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


def _parse_float_list(s: str) -> list[float]:
    s = (s or "").strip()
    if not s:
        return []
    out: list[float] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    return out


def _stem(prefix: str, damping: float, chunk: int) -> str:
    return f"{prefix}_d{damping:.12g}_c{chunk:02d}".replace(".", "p")


def _make_command(*, dashboard: str, out_prefix: str, runs: int, timeout_s: float, params: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "sol.dashboard.sweep.v1",
        "dashboard": dashboard,
        "outPrefix": out_prefix,
        "runs": int(runs),
        "timeoutS": float(timeout_s),
        "params": params,
        "meta": meta,
    }


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


def main() -> int:
    ap = argparse.ArgumentParser()

    ap.add_argument("--dashboard", default="sol_dashboard_v3_7_2.html")
    ap.add_argument("--steps", type=int, default=4000)
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

    ap.add_argument("--dampings", required=True, help="Comma-separated damping values to interleave.")
    ap.add_argument("--runs-per-point", type=int, default=100)
    ap.add_argument("--chunk-size", type=int, default=10)
    ap.add_argument("--timeout-s", type=float, default=1200.0)

    ap.add_argument("--budget", type=int, default=1200)
    ap.add_argument("--c-bandwidth-tol", type=float, default=0.02)
    ap.add_argument("--include-pure-c", action="store_true")

    ap.add_argument("--out-root", default="", help="Optional output root under solData/testResults/.")

    args = ap.parse_args()

    dampings = _parse_float_list(str(args.dampings))
    if not dampings:
        raise SystemExit("--dampings must be non-empty")

    runs_per_point = int(args.runs_per_point)
    chunk_size = int(args.chunk_size)
    if runs_per_point <= 0 or chunk_size <= 0:
        raise SystemExit("--runs-per-point and --chunk-size must be > 0")
    if runs_per_point % chunk_size != 0:
        raise SystemExit("--runs-per-point must be divisible by --chunk-size for deterministic chunking")

    chunks = runs_per_point // chunk_size

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
        out_root = (sol_root / "solData" / "testResults" / "phase_layers" / stamp).resolve()

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

    # Interleaved enqueue.
    # NOTE: We keep one command file per (damping, chunk) so that the runner
    # uses a single outPrefix per damping (downloads are grouped by damping).
    queue = paths["queue"]
    cmd_i = 0
    for chunk in range(1, chunks + 1):
        for d in dampings:
            cmd_i += 1
            params = dict(common_params)
            params["dampings"] = [float(d)]

            out_prefix = f"phaseLayer_{_stem('damp', float(d), chunk)}"
            meta = {
                "phase": "PHASE_LAYER",
                "kind": "phaseLayer.interleaved.boundary.v1",
                "scenario": str(args.scenario),
                "knob": "damping",
                "damping": float(d),
                "dampingSourceRequired": "physics.step",
                "notes": "Damping passed directly to physics.step(dt, pressC, dampEff); do not rely on UI slider (quantized).",
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
            }

            cmd = _make_command(
                dashboard=str(args.dashboard),
                out_prefix=out_prefix,
                runs=int(chunk_size),
                timeout_s=float(args.timeout_s),
                params=params,
                meta=meta,
            )

            stem = f"cmd_{cmd_i:04d}_{_stem('damp', float(d), chunk)}"
            _write_json(queue / f"{stem}.json", cmd)

    # Execute.
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
            str(args.timeout_s),
            "--auto",
        ],
    )

    # Summaries.
    _run_py(analyze_script, ["--batch-dir", str(out_root), "--download-dir", str(out_root)])

    # Compare plots.
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

    # Phase-layer analysis directly on the batch root (will scan all *_trace_*.csv).
    _run_py(phase_script, ["--batch-dir", str(out_root), "--budget", str(int(args.budget))])

    print(f"Phase-layer interleaved run complete. Root: {out_root}")
    print(f"Compare: {compare_out / 'cognitive_load_compare.md'}")
    print(f"Phase-layer report: {out_root / 'phase_layer' / 'phase_layer_trace_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
