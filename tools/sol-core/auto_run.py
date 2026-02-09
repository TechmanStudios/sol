"""
SOL Auto-Run Pipeline
=====================
Phase 1 of the Hippocampus Roadmap.

Given a protocol JSON, this module:
  1. Creates a headless SOL engine
  2. Runs all conditions (knob sweep × reps)
  3. Collects per-step metrics
  4. Runs sanity checks
  5. Generates run bundle + CSV exports
  6. Returns structured results for agent consumption

Usage (CLI):
    python auto_run.py protocol.json
    python auto_run.py protocol.json --out-dir results/

Usage (Python API):
    from auto_run import execute_protocol
    results = execute_protocol(protocol_dict)
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
import time
from pathlib import Path
from typing import Any

# Resolve imports regardless of cwd
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from sol_engine import SOLEngine, compute_metrics, snapshot_state, restore_state
from analysis.metrics import summarize_condition, compare_conditions
from analysis.sanity import run_standard_checks
from analysis.report import generate_run_bundle


def _build_conditions(protocol: dict) -> list[dict]:
    """Expand knobs into a list of condition dicts.
    
    If knobs is {"damping": [0.1, 0.2], "dt": [0.1, 0.12]},
    produces 4 conditions (cartesian product).
    If knobs is empty, produces a single condition with invariant values.
    """
    inv = protocol.get("invariants", {})
    knobs = protocol.get("knobs", {})

    if not knobs:
        # Single condition using invariants as the params
        return [{"label": "baseline", "params": dict(inv)}]

    # Build cartesian product
    knob_names = sorted(knobs.keys())
    knob_values = [knobs[k] for k in knob_names]
    conditions = []

    for combo in itertools.product(*knob_values):
        params = dict(inv)
        label_parts = []
        for name, val in zip(knob_names, combo):
            params[name] = val
            label_parts.append(f"{name}={val}")
        conditions.append({
            "label": "_".join(label_parts),
            "params": params,
        })

    return conditions


def _create_engine(params: dict, protocol: dict) -> SOLEngine:
    """Create an engine from condition params."""
    graph_path = params.get("graph", "default")
    kwargs = {
        "dt": params.get("dt", 0.12),
        "c_press": params.get("c_press", 0.1),
        "damping": params.get("damping", 0.2),
        "rng_seed": params.get("rng_seed", 42),
        "cap_law": params.get("cap_law"),
    }
    if graph_path and graph_path != "default":
        kwargs["graph_path"] = graph_path
    return SOLEngine.from_default_graph(**kwargs)


def _run_single(engine: SOLEngine, protocol: dict, rep: int) -> list[dict]:
    """Run a single rep of a condition. Returns per-step metric rows."""
    injections = protocol.get("injections", [{"label": "grail", "amount": 50}])
    steps = protocol.get("steps", 100)
    every = protocol.get("metrics_every", 1)
    deferred = [inj for inj in injections if inj.get("at_step", 0) > 0]
    immediate = [inj for inj in injections if inj.get("at_step", 0) == 0]

    # Immediate injections
    for inj in immediate:
        engine.inject(inj["label"], inj["amount"])

    rows = []
    for step_i in range(steps):
        # Deferred injections
        for inj in deferred:
            if inj.get("at_step") == step_i:
                engine.inject(inj["label"], inj["amount"])

        engine.step()

        if (step_i + 1) % every == 0 or step_i == steps - 1:
            m = engine.compute_metrics()
            m["step"] = step_i + 1
            m["t"] = engine.t
            m["rep"] = rep
            rows.append(m)

    return rows


def execute_protocol(protocol: dict, out_dir: Path | None = None) -> dict:
    """Execute a full protocol and return structured results.
    
    This is the main entry point for agent consumption.
    
    Returns:
        dict with keys:
        - summary: {total_conditions, total_reps, total_steps, runtime_sec}
        - conditions: {label: {final_metrics, analysis, trace}}
        - sanity: SanityReport as dict
        - exports: {name: path} of any written files
        - run_bundle: Markdown string
    """
    t0 = time.time()
    conditions = _build_conditions(protocol)
    reps = protocol.get("reps", 1)
    baseline_mode = protocol.get("baseline", "fresh")

    all_condition_results: dict[str, dict] = {}
    all_rows_flat: list[dict] = []
    all_condition_descriptors: list[dict] = []
    total_steps = 0

    injected_total = sum(inj.get("amount", 0) for inj in protocol.get("injections", []))

    for cond in conditions:
        label = cond["label"]
        params = cond["params"]
        cond_rows: list[dict] = []

        for rep_i in range(reps):
            if baseline_mode == "fresh" or rep_i == 0:
                engine = _create_engine(params, protocol)
            else:
                # restore mode: reset to post-init state
                restore_state(engine.physics, baseline_snap, protocol.get("invariants", {}).get("cap_law"))

            # Save baseline for restore mode
            if rep_i == 0 and baseline_mode == "restore":
                baseline_snap = snapshot_state(engine.physics)

            rep_rows = _run_single(engine, protocol, rep_i)
            # Tag each row with condition info
            for r in rep_rows:
                r["condition"] = label
                for k, v in params.items():
                    if k not in ("graph", "cap_law"):
                        r[f"param_{k}"] = v

            cond_rows.extend(rep_rows)
            total_steps += protocol.get("steps", 100)

        # Analyze this condition
        analysis = summarize_condition(cond_rows)
        final_metrics = cond_rows[-1] if cond_rows else {}

        all_condition_results[label] = {
            "final_metrics": final_metrics,
            "analysis": analysis,
            "trace": cond_rows,
        }
        all_rows_flat.extend(cond_rows)
        all_condition_descriptors.append(params)

    runtime = time.time() - t0

    # Sanity checks
    sanity = run_standard_checks(
        protocol, all_condition_descriptors, all_rows_flat, injected_total
    )

    # Build results
    summary = {
        "total_conditions": len(conditions),
        "total_reps": reps * len(conditions),
        "total_steps": total_steps,
        "runtime_sec": runtime,
    }

    run_results = {
        "summary": summary,
        "conditions": {
            label: {
                "final_metrics": data["final_metrics"],
                "analysis": data["analysis"],
            }
            for label, data in all_condition_results.items()
        },
    }

    # Comparison table (if >1 condition)
    comparison = None
    if len(all_condition_results) > 1:
        summaries = {label: data["analysis"] for label, data in all_condition_results.items()}
        comparison = compare_conditions(summaries)

    # Generate run bundle
    run_bundle_md = generate_run_bundle(protocol, run_results, sanity.to_dict())

    # Write exports if out_dir specified
    exports = {}
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        series = protocol.get("seriesName", "unnamed")

        # Summary CSV (one row per condition)
        summary_path = out_dir / f"{series}_summary.csv"
        _write_summary_csv(summary_path, all_condition_results)
        exports["summary_csv"] = str(summary_path)

        # Trace CSV (all per-step rows)
        if protocol.get("outputs", {}).get("trace_csv", True):
            trace_path = out_dir / f"{series}_trace.csv"
            _write_trace_csv(trace_path, all_rows_flat)
            exports["trace_csv"] = str(trace_path)

        # Run bundle Markdown
        if protocol.get("outputs", {}).get("run_bundle_md", True):
            bundle_path = out_dir / f"{series}_run_bundle.md"
            bundle_path.write_text(run_bundle_md, encoding="utf-8")
            exports["run_bundle_md"] = str(bundle_path)

        # Node states (optional)
        if protocol.get("outputs", {}).get("node_states", False):
            # Save final node states for the last condition
            last_label = list(all_condition_results.keys())[-1]
            states_path = out_dir / f"{series}_node_states.json"
            # Need to re-run to get states (or capture during run)
            # For now, skip — will add in future iteration
            pass

        run_results["exports"] = exports

    return {
        "summary": summary,
        "conditions": {
            label: {
                "final_metrics": data["final_metrics"],
                "analysis": data["analysis"],
            }
            for label, data in all_condition_results.items()
        },
        "comparison": comparison,
        "sanity": sanity.to_dict(),
        "run_bundle": run_bundle_md,
        "exports": exports,
    }


def _write_summary_csv(path: Path, condition_results: dict):
    """Write one row per condition with final metrics."""
    rows = []
    for label, data in condition_results.items():
        fm = data["final_metrics"]
        row = {"condition": label}
        for k, v in fm.items():
            if k not in ("condition", "rep"):
                row[k] = v
        rows.append(row)

    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _write_trace_csv(path: Path, rows: list[dict]):
    """Write all per-step metric rows."""
    if not rows:
        return
    # Collect all keys across all rows
    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())
    fieldnames = sorted(all_keys)

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---- CLI ---------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="SOL Auto-Run Pipeline")
    parser.add_argument("protocol", type=str, help="Path to protocol JSON file")
    parser.add_argument("--out-dir", type=str, default=None,
                        help="Output directory for CSVs and run bundle")
    parser.add_argument("--json", action="store_true",
                        help="Print results as JSON to stdout")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress summary output")

    args = parser.parse_args()

    protocol_path = Path(args.protocol)
    if not protocol_path.exists():
        print(f"Protocol file not found: {protocol_path}", file=sys.stderr)
        sys.exit(1)

    with open(protocol_path, "r", encoding="utf-8") as f:
        protocol = json.load(f)

    out_dir = Path(args.out_dir) if args.out_dir else protocol_path.parent / f"{protocol.get('seriesName', 'results')}_output"

    results = execute_protocol(protocol, out_dir)

    if args.json:
        # Strip large trace data for JSON output
        output = {
            "summary": results["summary"],
            "sanity": results["sanity"],
            "comparison": results["comparison"],
            "exports": results["exports"],
            "conditions": {
                label: {"final_metrics": data["final_metrics"]}
                for label, data in results["conditions"].items()
            },
        }
        print(json.dumps(output, indent=2, default=str))
    elif not args.quiet:
        s = results["summary"]
        print(f"=== {protocol.get('seriesName', 'unnamed')} ===")
        print(f"Conditions: {s['total_conditions']}  |  Reps: {s['total_reps']}  |  Steps: {s['total_steps']}  |  Runtime: {s['runtime_sec']:.2f}s")
        print()

        # Sanity
        sanity = results["sanity"]
        status = "PASS" if sanity["all_passed"] else "FAIL"
        print(f"Sanity: {status} ({sanity['total']} checks, {sanity['failures']} failures)")
        for check in sanity["checks"]:
            mark = "✓" if check["passed"] else "✗"
            print(f"  {mark} {check['name']}: {check['detail']}")
        print()

        # Per-condition final metrics
        for label, data in results["conditions"].items():
            fm = data["final_metrics"]
            print(f"  [{label}] entropy={fm.get('entropy', 0):.6f}  flux={fm.get('totalFlux', 0):.4f}  mass={fm.get('mass', 0):.4f}  active={fm.get('activeCount', 0)}")

        print()
        print(f"Exports: {', '.join(results['exports'].keys()) if results['exports'] else 'none'}")

    sys.exit(0 if results["sanity"]["all_passed"] else 1)


if __name__ == "__main__":
    main()
