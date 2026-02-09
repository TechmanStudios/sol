"""Enqueue SOL dashboard sweep commands for run_dashboard_sweep.py.

This is a convenience tool to drop a command JSON into the command queue.
It is designed so an agent (or you) can create repeatable experiment runs
without typing inside the runner process.

Example:
  python tools/dashboard_automation/enqueue_command.py --runs 3 --out-prefix sol_mechSweep --params-json "{\"steps\":2000}"

Then, in another terminal/process, run:
  python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --watch-commands
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--download-dir",
        default=str(Path(__file__).resolve().parents[2] / "solData" / "testResults"),
        help="Base folder used by the runner (default: solData/testResults).",
    )
    ap.add_argument(
        "--dashboard",
        default="sol_dashboard_v3_7_2.html",
        help="Dashboard HTML file to load.",
    )
    ap.add_argument(
        "--out-prefix",
        default="sol_mechSweep",
        help="CSV filename prefix.",
    )
    ap.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of sweeps to execute for this command.",
    )
    ap.add_argument(
        "--params-json",
        default="{}",
        help="JSON object passed as params to solMechanismTraceSweepV1.run().",
    )
    ap.add_argument(
        "--dashboard-config-json",
        default="{}",
        help=(
            "Optional JSON object merged into SOLDashboard.config before the sweep runs. "
            "Example: {\"capLaw\":{\"enabled\":false}}"
        ),
    )
    ap.add_argument(
        "--preset",
        default="",
        help=(
            "Optional preset params. Supported: smoke. "
            "Preset values are applied first, then overridden by --params-json."
        ),
    )
    ap.add_argument(
        "--timeout-s",
        type=float,
        default=600.0,
        help="Timeout for a single sweep + downloads.",
    )
    ap.add_argument(
        "--name",
        default="",
        help="Optional command file base name (otherwise timestamped).",
    )

    args = ap.parse_args()

    params_overrides = json.loads(args.params_json)
    if not isinstance(params_overrides, dict):
        raise SystemExit("--params-json must be a JSON object")

    dashboard_cfg = json.loads(args.dashboard_config_json)
    if not isinstance(dashboard_cfg, dict):
        raise SystemExit("--dashboard-config-json must be a JSON object")

    preset = str(args.preset or "").strip().lower()
    params: dict[str, Any] = {}
    if preset:
        if preset != "smoke":
            raise SystemExit(f"Unsupported --preset: {args.preset}")

        # Tiny, fast end-to-end run. Intended to validate:
        # - baseline restore works
        # - JS harness runs
        # - 2 CSVs download into solData/testResults/
        params = {
            "steps": 800,
            "dts": [0.12],
            "dampings": [4],
            "modes": ["pulse100"],
            "pressSliderVal": 200,
            "injectAmount": 10,
            "traceEvery": 100,
            "progressEvery": 400,
            "adaptiveTrace": False,
            "targetId": 64,
            "probeIds": [64, 82, 79],
            "guardrail": {"type": "none"},
        }

    params.update(params_overrides)

    base = Path(args.download_dir).resolve()
    q = base / "command_queue"

    stamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = args.name.strip() or f"cmd_{stamp}"
    path = q / f"{base_name}.json"

    payload: dict[str, Any] = {
        "kind": "sol.dashboard.sweep.v1",
        "dashboard": args.dashboard,
        "outPrefix": args.out_prefix,
        "runs": int(args.runs),
        "timeoutS": float(args.timeout_s),
        "params": params,
    }

    if dashboard_cfg:
        payload["dashboardConfig"] = dashboard_cfg

    _write_json(path, payload)
    print(f"Enqueued: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
