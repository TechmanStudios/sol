"""Enqueue SOL Auto Mapper commands for run_dashboard_sweep.py.

This mirrors enqueue_command.py but targets solAutoMap.runPlan(plan) instead of
solMechanismTraceSweepV1.

Example (smoke):
  python tools/dashboard_automation/enqueue_auto_map_command.py \
    --plan-json "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\templates\\smoke_mapping_plan.example.json" \
    --pack-path "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\scripts\\sol_auto_mapper_pack.js" \
    --name autoMap_smoke_001

Then run (headless, command-file one-shot):
  python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --headless \
    --auto-map-pack "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\scripts\\sol_auto_mapper_pack.js" \
    --command-file "solData\\testResults\\command_queue\\autoMap_smoke_001.json"
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


def _is_plain_object(x: Any) -> bool:
    return isinstance(x, dict)


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
    for k, v in source.items():
        if _is_plain_object(v) and _is_plain_object(target.get(k)):
            _deep_merge(target[k], v)  # type: ignore[index]
        else:
            target[k] = v


def _preset_plan(name: str) -> dict[str, Any]:
    preset = name.strip().lower()
    if preset != "smoke":
        raise SystemExit(f"Unsupported --preset: {name}")

    # Mirrors aiAgents/.github/skills/sol-auto-mapper/templates/smoke_mapping_plan.example.json
    return {
        "planName": "smoke_plan_v1",
        "notes": (
            "Tiny smoke plan: one basin, one grid point, short duration. "
            "Intended to validate wiring + downloads + organizer + candidate creation."
        ),
        "basins": [90],
        "replicates": 1,
        "engine": {"strictStepParams": True},
        "scenario": {
            "type": "inject_then_watch",
            "injectAmount": 30,
            "preSteps": 1,
            "preDt": 0.12,
        },
        "measurement": {
            "durationMs": 3000,
            "everyMs": 250,
            "dt": 0.12,
            "includeBackgroundEdges": False,
        },
        "grid": {"pressureC": [20], "damping": [8]},
        "timing": {"timingMode": "tight", "spinWaitMs": 2.0},
    }


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
        "--plan-json",
        type=Path,
        default=None,
        help=(
            "Path to a solAutoMap plan JSON object (passed into solAutoMap.runPlan(plan)). "
            "Optional if --preset is used."
        ),
    )
    ap.add_argument(
        "--preset",
        default="",
        help=(
            "Optional preset plan. Supported: smoke. "
            "Preset values are applied first, then overridden by --plan-json and --plan-overrides-json."
        ),
    )
    ap.add_argument(
        "--plan-overrides-json",
        default="{}",
        help=(
            "Optional JSON object deep-merged into the plan after preset/plan-json. "
            'Example: {"grid":{"damping":[4,8,12]}}'
        ),
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
            "Optional JSON object merged into SOLDashboard.config before the plan runs. "
            "Example: {\"capLaw\":{\"enabled\":false}}"
        ),
    )
    ap.add_argument(
        "--timeout-s",
        type=float,
        default=300.0,
        help="Timeout for the plan run + downloads.",
    )
    ap.add_argument(
        "--name",
        default="",
        help="Optional command file base name (otherwise timestamped).",
    )

    args = ap.parse_args()

    plan: dict[str, Any] = {}
    preset = str(args.preset or "").strip()
    if preset:
        plan = _preset_plan(preset)

    if args.plan_json is not None:
        plan_path = Path(args.plan_json).resolve()
        if not plan_path.exists():
            raise SystemExit(f"--plan-json not found: {plan_path}")
        loaded = _read_json_obj(plan_path, label="--plan-json")
        _deep_merge(plan, loaded)

    if not plan:
        raise SystemExit("Provide --plan-json or --preset")

    plan_overrides = json.loads(args.plan_overrides_json)
    if not isinstance(plan_overrides, dict):
        raise SystemExit("--plan-overrides-json must be a JSON object")
    if plan_overrides:
        _deep_merge(plan, plan_overrides)

    dashboard_cfg = json.loads(args.dashboard_config_json)
    if not isinstance(dashboard_cfg, dict):
        raise SystemExit("--dashboard-config-json must be a JSON object")

    base = Path(args.download_dir).resolve()
    q = base / "command_queue"

    stamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = args.name.strip() or f"cmd_autoMap_{stamp}"
    path = q / f"{base_name}.json"

    payload: dict[str, Any] = {
        "kind": "sol.dashboard.auto_map.v1",
        "dashboard": args.dashboard,
        "runs": 1,
        "timeoutS": float(args.timeout_s),
        "plan": plan,
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
