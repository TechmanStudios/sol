"""
SOL Evolve — A/B Test Harness
================================
Runs the same protocol on both the golden (unmodified) engine and a
candidate-modified engine, then compares outputs to detect regressions
and improvements.

Verdict categories:
  PASS       — Candidate produces identical or near-identical results
  IMPROVE    — Candidate improves target metrics without net regression
  REGRESS    — Candidate degrades metrics beyond acceptable tolerance
  MIXED      — Some improve, some regress (needs human review)

Usage (CLI):
    python ab_test.py --candidate tune_conductance_gamma_up
    python ab_test.py --candidate tune_conductance_gamma_up --protocol single_inject_baseline

Usage (Python API):
    from ab_test import ABTest
    test = ABTest("tune_conductance_gamma_up")
    report = test.run()
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
_SOL_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))

from sol_engine import SOLEngine, compute_metrics
from candidates import Candidate, load_candidate, apply_candidate
from regression_builder import GOLDEN_DIR, PROTOCOL_DIR, CANONICAL_PROTOCOLS, _run_golden


# ---------------------------------------------------------------------------
# Tolerance configuration
# ---------------------------------------------------------------------------

# Relative tolerance for numeric comparisons
DEFAULT_TOLERANCE = {
    "entropy": 0.05,        # 5% relative
    "totalFlux": 0.10,      # 10% relative (flux is noisy)
    "mass": 0.02,           # 2% relative (mass is conserved)
    "maxRho": 0.10,         # 10% relative
    "activeCount": 0.15,    # 15% relative (integer metric, jumpy)
}


# ---------------------------------------------------------------------------
# Comparison engine
# ---------------------------------------------------------------------------

@dataclass
class MetricDelta:
    """Comparison of a single metric between golden and candidate."""
    metric: str
    golden_val: float
    candidate_val: float
    absolute_delta: float
    relative_delta: float          # (candidate - golden) / golden
    tolerance: float
    within_tolerance: bool
    direction: str                 # "improved", "regressed", "unchanged"

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "golden": round(self.golden_val, 8),
            "candidate": round(self.candidate_val, 8),
            "abs_delta": round(self.absolute_delta, 8),
            "rel_delta": f"{self.relative_delta:+.4%}",
            "tolerance": f"{self.tolerance:.2%}",
            "within_tolerance": self.within_tolerance,
            "direction": self.direction,
        }


def compare_checkpoints(golden_cps: list[dict], candidate_cps: list[dict],
                         tolerance: dict | None = None) -> list[dict]:
    """Compare checkpoint-by-checkpoint metrics."""
    tol = tolerance or DEFAULT_TOLERANCE
    comparisons = []

    for g_cp, c_cp in zip(golden_cps, candidate_cps):
        step = g_cp["step"]
        step_deltas = []

        for metric in ("entropy", "totalFlux", "mass", "maxRho", "activeCount"):
            g_val = g_cp.get(metric, 0)
            c_val = c_cp.get(metric, 0)
            abs_delta = c_val - g_val
            rel_delta = abs_delta / g_val if g_val != 0 else (0 if c_val == 0 else float("inf"))
            t = tol.get(metric, 0.05)
            within = abs(rel_delta) <= t

            # Determine direction heuristic
            if abs(rel_delta) <= t * 0.1:
                direction = "unchanged"
            elif metric == "entropy":
                direction = "improved" if c_val > g_val else "regressed"
            elif metric == "mass":
                direction = "unchanged" if within else ("regressed" if c_val < g_val else "improved")
            elif metric == "activeCount":
                direction = "improved" if c_val > g_val else "regressed"
            else:
                direction = "changed"

            step_deltas.append(MetricDelta(
                metric=metric, golden_val=g_val, candidate_val=c_val,
                absolute_delta=abs_delta, relative_delta=rel_delta,
                tolerance=t, within_tolerance=within, direction=direction,
            ))

        # RhoMaxId (discrete)
        rho_match = g_cp.get("rhoMaxId") == c_cp.get("rhoMaxId")

        comparisons.append({
            "step": step,
            "metrics": [d.to_dict() for d in step_deltas],
            "rhoMaxId_match": rho_match,
            "rhoMaxId_golden": g_cp.get("rhoMaxId"),
            "rhoMaxId_candidate": c_cp.get("rhoMaxId"),
            "all_within_tolerance": all(d.within_tolerance for d in step_deltas),
        })

    return comparisons


def determine_verdict(comparisons: list[dict], candidate: Candidate) -> dict:
    """Determine overall verdict from checkpoint comparisons."""
    total_checks = 0
    within_tol = 0
    regressions = 0
    improvements = 0
    rho_mismatches = 0

    for comp in comparisons:
        for m in comp["metrics"]:
            total_checks += 1
            if m["within_tolerance"]:
                within_tol += 1
            if m["direction"] == "regressed" and not m["within_tolerance"]:
                regressions += 1
            if m["direction"] == "improved" and not m["within_tolerance"]:
                improvements += 1
        if not comp["rhoMaxId_match"]:
            rho_mismatches += 1

    regression_rate = regressions / max(1, total_checks)
    improvement_rate = improvements / max(1, total_checks)

    if regression_rate == 0 and improvement_rate == 0:
        verdict = "PASS"
        reason = "Candidate produces results within tolerance of golden"
    elif regression_rate == 0 and improvement_rate > 0:
        verdict = "IMPROVE"
        reason = f"{improvements} metrics improved, 0 regressions"
    elif regression_rate > 0 and improvement_rate == 0:
        verdict = "REGRESS"
        reason = f"{regressions} metrics regressed"
    else:
        verdict = "MIXED"
        reason = f"{improvements} improvements, {regressions} regressions — needs human review"

    return {
        "verdict": verdict,
        "reason": reason,
        "total_checks": total_checks,
        "within_tolerance": within_tol,
        "regressions": regressions,
        "improvements": improvements,
        "rhoMaxId_mismatches": rho_mismatches,
        "regression_rate": f"{regression_rate:.1%}",
        "improvement_rate": f"{improvement_rate:.1%}",
    }


# ---------------------------------------------------------------------------
# ABTest class
# ---------------------------------------------------------------------------

class ABTest:
    """Run an A/B test comparing golden vs candidate-modified engine."""

    def __init__(self, candidate_name: str,
                 protocol_names: list[str] | None = None,
                 tolerance: dict | None = None):
        self.candidate = load_candidate(candidate_name)
        self.protocols = protocol_names or CANONICAL_PROTOCOLS
        self.tolerance = tolerance or DEFAULT_TOLERANCE
        self.results: dict[str, dict] = {}

    def run(self) -> dict:
        """Execute the A/B test across all protocols.

        Returns a comprehensive test report.
        """
        t0 = time.time()
        overall_verdicts = []

        for proto_name in self.protocols:
            proto_path = PROTOCOL_DIR / f"{proto_name}.json"
            golden_path = GOLDEN_DIR / f"{proto_name}_golden.json"

            if not proto_path.exists():
                self.results[proto_name] = {"status": "SKIP", "reason": "protocol not found"}
                continue

            protocol = json.loads(proto_path.read_text(encoding="utf-8"))

            # Load or generate golden
            if golden_path.exists():
                golden = json.loads(golden_path.read_text(encoding="utf-8"))
            else:
                golden = _run_golden(protocol)

            # Run candidate
            candidate_output = self._run_candidate(protocol)

            # Compare each condition
            condition_results = {}
            for cond_label in golden["conditions"]:
                if cond_label not in candidate_output["conditions"]:
                    condition_results[cond_label] = {"status": "MISSING"}
                    continue

                g_cps = golden["conditions"][cond_label]["checkpoints"]
                c_cps = candidate_output["conditions"][cond_label]["checkpoints"]

                comparisons = compare_checkpoints(g_cps, c_cps, self.tolerance)
                verdict = determine_verdict(comparisons, self.candidate)

                condition_results[cond_label] = {
                    "verdict": verdict,
                    "comparisons": comparisons,
                }
                overall_verdicts.append(verdict["verdict"])

            self.results[proto_name] = {
                "status": "COMPLETE",
                "conditions": condition_results,
            }

        elapsed = time.time() - t0

        # Overall verdict
        if all(v == "PASS" for v in overall_verdicts):
            overall = "PASS"
        elif "REGRESS" in overall_verdicts:
            overall = "REGRESS"
        elif "MIXED" in overall_verdicts:
            overall = "MIXED"
        elif "IMPROVE" in overall_verdicts and "REGRESS" not in overall_verdicts:
            overall = "IMPROVE"
        else:
            overall = "UNKNOWN"

        return {
            "candidate": self.candidate.to_dict(),
            "overall_verdict": overall,
            "elapsed_sec": round(elapsed, 2),
            "protocols": self.results,
            "per_condition_verdicts": overall_verdicts,
        }

    def _run_candidate(self, protocol: dict) -> dict:
        """Run a protocol with the candidate modification applied."""
        inv = protocol.get("invariants", {})
        dt = inv.get("dt", 0.12)
        c_press = inv.get("c_press", 0.1)
        damping = inv.get("damping", 0.2)
        seed = inv.get("rng_seed", 42)
        steps = protocol.get("steps", 200)
        injections = protocol.get("injections", [{"label": "grail", "amount": 50}])

        knobs = protocol.get("knobs", {})
        conditions = {}
        if not knobs:
            conditions["baseline"] = {"dt": dt, "c_press": c_press, "damping": damping}
        else:
            import itertools
            knob_names = sorted(knobs.keys())
            knob_values = [knobs[k] for k in knob_names]
            for combo in itertools.product(*knob_values):
                params = {"dt": dt, "c_press": c_press, "damping": damping}
                label_parts = []
                for name, val in zip(knob_names, combo):
                    params[name] = val
                    label_parts.append(f"{name}={val}")
                conditions["_".join(label_parts)] = params

        checkpoint_steps = sorted(set([0, steps // 4, steps // 2, 3 * steps // 4, steps - 1]))
        candidate_conditions = {}

        for label, params in conditions.items():
            engine = SOLEngine.from_default_graph(
                dt=params["dt"], c_press=params["c_press"],
                damping=params["damping"], rng_seed=seed,
            )

            # Apply candidate modification
            apply_candidate(engine, self.candidate)

            for inj in injections:
                if inj.get("at_step", 0) == 0:
                    engine.inject(inj["label"], inj["amount"])

            deferred = [inj for inj in injections if inj.get("at_step", 0) > 0]
            checkpoints = []

            for step_i in range(steps):
                for inj in deferred:
                    if inj.get("at_step") == step_i:
                        engine.inject(inj["label"], inj["amount"])
                engine.step()
                if step_i in checkpoint_steps:
                    m = engine.compute_metrics()
                    checkpoints.append({
                        "step": step_i + 1,
                        "entropy": m["entropy"],
                        "totalFlux": m["totalFlux"],
                        "mass": m["mass"],
                        "rhoMaxId": m["rhoMaxId"],
                        "activeCount": m["activeCount"],
                        "maxRho": m["maxRho"],
                    })

            candidate_conditions[label] = {
                "params": params,
                "checkpoints": checkpoints,
                "final_metrics": engine.compute_metrics(),
            }

        return {"conditions": candidate_conditions}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SOL Evolve — A/B Test Harness")
    parser.add_argument("--candidate", type=str, required=True,
                        help="Name of the candidate to test")
    parser.add_argument("--protocol", type=str, default=None,
                        help="Test against a specific protocol only")
    parser.add_argument("--json", action="store_true",
                        help="Output full report as JSON")
    parser.add_argument("--out", type=str, default=None,
                        help="Save report to this file")
    args = parser.parse_args()

    protocols = [args.protocol] if args.protocol else None
    test = ABTest(args.candidate, protocols)

    print(f"=== A/B Test: {args.candidate} ===\n")
    report = test.run()

    if args.json:
        output = json.dumps(report, indent=2, default=str)
        if args.out:
            Path(args.out).write_text(output, encoding="utf-8")
            print(f"Report saved to {args.out}")
        else:
            print(output)
    else:
        print(f"Candidate:  {report['candidate']['name']}")
        print(f"Hypothesis: {report['candidate']['hypothesis']}")
        print(f"Verdict:    {report['overall_verdict']}")
        print(f"Runtime:    {report['elapsed_sec']}s\n")

        for proto_name, proto_result in report["protocols"].items():
            if proto_result["status"] != "COMPLETE":
                print(f"  [{proto_name}] {proto_result['status']}: {proto_result.get('reason', '')}")
                continue

            for cond, cond_result in proto_result["conditions"].items():
                v = cond_result["verdict"]
                print(f"  [{proto_name}/{cond}] {v['verdict']}: {v['reason']}")
                if v["regressions"] > 0:
                    # Show which metrics regressed
                    for comp in cond_result["comparisons"]:
                        for m in comp["metrics"]:
                            if m["direction"] == "regressed" and not m["within_tolerance"]:
                                print(f"    ! step={comp['step']} {m['metric']}: "
                                      f"golden={m['golden']}, candidate={m['candidate']} "
                                      f"({m['rel_delta']})")

        if args.out:
            Path(args.out).write_text(
                json.dumps(report, indent=2, default=str), encoding="utf-8")
            print(f"\nFull report saved to {args.out}")

    sys.exit(0 if report["overall_verdict"] in ("PASS", "IMPROVE") else 1)


if __name__ == "__main__":
    main()
