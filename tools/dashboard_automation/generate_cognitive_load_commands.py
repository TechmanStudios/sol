"""Generate a staged batch of commands to probe "cognitive load → infinity".

This writes a folder containing:
- command_queue/*.json  (inputs to run_dashboard_sweep.py)
- command_done/         (populated by runner)
- command_results/      (populated by runner)
- cognitive_load_manifest_<stamp>.json

The intent is to sweep a single knob upward (default: injectAmount) while
keeping the rest fixed, so we can detect thresholds, runaway regimes, and
afterstate lock-in.

Typical workflow:
1) Generate a batch folder
2) Run it with one Firefox session:
   python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev \
     --run-command-dir <batch>/command_queue \
     --command-done-dir <batch>/command_done \
     --command-results-dir <batch>/command_results
3) Analyze:
   python tools/dashboard_automation/analyze_cognitive_load_sweep.py --batch-dir <batch>
"""

from __future__ import annotations

import argparse
import json
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


def _geom_series(start: float, factor: float, max_value: float, max_terms: int) -> list[float]:
    if start <= 0:
        raise ValueError("start must be > 0")
    if factor <= 1:
        raise ValueError("factor must be > 1")
    if max_value < start:
        return [start]

    xs: list[float] = []
    x = float(start)
    for _ in range(max_terms):
        xs.append(x)
        if x >= max_value:
            break
        x *= factor
    return xs


def _geom_series_down(start: float, factor: float, min_value: float, max_terms: int) -> list[int]:
    """Geometric series decreasing toward min_value.

    Example: start=64, factor=0.5, min_value=1 -> 64,32,16,...,1
    """
    if start < 1:
        raise ValueError("start must be >= 1")
    if not (0 < factor < 1):
        raise ValueError("factor must be between 0 and 1")
    if min_value < 1:
        raise ValueError("min_value must be >= 1")

    xs: list[int] = []
    x = float(start)
    for _ in range(max_terms):
        xi = int(round(x))
        xi = max(int(min_value), xi)
        if xs and xi == xs[-1]:
            break
        xs.append(xi)
        if xi <= min_value:
            break
        x *= factor
    return xs


@dataclass(frozen=True)
class BatchPaths:
    root: Path
    queue: Path
    done: Path
    results: Path
    manifest: Path


def _resolve_batch_paths(sol_root: Path, enqueue: bool) -> BatchPaths:
    test_results = sol_root / "solData" / "testResults"
    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"

    if enqueue:
        root = test_results
        queue = root / "command_queue"
        done = root / "command_done"
        results = root / "command_results"
        manifest = root / f"cognitive_load_manifest_{stamp}.json"
        return BatchPaths(root=root, queue=queue, done=done, results=results, manifest=manifest)

    root = test_results / "cognitive_load_batches" / stamp
    # Extremely defensive: if two calls land in the same millisecond, suffix.
    if root.exists():
        for i in range(1, 100):
            candidate = test_results / "cognitive_load_batches" / f"{stamp}_{i:02d}"
            if not candidate.exists():
                root = candidate
                break
    queue = root / "command_queue"
    done = root / "command_done"
    results = root / "command_results"
    manifest = root / f"cognitive_load_manifest_{stamp}.json"
    return BatchPaths(root=root, queue=queue, done=done, results=results, manifest=manifest)


def _make_command(
    *,
    dashboard: str,
    out_prefix: str,
    params: dict[str, Any],
    meta: dict[str, Any],
    runs: int,
    timeout_s: float,
) -> dict[str, Any]:
    return {
        "kind": "sol.dashboard.sweep.v1",
        "dashboard": dashboard,
        "outPrefix": out_prefix,
        "runs": runs,
        "timeoutS": timeout_s,
        "params": params,
        "meta": meta,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dashboard",
        default="sol_dashboard_v3_7_2.html",
        help="Dashboard HTML under sol/.",
    )
    ap.add_argument(
        "--enqueue",
        action="store_true",
        help="Write directly into solData/testResults/command_queue (runs if watcher is active).",
    )

    # Core sweep definition
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--dt", type=float, default=0.12)
    ap.add_argument("--damping", type=float, default=4.0)
    ap.add_argument("--mode", default="multiAgentTrain")
    ap.add_argument("--press-slider", type=float, default=200)
    ap.add_argument("--target-id", type=int, default=64)
    ap.add_argument("--probe-ids", default="64,82,79", help="Comma-separated node ids to record in telemetry.")

    # Multi-agent injection params (models many concurrent writers)
    ap.add_argument(
        "--scenario",
        default="distributed",
        choices=["distributed", "concentrated", "roaming", "burstAll"],
        help=(
            "How to map 'agents' onto injection targets. "
            "distributed: multiple targets, up to targetsPerPulse each pulse. "
            "concentrated: all writes go to --target-id only. "
            "roaming: one write per pulse, cycling through --agent-target-ids. "
            "burstAll: all agents write each pulse (targetsPerPulse = agentCount)."
        ),
    )
    ap.add_argument(
        "--agent-target-ids",
        default="64,82,79",
        help=(
            "Comma-separated node ids used as injection targets. "
            "agentCount selects a prefix of this list."
        ),
    )
    ap.add_argument("--agent-count", type=int, default=3)
    ap.add_argument("--targets-per-pulse", type=int, default=3, help="How many agents inject per pulse step.")
    ap.add_argument("--pulse-step", type=int, default=100, help="First pulse step.")
    ap.add_argument("--pulse-every", type=int, default=10, help="Pulse period in steps (smaller => higher load).")
    ap.add_argument("--pulse-count", type=int, default=0, help="Max number of pulses (0 => until steps).")

    # Cognitive-load scaling knob
    ap.add_argument(
        "--load-knob",
        default="injectAmount",
        choices=["injectAmount", "agentCount", "pulseEvery", "damping"],
        help=(
            "Which parameter to scale. "
            "injectAmount increases per-agent pulse magnitude. "
            "agentCount increases how many agent targets participate. "
            "pulseEvery decreases pulse period (higher frequency => higher load). "
            "damping sweeps dissipation/resonance (stability/compute tradeoff)."
        ),
    )
    ap.add_argument("--inject-start", type=float, default=1.0)
    ap.add_argument("--inject-factor", type=float, default=2.0)
    ap.add_argument("--inject-max", type=float, default=2048.0)
    ap.add_argument("--agent-start", type=int, default=1)
    ap.add_argument("--agent-factor", type=float, default=2.0)
    ap.add_argument("--agent-max", type=int, default=16)
    ap.add_argument("--pulse-every-start", type=int, default=64)
    ap.add_argument("--pulse-every-factor", type=float, default=0.5)
    ap.add_argument("--pulse-every-min", type=int, default=1)
    ap.add_argument("--max-terms", type=int, default=12, help="Safety cap on number of sweep points.")

    # Damping sweep (only used when --load-knob damping)
    ap.add_argument(
        "--damping-sweep-start",
        type=float,
        default=None,
        help="Start damping for sweep (defaults to --damping).",
    )
    ap.add_argument("--damping-sweep-factor", type=float, default=2.0)
    ap.add_argument("--damping-sweep-max", type=float, default=16.0)

    ap.add_argument(
        "--out-prefix",
        default="cogLoad",
        help="Base outPrefix used for CSV filenames.",
    )
    ap.add_argument(
        "--timeout-s",
        type=float,
        default=900.0,
        help="Timeout per command.",
    )
    ap.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of sweeps per command JSON (usually 1).",
    )

    args = ap.parse_args()

    sol_root = Path(__file__).resolve().parents[2]
    paths = _resolve_batch_paths(sol_root, enqueue=bool(args.enqueue))

    # Ensure folders exist for staged mode (runner will populate done/results).
    paths.queue.mkdir(parents=True, exist_ok=True)
    paths.done.mkdir(parents=True, exist_ok=True)
    paths.results.mkdir(parents=True, exist_ok=True)

    probe_ids = _parse_int_list(args.probe_ids)
    scenario = str(args.scenario)

    agent_targets_all = _parse_int_list(args.agent_target_ids)
    if scenario != "concentrated":
        if not agent_targets_all:
            raise SystemExit("--agent-target-ids must contain at least one id")
    else:
        # Concentrated mode ignores --agent-target-ids.
        agent_targets_all = [int(args.target_id)]

    base_agent_count = int(args.agent_count)
    if scenario == "concentrated":
        # One effective writer target in concentrated mode.
        base_agent_count = 1
    if base_agent_count < 1:
        raise SystemExit("--agent-count must be >= 1")
    if base_agent_count > len(agent_targets_all):
        raise SystemExit(
            f"--agent-count={base_agent_count} exceeds --agent-target-ids length ({len(agent_targets_all)}). "
            "Provide more ids in --agent-target-ids."
        )

    base_targets_per_pulse = int(args.targets_per_pulse)
    if base_targets_per_pulse < 1:
        raise SystemExit("--targets-per-pulse must be >= 1")

    # Determine sweep values for the chosen knob.
    knob = str(args.load_knob)
    inject_values = _geom_series(args.inject_start, args.inject_factor, args.inject_max, args.max_terms)
    agent_values = _geom_series(float(args.agent_start), float(args.agent_factor), float(args.agent_max), args.max_terms)
    agent_values_int = [max(1, int(round(x))) for x in agent_values]
    pulse_every_values = _geom_series_down(args.pulse_every_start, args.pulse_every_factor, args.pulse_every_min, args.max_terms)

    damping_start = float(args.damping) if args.damping_sweep_start is None else float(args.damping_sweep_start)
    damping_values = _geom_series(damping_start, float(args.damping_sweep_factor), float(args.damping_sweep_max), args.max_terms)

    if knob == "injectAmount":
        sweep_values: list[Any] = inject_values
    elif knob == "agentCount":
        sweep_values = agent_values_int
    elif knob == "pulseEvery":
        sweep_values = pulse_every_values
    elif knob == "damping":
        sweep_values = damping_values
    else:
        raise SystemExit(f"Unsupported --load-knob: {args.load_knob}")

    commands: list[dict[str, Any]] = []
    for i, v in enumerate(sweep_values, start=1):
        inject_amount = float(args.inject_start)
        agent_count = base_agent_count
        pulse_every = int(args.pulse_every)
        damping = float(args.damping)

        if knob == "injectAmount":
            inject_amount = float(v)
            label = f"inj{inject_amount:g}".replace(".", "p")
        elif knob == "agentCount":
            agent_count = int(v)
            label = f"agents{agent_count}".replace(".", "p")
        elif knob == "pulseEvery":
            pulse_every = int(v)
            label = f"every{pulse_every}".replace(".", "p")
        elif knob == "damping":
            damping = float(v)
            label = f"damp{damping:g}".replace(".", "p")
        else:
            label = f"v{i}".replace(".", "p")

        if agent_count > len(agent_targets_all):
            raise SystemExit(
                f"Sweep value agentCount={agent_count} exceeds --agent-target-ids length ({len(agent_targets_all)})."
            )

        agent_targets = agent_targets_all[:agent_count]
        if scenario == "concentrated":
            agent_targets = [int(args.target_id)]
            agent_count = 1
            targets_per_pulse = 1
        elif scenario == "roaming":
            targets_per_pulse = 1
        elif scenario == "burstAll":
            targets_per_pulse = agent_count
        else:
            targets_per_pulse = min(base_targets_per_pulse, agent_count)

        approx_inject_rate = float(inject_amount) * float(targets_per_pulse) / max(1.0, float(pulse_every))

        out_prefix = f"{args.out_prefix}_{label}"  # becomes <outPrefix>_summary_*.csv

        params: dict[str, Any] = {
            "steps": int(args.steps),
            "dts": [float(args.dt)],
            "dampings": [float(damping)],
            "modes": [str(args.mode)],
            "pressSliderVal": float(args.press_slider),
            "injectAmount": float(inject_amount),
            "targetId": int(args.target_id),
            "targetIds": agent_targets,
            "targetsPerPulse": int(targets_per_pulse),
            "pulseStep": int(args.pulse_step),
            "pulseEvery": int(pulse_every),
            "pulseCount": int(args.pulse_count),
            "probeIds": probe_ids,
            # Keep tracing moderate (analysis will use traceRows peaks).
            "traceEvery": 50,
            "progressEvery": 250,
            "adaptiveTrace": True,
            "guardrail": {"type": "none"},
        }

        meta = {
            "phase": "COGLOAD",
            "scenario": scenario,
            "knob": args.load_knob,
            "dt": float(args.dt),
            "damping": float(damping),
            "steps": int(args.steps),
            "pressSliderVal": float(args.press_slider),
            "injectAmount": float(inject_amount),
            "agentCount": int(agent_count),
            "targetsPerPulse": int(targets_per_pulse),
            "pulseEvery": int(pulse_every),
            "pulseStep": int(args.pulse_step),
            "pulseCount": int(args.pulse_count),
            "approxInjectRate": approx_inject_rate,
            "pointIndex": i,
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        cmd = _make_command(
            dashboard=str(args.dashboard),
            out_prefix=out_prefix,
            params=params,
            meta=meta,
            runs=int(args.runs),
            timeout_s=float(args.timeout_s),
        )
        commands.append(cmd)

        stem = f"cogload_{i:03d}_{label}"
        _write_json(paths.queue / f"{stem}.json", cmd)

    _write_json(
        paths.manifest,
        {
            "kind": "sol.cognitive_load.batch.v1",
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "dashboard": str(args.dashboard),
            "queueDir": str(paths.queue),
            "count": len(commands),
            "paramsTemplate": {
                "steps": int(args.steps),
                "dt": float(args.dt),
                "damping": float(args.damping),
                "dampingSweepStart": float(damping_start),
                "dampingSweepFactor": float(args.damping_sweep_factor),
                "dampingSweepMax": float(args.damping_sweep_max),
                "mode": str(args.mode),
                "pressSliderVal": float(args.press_slider),
                "targetId": int(args.target_id),
                "scenario": scenario,
                "agentTargetIds": agent_targets_all,
                "agentCount": int(base_agent_count),
                "targetsPerPulse": int(base_targets_per_pulse),
                "pulseStep": int(args.pulse_step),
                "pulseEvery": int(args.pulse_every),
                "pulseCount": int(args.pulse_count),
                "probeIds": probe_ids,
                "loadKnob": args.load_knob,
                "injectStart": float(args.inject_start),
                "injectFactor": float(args.inject_factor),
                "injectMax": float(args.inject_max),
                "agentStart": int(args.agent_start),
                "agentFactor": float(args.agent_factor),
                "agentMax": int(args.agent_max),
                "pulseEveryStart": int(args.pulse_every_start),
                "pulseEveryFactor": float(args.pulse_every_factor),
                "pulseEveryMin": int(args.pulse_every_min),
            },
            "commands": [
                {
                    "outPrefix": c.get("outPrefix"),
                    "meta": c.get("meta"),
                }
                for c in commands
            ],
        },
    )

    print(f"Wrote {len(commands)} command(s) into: {paths.queue}")
    if not args.enqueue:
        print("\nRun this batch with one browser session:")
        print(
            "python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev "
            f"--run-command-dir \"{paths.queue}\" "
            f"--command-done-dir \"{paths.done}\" "
            f"--command-results-dir \"{paths.results}\""
        )
        print("\nThen analyze:")
        print(f"python tools/dashboard_automation/analyze_cognitive_load_sweep.py --batch-dir \"{paths.root}\"")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
