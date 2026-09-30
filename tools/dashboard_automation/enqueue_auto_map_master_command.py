"""Enqueue SOL Auto Mapper *master* commands for run_dashboard_sweep.py.

This writes a command JSON into solData/testResults/command_queue/.
The runner will inject sol_auto_mapper_pack.js and execute:
  window.solAutoMap.runMaster(masterPlan)

Example:
  python tools/dashboard_automation/enqueue_auto_map_master_command.py \
    --master-plan-json "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\templates\\master_mapping_plan.v2.json" \
    --pack-path "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\scripts\\sol_auto_mapper_pack.js" \
    --name autoMap_master_v2_overnight

Then run headless one-shot:
  python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --headless \
    --command-file "solData\\testResults\\command_queue\\autoMap_master_v2_overnight.json"
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


def _read_json_obj(path: Path, *, label: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{label} must be a JSON object: {path}")
    return data


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
        "--master-plan-json",
        type=Path,
        required=True,
        help="Path to a solAutoMap master plan JSON object (passed into solAutoMap.runMaster(masterPlan)).",
    )
    ap.add_argument(
        "--pack-path",
        default="",
        help=(
            "Optional path to sol_auto_mapper_pack.js. If omitted, you must pass --auto-map-pack to the runner. "
            "If provided, it is written into the command JSON as packPath."
        ),
    )
    ap.add_argument(
        "--dashboard-config-json",
        default="{}",
        help=(
            "Optional JSON object merged into SOLDashboard.config before the master plan runs. "
            "Example: {\"capLaw\":{\"enabled\":false}}"
        ),
    )
    ap.add_argument(
        "--timeout-s",
        type=float,
        default=60 * 60 * 7,
        help="Timeout for the master plan run + downloads (seconds). Default: 7 hours.",
    )
    ap.add_argument(
        "--name",
        default="",
        help="Optional command file base name (otherwise timestamped).",
    )

    args = ap.parse_args()

    plan_path = Path(args.master_plan_json).resolve()
    if not plan_path.exists():
        raise SystemExit(f"--master-plan-json not found: {plan_path}")
    master_plan = _read_json_obj(plan_path, label="--master-plan-json")

    dashboard_cfg = json.loads(args.dashboard_config_json)
    if not isinstance(dashboard_cfg, dict):
        raise SystemExit("--dashboard-config-json must be a JSON object")

    base = Path(args.download_dir).resolve()
    q = base / "command_queue"

    stamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = args.name.strip() or f"cmd_autoMapMaster_{stamp}"
    path = q / f"{base_name}.json"

    payload: dict[str, Any] = {
        "kind": "sol.dashboard.auto_map_master.v1",
        "dashboard": args.dashboard,
        "runs": 1,
        "timeoutS": float(args.timeout_s),
        "masterPlan": master_plan,
    }

    pack_path = str(args.pack_path or "").strip()
    if pack_path:
        payload["packPath"] = pack_path

    if dashboard_cfg:
        payload["dashboardConfig"] = dashboard_cfg

    _write_json(path, payload)
    print(f"Enqueued: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
