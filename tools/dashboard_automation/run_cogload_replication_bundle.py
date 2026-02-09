"""Run a small replication bundle for cognitive-load damping windows.

This is a convenience wrapper around:
- run_dashboard_sweep.py (headless Firefox)
- analyze_cognitive_load_sweep.py
- analyze_cognitive_load_compare.py

It writes two staged batches under solData/testResults/ and executes them.
"""

from __future__ import annotations

import argparse
import json
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


def _stem_from_damping(prefix: str, damping: float) -> str:
    return f"{prefix}_damp{damping:.10g}".replace(".", "p")


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


def _run_py(script: Path, args: list[str]) -> None:
    import subprocess

    cmd = [sys.executable, str(script), *args]
    subprocess.check_call(cmd)


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

    ap.add_argument("--runs-per-point", type=int, default=5)
    ap.add_argument("--timeout-s", type=float, default=1200.0)

    ap.add_argument("--budget", type=int, default=1200)
    ap.add_argument("--c-bandwidth-tol", type=float, default=0.02)
    ap.add_argument("--include-pure-c", action="store_true")

    ap.add_argument(
        "--window-a",
        default="1.1960095166889058,1.1962952656127983,1.196581014536691,1.1968667634605836,1.1971525123844762,1.197438261308369,1.1977240102322615",
        help="Comma-separated damping values for window A (spread basin).",
    )
    ap.add_argument(
        "--window-b",
        default="1.8690118729270682,1.8690475915425546,1.869083310158041,1.8691190287735275,1.869154747389014,1.8691904660045005,1.869226184619987",
        help="Comma-separated damping values for window B (budget boundary).",
    )

    ap.add_argument("--out-root", default="", help="Optional output root under solData/testResults/.")

    args = ap.parse_args()

    sol_root = Path(__file__).resolve().parents[2]
    tools_dir = sol_root / "tools" / "dashboard_automation"
    run_script = tools_dir / "run_dashboard_sweep.py"
    analyze_script = tools_dir / "analyze_cognitive_load_sweep.py"
    compare_script = tools_dir / "analyze_cognitive_load_compare.py"

    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
    if args.out_root:
        out_root = Path(args.out_root).resolve()
    else:
        out_root = (sol_root / "solData" / "testResults" / "cogload_replications" / stamp).resolve()

    win_a = _parse_float_list(str(args.window_a))
    win_b = _parse_float_list(str(args.window_b))
    if not win_a or not win_b:
        raise SystemExit("Both --window-a and --window-b must be non-empty")

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

    def write_window(batch_dir: Path, window_name: str, dampings: list[float]) -> None:
        paths = _mk_batch(batch_dir)
        q = paths["queue"]

        for i, d in enumerate(dampings, start=1):
            stem = _stem_from_damping(f"rep_{window_name}_{i:02d}", float(d))
            out_prefix = _stem_from_damping(f"repCog_{window_name}", float(d))

            params = dict(common_params)
            params["dampings"] = [float(d)]

            meta = {
                "phase": "COGLOAD",
                "kind": "replication.cognitiveLoad.window",
                "window": window_name,
                "knob": "damping",
                "scenario": str(args.scenario),
                "injectAmount": float(inject_amount),
                "agentCount": int(agent_count),
                "targetsPerPulse": int(targets_per_pulse),
                "pulseEvery": int(pulse_every),
                "dt": float(args.dt),
                "damping": float(d),
                "steps": int(args.steps),
                "pressSliderVal": float(args.press_slider),
                "approxInjectRate": float(approx_rate),
                "budget": int(args.budget),
                "runsPerPoint": int(args.runs_per_point),
            }

            cmd = _make_command(
                dashboard=str(args.dashboard),
                out_prefix=out_prefix,
                runs=int(args.runs_per_point),
                timeout_s=float(args.timeout_s),
                params=params,
                meta=meta,
            )
            _write_json(q / f"{stem}.json", cmd)

        # Execute commands and analyze.
        _run_py(
            run_script,
            [
                "--firefox-dev",
                "--headless",
                "--download-dir",
                str(batch_dir),
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

        _run_py(analyze_script, ["--batch-dir", str(batch_dir), "--download-dir", str(batch_dir)])

        compare_out = batch_dir / "compare"
        compare_args = [
            "--batch-dirs",
            str(batch_dir),
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

    out_root.mkdir(parents=True, exist_ok=True)

    batch_a = out_root / "window_A_1196_spread"
    batch_b = out_root / "window_B_1869_budget"

    write_window(batch_a, "A_1196_spread", win_a)
    write_window(batch_b, "B_1869_budget", win_b)

    print(f"Replication complete. Root: {out_root}")
    print(f"Window A compare: {batch_a / 'compare' / 'cognitive_load_compare.md'}")
    print(f"Window B compare: {batch_b / 'compare' / 'cognitive_load_compare.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
