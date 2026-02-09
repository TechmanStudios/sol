"""
sol-core CLI — Run headless SOL simulations from the command line.
=================================================================

Usage:
    python cli.py smoke              Quick sanity check
    python cli.py run --steps 200    Run 200 steps, print final metrics
    python cli.py run --steps 200 --inject grail:50,consciousness:30
    python cli.py run --steps 200 --json          Output as JSON
    python cli.py run --steps 200 --csv out.csv   Write per-step CSV
    python cli.py sweep --param damping --range 0.05,0.1,0.2,0.5 --steps 100
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Allow running from any working directory
sys.path.insert(0, str(Path(__file__).parent))
from sol_engine import SOLEngine, compute_metrics


def cmd_smoke(args):
    """Quick smoke test: inject into a node, run 100 steps, print metrics."""
    engine = SOLEngine.from_default_graph()
    m0 = engine.compute_metrics()
    engine.inject("grail", 50)
    engine.run(100)
    m1 = engine.compute_metrics()
    print("=== SOL-Core Smoke Test ===")
    print(f"Nodes: {len(engine.physics.nodes)}")
    print(f"Edges: {len(engine.physics.edges)}")
    print(f"Steps: 100")
    print(f"Pre-inject mass:  {m0['mass']:.4f}")
    print(f"Post-run mass:    {m1['mass']:.4f}")
    print(f"Entropy:          {m1['entropy']:.6f}")
    print(f"Total flux:       {m1['totalFlux']:.4f}")
    print(f"Active nodes:     {m1['activeCount']}")
    print(f"Max ρ:            {m1['maxRho']:.4f} (node: {m1['rhoMaxId']})")
    ok = m1["mass"] > 0 and m1["entropy"] > 0 and m1["activeCount"] > 0
    print(f"Result: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def cmd_run(args):
    """Run a simulation and print results."""
    engine = SOLEngine.from_default_graph(
        dt=args.dt, c_press=args.c_press, damping=args.damping,
    )

    # Apply injections
    if args.inject:
        for pair in args.inject.split(","):
            parts = pair.strip().split(":")
            label = parts[0].strip()
            amount = float(parts[1]) if len(parts) > 1 else 50.0
            ok = engine.inject(label, amount)
            if not ok:
                print(f"Warning: node '{label}' not found", file=sys.stderr)

    # Run and collect per-step data
    rows = []
    for i in range(args.steps):
        step_result = engine.step()
        if args.csv or args.every and (i + 1) % args.every == 0:
            m = engine.compute_metrics()
            m["step"] = i + 1
            m["t"] = engine.t
            rows.append(m)

    final = engine.compute_metrics()
    final["step"] = args.steps
    final["t"] = engine.t

    if args.csv:
        out_path = Path(args.csv)
        if not rows:
            rows = [final]
        fieldnames = list(rows[0].keys())
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {len(rows)} rows to {out_path}")
    elif args.json:
        print(json.dumps(final, indent=2, default=str))
    else:
        print(f"Steps: {args.steps}  |  t = {engine.t:.4f}")
        for k, v in final.items():
            if isinstance(v, float):
                print(f"  {k:20s} = {v:.6f}")
            else:
                print(f"  {k:20s} = {v}")

    return 0


def cmd_sweep(args):
    """Sweep one parameter across a range and compare final metrics."""
    values = [float(x) for x in args.range.split(",")]
    results = []

    for val in values:
        kwargs = {"dt": args.dt, "c_press": args.c_press, "damping": args.damping}
        if args.param in kwargs:
            kwargs[args.param] = val
        else:
            print(f"Unknown param: {args.param}", file=sys.stderr)
            return 1

        engine = SOLEngine.from_default_graph(**kwargs)
        if args.inject:
            for pair in args.inject.split(","):
                parts = pair.strip().split(":")
                engine.inject(parts[0].strip(), float(parts[1]) if len(parts) > 1 else 50.0)

        engine.run(args.steps)
        m = engine.compute_metrics()
        m[args.param] = val
        results.append(m)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        header = [args.param, "entropy", "totalFlux", "mass", "activeCount"]
        print(" | ".join(f"{h:>14s}" for h in header))
        print("-" * (16 * len(header)))
        for r in results:
            print(" | ".join(f"{r.get(h, ''):>14.6f}" if isinstance(r.get(h), float) else f"{r.get(h, ''):>14}" for h in header))

    return 0


def main():
    parser = argparse.ArgumentParser(description="SOL Engine Headless CLI")
    sub = parser.add_subparsers(dest="command")

    # smoke
    sub.add_parser("smoke", help="Quick sanity check")

    # run
    run_p = sub.add_parser("run", help="Run a simulation")
    run_p.add_argument("--steps", type=int, default=100)
    run_p.add_argument("--dt", type=float, default=0.12)
    run_p.add_argument("--c-press", type=float, default=0.1)
    run_p.add_argument("--damping", type=float, default=0.2)
    run_p.add_argument("--inject", type=str, default=None, help="label:amount,label:amount")
    run_p.add_argument("--json", action="store_true")
    run_p.add_argument("--csv", type=str, default=None)
    run_p.add_argument("--every", type=int, default=1, help="Record metrics every N steps")

    # sweep
    sweep_p = sub.add_parser("sweep", help="Sweep a parameter")
    sweep_p.add_argument("--param", type=str, required=True)
    sweep_p.add_argument("--range", type=str, required=True, help="Comma-separated values")
    sweep_p.add_argument("--steps", type=int, default=100)
    sweep_p.add_argument("--dt", type=float, default=0.12)
    sweep_p.add_argument("--c-press", type=float, default=0.1)
    sweep_p.add_argument("--damping", type=float, default=0.2)
    sweep_p.add_argument("--inject", type=str, default=None)
    sweep_p.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "smoke":
        sys.exit(cmd_smoke(args))
    elif args.command == "run":
        sys.exit(cmd_run(args))
    elif args.command == "sweep":
        sys.exit(cmd_sweep(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
