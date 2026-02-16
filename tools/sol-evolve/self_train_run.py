from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from self_train.loop import run_generation_loop


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SOL self-train canonical run launcher")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("tools") / "sol-evolve" / "self_train" / "config" / "self_train_config.json",
        help="Path to self-train config JSON",
    )
    parser.add_argument("--generations", type=int, default=3, help="How many generations to run")
    parser.add_argument(
        "--mode",
        choices=["default", "fast", "full", "overnight"],
        default="default",
        help="Runtime profile mode",
    )
    parser.add_argument(
        "--source",
        default="local-desktop",
        help="Source label (e.g., local-desktop, github-actions)",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Optional externally provided run id (e.g., GitHub run_id)",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("data") / "sol_self_train_runs",
        help="Canonical root for all self-train runs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))

    run_tag = args.run_id.strip() or utc_stamp()
    out_dir = args.out_root / args.source / args.mode / run_tag

    active_policy_path = run_generation_loop(
        config=config,
        generations=args.generations,
        out_dir=out_dir,
        mode=args.mode,
    )

    print(f"[self-train-run] source={args.source} mode={args.mode} run={run_tag}")
    print(f"[self-train-run] out_dir={out_dir}")
    print(f"[self-train-run] active_policy={active_policy_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
