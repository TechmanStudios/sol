from __future__ import annotations

import argparse
import json
from pathlib import Path

_HERE = Path(__file__).parent

from self_train.loop import run_generation_loop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SOL self-train scaffold loop")
    parser.add_argument(
        "--config",
        type=Path,
        default=_HERE / "self_train" / "config" / "self_train_config.json",
        help="Path to self-train config JSON",
    )
    parser.add_argument("--generations", type=int, default=3, help="How many generations to run")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data") / "sol_self_train",
        help="Output directory for run artifacts",
    )
    parser.add_argument(
        "--mode",
        choices=["default", "fast", "full", "overnight"],
        default="default",
        help="Runtime profile mode for per-task overrides",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    active_policy_path = run_generation_loop(
        config=config,
        generations=args.generations,
        out_dir=args.out_dir,
        mode=args.mode,
    )
    print(f"[self-train] complete. active policy: {active_policy_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
