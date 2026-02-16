from __future__ import annotations

import copy
import importlib.util
import json
import statistics
from pathlib import Path
from typing import Any

from .models import Policy, RunResult, TaskSpec

_HERE = Path(__file__).resolve()
_SOL_ROOT = _HERE.parents[3]
_SOL_CORE_DIR = _SOL_ROOT / "tools" / "sol-core"


def _load_execute_protocol():
    auto_run_path = _SOL_CORE_DIR / "auto_run.py"
    spec = importlib.util.spec_from_file_location("sol_core_auto_run", auto_run_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load auto_run module from {auto_run_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    execute = getattr(module, "execute_protocol", None)
    if execute is None:
        raise ImportError("execute_protocol not found in sol-core auto_run.py")
    return execute


_EXECUTE_PROTOCOL = _load_execute_protocol()


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


class Runner:
    """Executes policy/task evaluations on real SOL protocols."""

    def __init__(self, protocol_root: Path | None = None):
        self.protocol_root = protocol_root or (_SOL_ROOT / "tools" / "sol-core" / "protocols")

    def run_task(self, policy: Policy, task: TaskSpec) -> RunResult:
        protocol_name = str(task.payload.get("protocol", "")).strip()
        if not protocol_name:
            raise ValueError(f"Task {task.task_id} is missing payload.protocol")

        protocol = self._load_protocol(protocol_name)
        protocol = self._apply_policy_to_protocol(protocol, policy, task)
        protocol = self._apply_task_runtime_overrides(protocol, task)
        results = _EXECUTE_PROTOCOL(protocol)

        metrics = self._derive_training_metrics(results, protocol)
        elapsed = float(results.get("summary", {}).get("runtime_sec", 0.0))
        snapshot = self._build_run_snapshot(task, protocol_name, protocol, results, metrics)

        return RunResult(
            policy_id=policy.policy_id,
            task_id=task.task_id,
            metrics=metrics,
            elapsed_sec=elapsed,
            run_snapshot=snapshot,
        )

    def _load_protocol(self, protocol_name: str) -> dict:
        name = protocol_name if protocol_name.endswith(".json") else f"{protocol_name}.json"
        path = self.protocol_root / name
        if not path.exists():
            raise FileNotFoundError(f"Protocol not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _apply_policy_to_protocol(self, protocol: dict, policy: Policy, task: TaskSpec) -> dict:
        updated = copy.deepcopy(protocol)
        invariants = updated.setdefault("invariants", {})
        knobs = updated.setdefault("knobs", {})

        override_map = task.payload.get("policy_overrides", {})

        for key, value in policy.knobs.items():
            target = override_map.get(key)
            if isinstance(target, str) and target.startswith("invariants."):
                invariants[target.split(".", 1)[1]] = value
                continue
            if isinstance(target, str) and target.startswith("knobs."):
                knobs[target.split(".", 1)[1]] = [value]
                continue

            if key in knobs:
                knobs[key] = [value]
            else:
                invariants[key] = value

        return updated

    def _apply_task_runtime_overrides(self, protocol: dict, task: TaskSpec) -> dict:
        updated = copy.deepcopy(protocol)
        runtime_overrides = task.payload.get("runtime_overrides", {})

        for key in ("steps", "reps", "metrics_every", "baseline"):
            if key in runtime_overrides:
                updated[key] = runtime_overrides[key]

        protocol_overrides = task.payload.get("protocol_overrides", {})
        for key, value in protocol_overrides.items():
            if key.startswith("invariants."):
                inv_key = key.split(".", 1)[1]
                updated.setdefault("invariants", {})[inv_key] = value
            elif key.startswith("knobs."):
                knob_key = key.split(".", 1)[1]
                if isinstance(value, list):
                    updated.setdefault("knobs", {})[knob_key] = value
                else:
                    updated.setdefault("knobs", {})[knob_key] = [value]
            else:
                updated[key] = value

        return updated

    def _build_run_snapshot(
        self,
        task: TaskSpec,
        protocol_name: str,
        protocol: dict,
        results: dict,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        return {
            "task_id": task.task_id,
            "family": task.family,
            "anchor": task.anchor,
            "protocol_name": protocol_name,
            "effective_protocol": {
                "seriesName": protocol.get("seriesName"),
                "invariants": protocol.get("invariants", {}),
                "knobs": protocol.get("knobs", {}),
                "steps": protocol.get("steps"),
                "reps": protocol.get("reps"),
                "metrics_every": protocol.get("metrics_every"),
                "baseline": protocol.get("baseline"),
                "injections": protocol.get("injections", []),
            },
            "summary": results.get("summary", {}),
            "sanity": results.get("sanity", {}),
            "comparison": results.get("comparison"),
            "conditions": results.get("conditions", {}),
            "derived_metrics": metrics,
        }

    def _derive_training_metrics(self, results: dict, protocol: dict) -> dict[str, float]:
        conditions = results.get("conditions", {})
        if not conditions:
            return {
                "stability": 0.0,
                "novelty": 0.0,
                "usefulness": 0.0,
                "reproducibility": 0.0,
                "cost": 10.0,
            }

        final_entropy_vals: list[float] = []
        final_flux_vals: list[float] = []
        final_mass_vals: list[float] = []
        entropy_ranges: list[float] = []
        entropy_stdevs: list[float] = []
        convergence_vals: list[float] = []

        for cond in conditions.values():
            final_m = cond.get("final_metrics", {})
            analysis = cond.get("analysis", {})

            final_entropy_vals.append(float(final_m.get("entropy", 0.0)))
            final_flux_vals.append(float(final_m.get("totalFlux", 0.0)))
            final_mass_vals.append(float(final_m.get("mass", 0.0)))

            entropy_info = analysis.get("entropy", {})
            entropy_ranges.append(float(entropy_info.get("range", 0.0)))
            entropy_stdevs.append(float(entropy_info.get("stdev", 0.0)))

            conv = analysis.get("convergence_entropy")
            if isinstance(conv, (int, float)):
                convergence_vals.append(float(conv))

        mean_entropy_range = statistics.mean(entropy_ranges) if entropy_ranges else 0.0
        mean_entropy_stdev = statistics.mean(entropy_stdevs) if entropy_stdevs else 0.0
        mean_convergence = statistics.mean(convergence_vals) if convergence_vals else 0.0
        mean_final_flux = statistics.mean(final_flux_vals) if final_flux_vals else 0.0
        mean_final_mass = statistics.mean(final_mass_vals) if final_mass_vals else 0.0

        sanity = results.get("sanity", {})
        sanity_score = 1.0 if sanity.get("all_passed", False) else 0.0

        injections = protocol.get("injections", [])
        injected_total = float(sum(float(i.get("amount", 0.0)) for i in injections))
        mass_retention = (mean_final_mass / injected_total) if injected_total > 0 else 0.0
        mass_retention = _clamp_01(mass_retention)

        reproducibility = _clamp_01(1.0 / (1.0 + 10.0 * mean_entropy_stdev))
        stability = _clamp_01(
            0.45 * reproducibility
            + 0.30 * (1.0 - _clamp_01(mean_entropy_range))
            + 0.25 * sanity_score
        )

        if len(final_entropy_vals) > 1:
            entropy_div = statistics.pstdev(final_entropy_vals)
            novelty = _clamp_01(min(1.0, entropy_div * 3.0) + 0.20 * _clamp_01(mean_entropy_range))
        else:
            novelty = _clamp_01(mean_entropy_range)

        flux_term = _clamp_01(mean_final_flux / 10.0)
        usefulness = _clamp_01(0.60 * mass_retention + 0.20 * flux_term + 0.20 * sanity_score)

        runtime_sec = float(results.get("summary", {}).get("runtime_sec", 0.0))
        total_steps = float(results.get("summary", {}).get("total_steps", 1.0))
        step_scale = max(1.0, total_steps / 1000.0)
        cost = runtime_sec / step_scale
        if not sanity.get("all_passed", False):
            cost += 0.25

        return {
            "stability": stability,
            "novelty": novelty,
            "usefulness": usefulness,
            "reproducibility": reproducibility,
            "cost": max(0.0, cost),
        }
