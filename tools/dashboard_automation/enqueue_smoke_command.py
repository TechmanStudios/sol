"""Enqueue a tiny UI-neutral smoke command for run_dashboard_sweep.py.

This validates that the dashboard can boot under automation mode and that
SOLDashboard.state.physics is present and can execute step() a few times.

Example:
  python tools/dashboard_automation/enqueue_smoke_command.py --name smoke_001

Run (headless):
  python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --headless \
    --command-file solData\\testResults\\command_queue\\smoke_001.json

Notes:
- run_dashboard_sweep.py loads the dashboard with ?automation=1; visualization is disabled.
- This smoke command produces no downloads; results are written into command_results/*.json
  by run_dashboard_sweep.py.
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
        "--name",
        default="",
        help="Optional command file base name (otherwise timestamped).",
    )
    ap.add_argument(
        "--runs",
        type=int,
        default=1,
        help="How many times to repeat the smoke in one command.",
    )
    ap.add_argument(
        "--steps",
        type=int,
        default=3,
        help="How many physics.step() calls to attempt.",
    )
    ap.add_argument(
        "--dt",
        type=float,
        default=0.12,
        help="dt passed into physics.step(dt, pressureC, damping) when supported.",
    )
    ap.add_argument(
        "--pressure-c",
        type=float,
        default=20.0,
        help="Pressure coefficient passed into physics.step(dt, pressureC, damping) when supported.",
    )
    ap.add_argument(
        "--damping",
        type=float,
        default=4.0,
        help="Damping passed into physics.step(dt, pressureC, damping) when supported.",
    )
    ap.add_argument(
        "--dashboard-config-json",
        default="{}",
        help=(
            "Optional JSON object merged into SOLDashboard.config before the smoke runs. "
            'Example: {"capLaw":{"enabled":false}}'
        ),
    )
    ap.add_argument(
        "--timeout-s",
        type=float,
        default=60.0,
        help="Timeout for the command (runner-enforced).",
    )

    args = ap.parse_args()

    dashboard_cfg = json.loads(args.dashboard_config_json)
    if not isinstance(dashboard_cfg, dict):
        raise SystemExit("--dashboard-config-json must be a JSON object")

    base = Path(args.download_dir).resolve()
    q = base / "command_queue"

    stamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = str(args.name or "").strip() or f"cmd_smoke_{stamp}"
    path = q / f"{base_name}.json"

    payload: dict[str, Any] = {
        "kind": "sol.dashboard.smoke.v1",
        "dashboard": str(args.dashboard),
        "runs": int(args.runs),
        "timeoutS": float(args.timeout_s),
        "smoke": {
            "steps": int(args.steps),
            "dt": float(args.dt),
            "pressureC": float(args.pressure_c),
            "damping": float(args.damping),
        },
    }

    if dashboard_cfg:
        payload["dashboardConfig"] = dashboard_cfg

    _write_json(path, payload)
    print(f"Enqueued: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
