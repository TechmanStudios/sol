from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class GenerationRecord:
    source: str
    mode: str
    run_id: str
    generation: int
    accepted: bool
    delta_anchor: float
    delta_full: float
    reason: str
    summary_path: str


@dataclass
class RunAggregate:
    source: str
    mode: str
    run_id: str
    generations: int
    accepted_generations: int
    acceptance_rate: float
    best_delta_anchor: float
    best_delta_full: float
    latest_delta_anchor: float
    latest_delta_full: float
    latest_reason: str


@dataclass
class Ledger:
    generated_at: str
    root: str
    total_generations: int
    total_runs: int
    accepted_generations: int
    acceptance_rate: float
    by_mode: dict[str, dict[str, Any]]
    top_runs_by_anchor: list[RunAggregate]
    promotion_ready_runs: list[RunAggregate]
    near_miss_runs: list[RunAggregate]
    generation_records: list[GenerationRecord]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _discover_generation_records(root: Path) -> list[GenerationRecord]:
    records: list[GenerationRecord] = []
    for summary in root.glob("*/*/*/gen_*/summary.json"):
        try:
            rel = summary.relative_to(root)
            parts = rel.parts
            if len(parts) < 5:
                continue
            source, mode, run_id = parts[0], parts[1], parts[2]
            if source.startswith("_"):
                continue

            payload = json.loads(summary.read_text(encoding="utf-8"))
            records.append(
                GenerationRecord(
                    source=source,
                    mode=mode,
                    run_id=run_id,
                    generation=int(payload.get("generation", 0)),
                    accepted=bool(payload.get("accepted", False)),
                    delta_anchor=_as_float(payload.get("delta_anchor", 0.0)),
                    delta_full=_as_float(payload.get("delta_full", 0.0)),
                    reason=str(payload.get("reason", "")),
                    summary_path=str(summary).replace("\\", "/"),
                )
            )
        except Exception:
            continue

    records.sort(key=lambda r: (r.source, r.mode, r.run_id, r.generation))
    return records


def _aggregate_runs(records: list[GenerationRecord]) -> list[RunAggregate]:
    grouped: dict[tuple[str, str, str], list[GenerationRecord]] = {}
    for record in records:
        key = (record.source, record.mode, record.run_id)
        grouped.setdefault(key, []).append(record)

    aggregates: list[RunAggregate] = []
    for (source, mode, run_id), rows in grouped.items():
        rows.sort(key=lambda r: r.generation)
        accepted_generations = sum(1 for r in rows if r.accepted)
        latest = rows[-1]
        best_anchor = max(r.delta_anchor for r in rows)
        best_full = max(r.delta_full for r in rows)

        generations = len(rows)
        aggregates.append(
            RunAggregate(
                source=source,
                mode=mode,
                run_id=run_id,
                generations=generations,
                accepted_generations=accepted_generations,
                acceptance_rate=accepted_generations / max(1, generations),
                best_delta_anchor=best_anchor,
                best_delta_full=best_full,
                latest_delta_anchor=latest.delta_anchor,
                latest_delta_full=latest.delta_full,
                latest_reason=latest.reason,
            )
        )

    aggregates.sort(key=lambda a: (a.source, a.mode, a.run_id))
    return aggregates


def _build_mode_summary(records: list[GenerationRecord]) -> dict[str, dict[str, Any]]:
    by_mode: dict[str, list[GenerationRecord]] = {}
    for record in records:
        by_mode.setdefault(record.mode, []).append(record)

    summary: dict[str, dict[str, Any]] = {}
    for mode, rows in sorted(by_mode.items()):
        accepted = sum(1 for r in rows if r.accepted)
        summary[mode] = {
            "runs": len({(r.source, r.run_id) for r in rows}),
            "generations": len(rows),
            "accepted_generations": accepted,
            "acceptance_rate": accepted / max(1, len(rows)),
            "best_delta_anchor": max(r.delta_anchor for r in rows),
            "mean_delta_anchor": sum(r.delta_anchor for r in rows) / max(1, len(rows)),
            "best_delta_full": max(r.delta_full for r in rows),
            "mean_delta_full": sum(r.delta_full for r in rows) / max(1, len(rows)),
        }
    return summary


def _to_markdown(ledger: Ledger) -> str:
    lines: list[str] = []
    lines.append("# Self-Train Consolidation Ledger")
    lines.append("")
    lines.append(f"Generated: {ledger.generated_at}")
    lines.append(f"Root: {ledger.root}")
    lines.append("")
    lines.append("## Global")
    lines.append("")
    lines.append(f"- Total runs: {ledger.total_runs}")
    lines.append(f"- Total generations: {ledger.total_generations}")
    lines.append(f"- Accepted generations: {ledger.accepted_generations}")
    lines.append(f"- Acceptance rate: {ledger.acceptance_rate:.2%}")
    lines.append("")

    lines.append("## By Mode")
    lines.append("")
    lines.append("| Mode | Runs | Gens | Accepted | Acceptance | Best dA | Mean dA | Best dF | Mean dF |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for mode, stats in ledger.by_mode.items():
        lines.append(
            "| {mode} | {runs} | {gens} | {acc} | {rate:.2%} | {bda:.4f} | {mda:.4f} | {bdf:.4f} | {mdf:.4f} |".format(
                mode=mode,
                runs=stats["runs"],
                gens=stats["generations"],
                acc=stats["accepted_generations"],
                rate=stats["acceptance_rate"],
                bda=stats["best_delta_anchor"],
                mda=stats["mean_delta_anchor"],
                bdf=stats["best_delta_full"],
                mdf=stats["mean_delta_full"],
            )
        )
    lines.append("")

    lines.append("## Top Runs by Anchor Delta")
    lines.append("")
    lines.append("| Source | Mode | Run | Gens | Best dA | Latest dA | Latest dF |")
    lines.append("|---|---|---|---:|---:|---:|---:|")
    for run in ledger.top_runs_by_anchor:
        lines.append(
            f"| {run.source} | {run.mode} | {run.run_id} | {run.generations} | {run.best_delta_anchor:.4f} | {run.latest_delta_anchor:.4f} | {run.latest_delta_full:.4f} |"
        )
    lines.append("")

    lines.append("## Promotion Ready Runs")
    lines.append("")
    if ledger.promotion_ready_runs:
        for run in ledger.promotion_ready_runs:
            lines.append(
                f"- {run.source}/{run.mode}/{run.run_id} (best dA={run.best_delta_anchor:.4f}, best dF={run.best_delta_full:.4f})"
            )
    else:
        lines.append("- None yet")
    lines.append("")

    lines.append("## Near Miss Runs")
    lines.append("")
    if ledger.near_miss_runs:
        for run in ledger.near_miss_runs:
            lines.append(
                f"- {run.source}/{run.mode}/{run.run_id} (best dA={run.best_delta_anchor:.4f}, latest reason: {run.latest_reason})"
            )
    else:
        lines.append("- None")
    lines.append("")

    return "\n".join(lines)


def build_ledger(root: Path, min_anchor_delta: float, min_full_delta: float) -> Ledger:
    records = _discover_generation_records(root)
    runs = _aggregate_runs(records)

    accepted_generations = sum(1 for r in records if r.accepted)
    acceptance_rate = accepted_generations / max(1, len(records))

    top_runs = sorted(runs, key=lambda r: (r.best_delta_anchor, r.best_delta_full), reverse=True)[:10]
    promotion_ready = [
        r for r in runs if r.best_delta_anchor >= min_anchor_delta and r.best_delta_full >= min_full_delta
    ]
    near_miss = [r for r in runs if r.best_delta_anchor < min_anchor_delta]
    near_miss = sorted(near_miss, key=lambda r: r.best_delta_anchor, reverse=True)[:10]

    return Ledger(
        generated_at=_utc_now_iso(),
        root=str(root).replace("\\", "/"),
        total_generations=len(records),
        total_runs=len(runs),
        accepted_generations=accepted_generations,
        acceptance_rate=acceptance_rate,
        by_mode=_build_mode_summary(records),
        top_runs_by_anchor=top_runs,
        promotion_ready_runs=promotion_ready,
        near_miss_runs=near_miss,
        generation_records=records,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consolidate self-train runs into a ledger")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("data") / "sol_self_train_runs",
        help="Canonical self-train run root",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data") / "sol_self_train_runs" / "_ledger",
        help="Output directory for ledger artifacts",
    )
    parser.add_argument(
        "--min-anchor-delta",
        type=float,
        default=0.005,
        help="Promotion-ready threshold for best delta_anchor",
    )
    parser.add_argument(
        "--min-full-delta",
        type=float,
        default=0.0,
        help="Promotion-ready threshold for best delta_full",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    ledger = build_ledger(args.root, args.min_anchor_delta, args.min_full_delta)

    json_path = args.out_dir / "self_train_ledger.json"
    md_path = args.out_dir / "self_train_ledger.md"

    json_payload = asdict(ledger)
    json_payload["generation_records"] = [asdict(r) for r in ledger.generation_records]
    json_payload["top_runs_by_anchor"] = [asdict(r) for r in ledger.top_runs_by_anchor]
    json_payload["promotion_ready_runs"] = [asdict(r) for r in ledger.promotion_ready_runs]
    json_payload["near_miss_runs"] = [asdict(r) for r in ledger.near_miss_runs]

    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(ledger), encoding="utf-8")

    print(f"[self-train-consolidate] root={args.root}")
    print(f"[self-train-consolidate] generations={ledger.total_generations} runs={ledger.total_runs}")
    print(f"[self-train-consolidate] json={json_path}")
    print(f"[self-train-consolidate] md={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
