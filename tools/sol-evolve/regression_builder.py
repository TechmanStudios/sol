"""
SOL Evolve — Regression Suite Builder
=======================================
Runs canonical protocols against the current engine and saves
deterministic "golden" outputs. These snapshots are the baseline
for A/B testing any proposed code change.

Golden outputs are deterministic because:
  - mulberry32 PRNG with seed=42
  - fresh baseline per rep
  - fixed protocol parameters

Usage (CLI):
    python regression_builder.py                    # Build all golden
    python regression_builder.py --protocol single_inject_baseline
    python regression_builder.py --verify           # Re-run and verify

Usage (Python API):
    from regression_builder import build_golden, verify_golden
    results = build_golden()
    report  = verify_golden()
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
_SOL_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))

from sol_engine import SOLEngine, compute_metrics, snapshot_state


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROTOCOL_DIR = _SOL_ROOT / "tools" / "sol-core" / "protocols"
GOLDEN_DIR = _SOL_ROOT / "tests" / "regression" / "golden"

# Canonical protocols — the regression suite
CANONICAL_PROTOCOLS = [
    "single_inject_baseline",
    "damping_sweep_smoke",
    "dual_inject_timing",
]


# ---------------------------------------------------------------------------
# Golden snapshot format
# ---------------------------------------------------------------------------

@dataclass
class GoldenCheckpoint:
    """A deterministic metric snapshot at a specific step."""
    step: int
    entropy: float
    totalFlux: float
    mass: float
    rhoMaxId: Any
    activeCount: int
    maxRho: float

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "entropy": self.entropy,
            "totalFlux": self.totalFlux,
            "mass": self.mass,
            "rhoMaxId": self.rhoMaxId,
            "activeCount": self.activeCount,
            "maxRho": self.maxRho,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GoldenCheckpoint":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})


def _run_golden(protocol: dict) -> dict:
    """Run a protocol deterministically and capture golden checkpoints.

    Single-rep, deterministic seed, capturing checkpoints at key steps.
    Returns a golden snapshot dict.
    """
    inv = protocol.get("invariants", {})
    dt = inv.get("dt", 0.12)
    c_press = inv.get("c_press", 0.1)
    damping = inv.get("damping", 0.2)
    seed = inv.get("rng_seed", 42)
    steps = protocol.get("steps", 200)
    injections = protocol.get("injections", [{"label": "grail", "amount": 50}])

    # Handle knob sweeps: run each condition separately
    knobs = protocol.get("knobs", {})
    conditions = {}

    if not knobs:
        # Single condition
        conditions["baseline"] = {"dt": dt, "c_press": c_press, "damping": damping}
    else:
        # Expand knobs
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

    # Checkpoint steps: start, 25%, 50%, 75%, end
    checkpoint_steps = sorted(set([
        0,
        steps // 4,
        steps // 2,
        3 * steps // 4,
        steps - 1,
    ]))

    golden_conditions = {}

    for label, params in conditions.items():
        engine = SOLEngine.from_default_graph(
            dt=params["dt"], c_press=params["c_press"],
            damping=params["damping"], rng_seed=seed,
        )

        # Immediate injections
        for inj in injections:
            if inj.get("at_step", 0) == 0:
                engine.inject(inj["label"], inj["amount"])

        deferred = [inj for inj in injections if inj.get("at_step", 0) > 0]
        checkpoints = []

        for step_i in range(steps):
            # Deferred injections
            for inj in deferred:
                if inj.get("at_step") == step_i:
                    engine.inject(inj["label"], inj["amount"])

            engine.step()

            if step_i in checkpoint_steps:
                m = engine.compute_metrics()
                checkpoints.append(GoldenCheckpoint(
                    step=step_i + 1,
                    entropy=m["entropy"],
                    totalFlux=m["totalFlux"],
                    mass=m["mass"],
                    rhoMaxId=m["rhoMaxId"],
                    activeCount=m["activeCount"],
                    maxRho=m["maxRho"],
                ).to_dict())

        golden_conditions[label] = {
            "params": params,
            "checkpoints": checkpoints,
            "final_metrics": engine.compute_metrics(),
        }

    return {
        "protocol": protocol.get("seriesName", "unnamed"),
        "engine_version": "sol_engine.py-phase0",
        "rng_seed": seed,
        "total_steps": steps,
        "conditions": golden_conditions,
    }


# ---------------------------------------------------------------------------
# Build & Verify
# ---------------------------------------------------------------------------

def build_golden(protocol_names: list[str] | None = None, out_dir: Path | None = None) -> dict:
    """Build golden outputs for all canonical protocols.

    Returns dict mapping protocol name → golden file path.
    """
    names = protocol_names or CANONICAL_PROTOCOLS
    out = out_dir or GOLDEN_DIR
    out.mkdir(parents=True, exist_ok=True)

    results = {}
    for name in names:
        proto_path = PROTOCOL_DIR / f"{name}.json"
        if not proto_path.exists():
            print(f"  SKIP: {name} — protocol not found at {proto_path}")
            continue

        protocol = json.loads(proto_path.read_text(encoding="utf-8"))
        golden = _run_golden(protocol)

        golden_path = out / f"{name}_golden.json"
        golden_path.write_text(json.dumps(golden, indent=2, default=str), encoding="utf-8")
        results[name] = str(golden_path)
        print(f"  GOLDEN: {name} → {golden_path}")

    return results


def verify_golden(golden_dir: Path | None = None, tolerance: float = 1e-9) -> dict:
    """Re-run all golden protocols and verify outputs match.

    Returns verification report.
    """
    g_dir = golden_dir or GOLDEN_DIR
    if not g_dir.exists():
        return {"status": "NO_GOLDEN", "message": "No golden directory found. Run build_golden() first."}

    report = {"status": "PASS", "protocols": {}}

    for gpath in sorted(g_dir.glob("*_golden.json")):
        golden = json.loads(gpath.read_text(encoding="utf-8"))
        proto_name = golden["protocol"]
        proto_path = PROTOCOL_DIR / f"{proto_name}.json"

        if not proto_path.exists():
            report["protocols"][proto_name] = {"status": "SKIP", "reason": "protocol file not found"}
            continue

        protocol = json.loads(proto_path.read_text(encoding="utf-8"))
        current = _run_golden(protocol)

        # Compare
        mismatches = []
        for cond_label in golden["conditions"]:
            if cond_label not in current["conditions"]:
                mismatches.append(f"{cond_label}: condition missing in current run")
                continue

            gold_cps = golden["conditions"][cond_label]["checkpoints"]
            curr_cps = current["conditions"][cond_label]["checkpoints"]

            for g_cp, c_cp in zip(gold_cps, curr_cps):
                for key in ("entropy", "totalFlux", "mass", "maxRho"):
                    g_val = g_cp.get(key, 0)
                    c_val = c_cp.get(key, 0)
                    if abs(g_val - c_val) > tolerance:
                        mismatches.append(
                            f"{cond_label} step={g_cp['step']} {key}: "
                            f"golden={g_val:.10f} current={c_val:.10f} delta={abs(g_val-c_val):.2e}")

                # RhoMaxId is discrete — must match exactly
                if g_cp.get("rhoMaxId") != c_cp.get("rhoMaxId"):
                    mismatches.append(
                        f"{cond_label} step={g_cp['step']} rhoMaxId: "
                        f"golden={g_cp['rhoMaxId']} current={c_cp['rhoMaxId']}")

        if mismatches:
            report["protocols"][proto_name] = {"status": "FAIL", "mismatches": mismatches}
            report["status"] = "FAIL"
        else:
            report["protocols"][proto_name] = {"status": "PASS", "checkpoints_verified": len(gold_cps)}

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SOL Evolve — Regression Suite Builder")
    parser.add_argument("--protocol", type=str, default=None,
                        help="Build golden for a specific protocol (by name)")
    parser.add_argument("--verify", action="store_true",
                        help="Re-run and verify existing golden outputs")
    parser.add_argument("--out-dir", type=str, default=None)
    args = parser.parse_args()

    if args.verify:
        print("=== Verifying Golden Outputs ===")
        report = verify_golden()
        print(f"\nOverall: {report['status']}")
        for name, info in report.get("protocols", {}).items():
            status = info["status"]
            detail = info.get("checkpoints_verified", info.get("mismatches", []))
            if status == "PASS":
                print(f"  ✓ {name}: PASS ({detail} checkpoints)")
            else:
                print(f"  ✗ {name}: {status}")
                if isinstance(detail, list):
                    for m in detail[:5]:
                        print(f"      {m}")
        sys.exit(0 if report["status"] == "PASS" else 1)

    names = [args.protocol] if args.protocol else None
    out = Path(args.out_dir) if args.out_dir else None

    print("=== Building Golden Outputs ===")
    results = build_golden(names, out)
    print(f"\n{len(results)} golden snapshots built")


if __name__ == "__main__":
    main()
