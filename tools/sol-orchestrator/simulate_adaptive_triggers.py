#!/usr/bin/env python3
"""
Phase 1.4 — Adaptive Trigger Simulation Harness

Deterministically simulates trigger conditions to validate policy branches
without waiting for organic runtime failures.

Scenarios:
  - cortex_sanity_fail: synthetic sanity failures trigger cortex retry/adoption
  - cortex_velocity_drop: zero protocol throughput triggers cortex retry/adoption
  - consolidate_recovery: consolidate failure triggers non-cortex retry/adoption
    - hippocampus_recovery: hippocampus failure triggers non-cortex retry/adoption
    - evolve_recovery: evolve failure triggers non-cortex retry/adoption
"""
from __future__ import annotations

import argparse
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import orchestrator as orch


@contextmanager
def _patched(module, replacements: dict[str, Any]):
    original: dict[str, Any] = {}
    for name, value in replacements.items():
        original[name] = getattr(module, name)
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in original.items():
            setattr(module, name, value)


def _base_paths(tmp_root: Path) -> dict[str, Any]:
    return {
        "_PIPELINE_DIR": tmp_root / "pipeline_runs",
        "_DELEGATION_LEDGER": tmp_root / "pipeline_runs" / "_delegation_trust_ledger.json",
        "verify_core_immutability": lambda: True,
        "stage_smoke": lambda cfg: {
            "engine_ok": True,
            "nodes": 140,
            "mass": 1.0,
            "entropy": 0.1,
            "maxRho": 1.0,
            "core_sha256": "simulated",
        },
    }


def run_cortex_sanity_fail_scenario() -> dict[str, Any]:
    calls = {"cortex": 0}

    def fake_cortex(cfg):
        calls["cortex"] += 1
        if calls["cortex"] == 1:
            return {
                "session_id": "SIM-CX-1",
                "session_dir": "sim://cx1",
                "protocols_run": 1,
                "total_steps": 100,
                "hypotheses": 1,
                "gaps_addressed": ["gap-a"],
                "sanity_results": [
                    {
                        "hypothesis": "H-001",
                        "series": "sim-series",
                        "sanity_passed": False,
                        "anomalies": ["simulated anomaly"],
                    }
                ],
                "dry_run": False,
            }
        return {
            "session_id": "SIM-CX-2",
            "session_dir": "sim://cx2",
            "protocols_run": 3,
            "total_steps": 300,
            "hypotheses": 2,
            "gaps_addressed": ["gap-a", "gap-b"],
            "sanity_results": [
                {
                    "hypothesis": "H-002",
                    "series": "sim-series-2",
                    "sanity_passed": True,
                    "anomalies": [],
                }
            ],
            "dry_run": False,
        }

    with tempfile.TemporaryDirectory(prefix="sol-adaptive-sim-") as tmp:
        tmp_root = Path(tmp)
        patch = _base_paths(tmp_root)
        patch["stage_cortex"] = fake_cortex
        with _patched(orch, patch):
            runner = orch.PipelineRunner(
                orch.PipelineConfig(stages=["smoke", "cortex", "report"], verbose=False)
            )
            summary = runner.run()

            stage = runner.results["cortex"]
            adaptive = stage.output.get("adaptive_response", {})
            assert adaptive.get("adopted") is True
            assert adaptive.get("triggered_by") == "sanity_fail"
            assert summary["delegation_v1"]["adaptive_actions"] >= 1
            return {
                "scenario": "cortex_sanity_fail",
                "passed": True,
                "adaptive": adaptive,
            }


def run_cortex_velocity_drop_scenario() -> dict[str, Any]:
    calls = {"cortex": 0}

    def fake_cortex(cfg):
        calls["cortex"] += 1
        if calls["cortex"] == 1:
            return {
                "session_id": "SIM-CX-V1",
                "session_dir": "sim://cxv1",
                "protocols_run": 0,
                "total_steps": 0,
                "hypotheses": 1,
                "gaps_addressed": ["gap-v"],
                "sanity_results": [],
                "dry_run": False,
            }
        return {
            "session_id": "SIM-CX-V2",
            "session_dir": "sim://cxv2",
            "protocols_run": 2,
            "total_steps": 200,
            "hypotheses": 2,
            "gaps_addressed": ["gap-v", "gap-v2"],
            "sanity_results": [],
            "dry_run": False,
        }

    with tempfile.TemporaryDirectory(prefix="sol-adaptive-sim-") as tmp:
        tmp_root = Path(tmp)
        patch = _base_paths(tmp_root)
        patch["stage_cortex"] = fake_cortex
        with _patched(orch, patch):
            runner = orch.PipelineRunner(
                orch.PipelineConfig(stages=["smoke", "cortex", "report"], verbose=False)
            )
            summary = runner.run()

            stage = runner.results["cortex"]
            adaptive = stage.output.get("adaptive_response", {})
            assert adaptive.get("adopted") is True
            assert adaptive.get("triggered_by") == "velocity_drop"
            assert summary["delegation_v1"]["adaptive_actions"] >= 1
            return {
                "scenario": "cortex_velocity_drop",
                "passed": True,
                "adaptive": adaptive,
            }


def run_consolidate_recovery_scenario() -> dict[str, Any]:
    calls = {"consolidate": 0}

    def fake_cortex(cfg):
        return {
            "session_id": "SIM-CX-CONS",
            "session_dir": "sim://cxcons",
            "protocols_run": 1,
            "total_steps": 100,
            "hypotheses": 1,
            "gaps_addressed": ["gap-cons"],
            "sanity_results": [],
            "dry_run": False,
        }

    def fake_consolidate(cfg, cortex_result):
        calls["consolidate"] += 1
        if calls["consolidate"] == 1:
            raise RuntimeError("simulated consolidate failure")
        return {"status": "ok", "artifacts": 2}

    with tempfile.TemporaryDirectory(prefix="sol-adaptive-sim-") as tmp:
        tmp_root = Path(tmp)
        patch = _base_paths(tmp_root)
        patch["stage_cortex"] = fake_cortex
        patch["stage_consolidate"] = fake_consolidate
        with _patched(orch, patch):
            runner = orch.PipelineRunner(
                orch.PipelineConfig(stages=["smoke", "cortex", "consolidate", "report"], verbose=False)
            )
            summary = runner.run()

            stage = runner.results["consolidate"]
            adaptive = stage.output.get("adaptive_response", {})
            assert stage.status == "passed"
            assert adaptive.get("adopted") is True
            assert adaptive.get("triggered_by") == "anomaly"
            assert summary["delegation_v1"]["adaptive_actions"] >= 1
            return {
                "scenario": "consolidate_recovery",
                "passed": True,
                "adaptive": adaptive,
            }


def run_hippocampus_recovery_scenario() -> dict[str, Any]:
    calls = {"hippocampus": 0}

    def fake_cortex(cfg):
        return {
            "session_id": "SIM-CX-HIP",
            "session_dir": "sim://cxhip",
            "protocols_run": 1,
            "total_steps": 100,
            "hypotheses": 1,
            "gaps_addressed": ["gap-hip"],
            "sanity_results": [],
            "dry_run": False,
        }

    def fake_consolidate(cfg, cortex_result):
        return {"status": "ok", "artifacts": 1}

    def fake_hippocampus(cfg):
        calls["hippocampus"] += 1
        if calls["hippocampus"] == 1:
            raise RuntimeError("simulated hippocampus failure")
        return {
            "dream_session_id": "SIM-DS-HIP",
            "sessions_replayed": 1,
            "replays_run": 1,
            "basins_discovered": 1,
            "basins_reinforced": 0,
            "basins_decayed": 0,
            "memory_nodes": 10,
            "memory_edges": 20,
            "dry_run": False,
        }

    with tempfile.TemporaryDirectory(prefix="sol-adaptive-sim-") as tmp:
        tmp_root = Path(tmp)
        patch = _base_paths(tmp_root)
        patch["stage_cortex"] = fake_cortex
        patch["stage_consolidate"] = fake_consolidate
        patch["stage_hippocampus"] = fake_hippocampus
        with _patched(orch, patch):
            runner = orch.PipelineRunner(
                orch.PipelineConfig(
                    stages=["smoke", "cortex", "consolidate", "hippocampus", "report"],
                    verbose=False,
                )
            )
            summary = runner.run()

            stage = runner.results["hippocampus"]
            adaptive = stage.output.get("adaptive_response", {})
            assert stage.status == "passed"
            assert adaptive.get("adopted") is True
            assert adaptive.get("triggered_by") == "anomaly"
            assert summary["delegation_v1"]["adaptive_actions"] >= 1
            return {
                "scenario": "hippocampus_recovery",
                "passed": True,
                "adaptive": adaptive,
            }


def run_evolve_recovery_scenario() -> dict[str, Any]:
    calls = {"evolve": 0}

    def fake_cortex(cfg):
        return {
            "session_id": "SIM-CX-EVO",
            "session_dir": "sim://cxevo",
            "protocols_run": 1,
            "total_steps": 100,
            "hypotheses": 1,
            "gaps_addressed": ["gap-evo"],
            "sanity_results": [],
            "dry_run": False,
        }

    def fake_consolidate(cfg, cortex_result):
        return {"status": "ok", "artifacts": 1}

    def fake_hippocampus(cfg):
        return {
            "dream_session_id": "SIM-DS-EVO",
            "sessions_replayed": 1,
            "replays_run": 1,
            "basins_discovered": 0,
            "basins_reinforced": 1,
            "basins_decayed": 0,
            "memory_nodes": 10,
            "memory_edges": 20,
            "dry_run": False,
        }

    def fake_evolve(cfg):
        calls["evolve"] += 1
        if calls["evolve"] == 1:
            raise RuntimeError("simulated evolve failure")
        return {
            "candidates_tested": 1,
            "reports": [{"candidate": "sim-cand", "verdict": "PASS"}],
            "any_regress": False,
        }

    with tempfile.TemporaryDirectory(prefix="sol-adaptive-sim-") as tmp:
        tmp_root = Path(tmp)
        patch = _base_paths(tmp_root)
        patch["stage_cortex"] = fake_cortex
        patch["stage_consolidate"] = fake_consolidate
        patch["stage_hippocampus"] = fake_hippocampus
        patch["stage_evolve"] = fake_evolve
        with _patched(orch, patch):
            runner = orch.PipelineRunner(
                orch.PipelineConfig(
                    stages=["smoke", "cortex", "consolidate", "hippocampus", "evolve", "report"],
                    evolve_candidates=["sim-cand"],
                    verbose=False,
                )
            )
            summary = runner.run()

            stage = runner.results["evolve"]
            adaptive = stage.output.get("adaptive_response", {})
            assert stage.status == "passed"
            assert adaptive.get("adopted") is True
            assert adaptive.get("triggered_by") == "anomaly"
            assert summary["delegation_v1"]["adaptive_actions"] >= 1
            return {
                "scenario": "evolve_recovery",
                "passed": True,
                "adaptive": adaptive,
            }


SCENARIOS = {
    "cortex_sanity_fail": run_cortex_sanity_fail_scenario,
    "cortex_velocity_drop": run_cortex_velocity_drop_scenario,
    "consolidate_recovery": run_consolidate_recovery_scenario,
    "hippocampus_recovery": run_hippocampus_recovery_scenario,
    "evolve_recovery": run_evolve_recovery_scenario,
}


def run_scenarios(selected: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name in selected:
        fn = SCENARIOS[name]
        results.append(fn())
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate adaptive trigger scenarios")
    parser.add_argument(
        "--scenario",
        choices=["all", *SCENARIOS.keys()],
        default="all",
        help="Scenario to run (default: all)",
    )
    args = parser.parse_args()

    selected = list(SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]
    results = run_scenarios(selected)

    print("Adaptive simulation results:")
    for result in results:
        print(f"  - {result['scenario']}: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
