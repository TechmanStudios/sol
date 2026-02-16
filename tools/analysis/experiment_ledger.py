from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ExperimentRecord:
    experiment: str
    source: str
    mode: str
    run_id: str
    generation: int
    accepted: bool
    metrics: dict[str, float]
    reason: str
    summary_path: str


@dataclass
class ExperimentRunSummary:
    experiment: str
    source: str
    mode: str
    run_id: str
    generations: int
    accepted_generations: int
    acceptance_rate: float
    best_anchor_delta: float
    best_full_delta: float
    latest_anchor_delta: float
    latest_full_delta: float
    latest_reason: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _discover_self_train_records(root: Path) -> list[ExperimentRecord]:
    records: list[ExperimentRecord] = []

    if not root.exists():
        return records

    for summary_path in root.glob("*/*/*/gen_*/summary.json"):
        try:
            rel = summary_path.relative_to(root)
            parts = rel.parts
            if len(parts) < 5:
                continue

            source, mode, run_id = parts[0], parts[1], parts[2]
            payload = json.loads(summary_path.read_text(encoding="utf-8"))

            records.append(
                ExperimentRecord(
                    experiment="self_train",
                    source=source,
                    mode=mode,
                    run_id=run_id,
                    generation=int(payload.get("generation", 0)),
                    accepted=bool(payload.get("accepted", False)),
                    metrics={
                        "delta_anchor": _safe_float(payload.get("delta_anchor", 0.0)),
                        "delta_full": _safe_float(payload.get("delta_full", 0.0)),
                    },
                    reason=str(payload.get("reason", "")),
                    summary_path=str(summary_path).replace("\\", "/"),
                )
            )
        except Exception:
            continue

    records.sort(key=lambda r: (r.experiment, r.source, r.mode, r.run_id, r.generation))
    return records


def _discover_resonance_records(phase1_root: Path, phase2_root: Path) -> list[ExperimentRecord]:
    records: list[ExperimentRecord] = []

    # Phase 1 resonance sweeps
    if phase1_root.exists():
        for summary_path in phase1_root.glob("*/summary.json"):
            try:
                run_id = summary_path.parent.name
                payload = json.loads(summary_path.read_text(encoding="utf-8"))
                best_trial = payload.get("best_trial", {})
                metric_means = payload.get("metric_means", {})

                primary_score = _safe_float(metric_means.get("resonance_index", 0.0))
                secondary_score = _safe_float(best_trial.get("resonance_index", 0.0))

                records.append(
                    ExperimentRecord(
                        experiment="resonance",
                        source="legacy-local",
                        mode="phase1",
                        run_id=run_id,
                        generation=1,
                        accepted=str(payload.get("status", "")).lower() == "ok",
                        metrics={
                            "delta_anchor": primary_score,
                            "delta_full": secondary_score,
                            "mean_resonance": primary_score,
                            "best_resonance": secondary_score,
                        },
                        reason=f"status={payload.get('status', 'unknown')}",
                        summary_path=str(summary_path).replace("\\", "/"),
                    )
                )
            except Exception:
                continue

    # Phase 2 focused resonance sweeps
    if phase2_root.exists():
        for summary_path in phase2_root.glob("*/summary.json"):
            try:
                run_id = summary_path.parent.name
                payload = json.loads(summary_path.read_text(encoding="utf-8"))
                best_trial = payload.get("best_trial", {})
                metric_means = payload.get("metric_means", {})
                phase1_ref = payload.get("phase1_reference", {})

                delta_mean = _safe_float(phase1_ref.get("delta_mean_resonance", 0.0))
                delta_best = _safe_float(phase1_ref.get("delta_best_resonance", 0.0))

                records.append(
                    ExperimentRecord(
                        experiment="resonance",
                        source="legacy-local",
                        mode="phase2",
                        run_id=run_id,
                        generation=1,
                        accepted=(
                            str(payload.get("status", "")).lower() == "ok"
                            and delta_mean >= 0.0
                        ),
                        metrics={
                            "delta_anchor": delta_mean,
                            "delta_full": delta_best,
                            "mean_resonance": _safe_float(metric_means.get("resonance_index", 0.0)),
                            "best_resonance": _safe_float(best_trial.get("resonance_index", 0.0)),
                        },
                        reason=(
                            f"status={payload.get('status', 'unknown')}; "
                            f"delta_mean={delta_mean:.4f}; delta_best={delta_best:.4f}"
                        ),
                        summary_path=str(summary_path).replace("\\", "/"),
                    )
                )
            except Exception:
                continue

    records.sort(key=lambda r: (r.experiment, r.source, r.mode, r.run_id, r.generation))
    return records


def _aggregate_runs(records: list[ExperimentRecord]) -> list[ExperimentRunSummary]:
    grouped: dict[tuple[str, str, str, str], list[ExperimentRecord]] = {}
    for record in records:
        key = (record.experiment, record.source, record.mode, record.run_id)
        grouped.setdefault(key, []).append(record)

    summaries: list[ExperimentRunSummary] = []
    for (experiment, source, mode, run_id), rows in grouped.items():
        rows.sort(key=lambda r: r.generation)
        latest = rows[-1]
        accepted_count = sum(1 for r in rows if r.accepted)

        anchor_vals = [r.metrics.get("delta_anchor", 0.0) for r in rows]
        full_vals = [r.metrics.get("delta_full", 0.0) for r in rows]

        summaries.append(
            ExperimentRunSummary(
                experiment=experiment,
                source=source,
                mode=mode,
                run_id=run_id,
                generations=len(rows),
                accepted_generations=accepted_count,
                acceptance_rate=accepted_count / max(1, len(rows)),
                best_anchor_delta=max(anchor_vals) if anchor_vals else 0.0,
                best_full_delta=max(full_vals) if full_vals else 0.0,
                latest_anchor_delta=latest.metrics.get("delta_anchor", 0.0),
                latest_full_delta=latest.metrics.get("delta_full", 0.0),
                latest_reason=latest.reason,
            )
        )

    summaries.sort(key=lambda s: (s.experiment, s.source, s.mode, s.run_id))
    return summaries


def _build_index(records: list[ExperimentRecord], run_summaries: list[ExperimentRunSummary]) -> dict[str, Any]:
    by_experiment: dict[str, dict[str, Any]] = {}

    for experiment in sorted({r.experiment for r in records}):
        exp_records = [r for r in records if r.experiment == experiment]
        exp_runs = [r for r in run_summaries if r.experiment == experiment]

        accepted = sum(1 for r in exp_records if r.accepted)

        by_mode: dict[str, dict[str, Any]] = {}
        for mode in sorted({r.mode for r in exp_records}):
            rows = [r for r in exp_records if r.mode == mode]
            by_mode[mode] = {
                "generations": len(rows),
                "runs": len({(r.source, r.run_id) for r in rows}),
                "accepted_generations": sum(1 for r in rows if r.accepted),
                "acceptance_rate": sum(1 for r in rows if r.accepted) / max(1, len(rows)),
                "best_anchor_delta": max((r.metrics.get("delta_anchor", 0.0) for r in rows), default=0.0),
                "best_full_delta": max((r.metrics.get("delta_full", 0.0) for r in rows), default=0.0),
            }

        by_experiment[experiment] = {
            "runs": len(exp_runs),
            "generations": len(exp_records),
            "accepted_generations": accepted,
            "acceptance_rate": accepted / max(1, len(exp_records)),
            "top_runs_by_anchor": [asdict(r) for r in sorted(exp_runs, key=lambda x: x.best_anchor_delta, reverse=True)[:10]],
            "by_mode": by_mode,
        }

    return {
        "generated_at": _utc_now_iso(),
        "records": len(records),
        "runs": len(run_summaries),
        "experiments": by_experiment,
    }


def _render_markdown(index: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Experiment Ledger")
    lines.append("")
    lines.append(f"Generated: {index['generated_at']}")
    lines.append(f"Records: {index['records']} | Runs: {index['runs']}")
    lines.append("")

    for experiment, payload in index.get("experiments", {}).items():
        lines.append(f"## {experiment}")
        lines.append("")
        lines.append(
            f"- Runs: {payload['runs']} | Generations: {payload['generations']} | Accepted: {payload['accepted_generations']} | Acceptance: {payload['acceptance_rate']:.2%}"
        )
        lines.append("")
        lines.append("### Modes")
        lines.append("")
        lines.append("| Mode | Runs | Gens | Accepted | Acceptance | Best dA | Best dF |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for mode, stats in payload.get("by_mode", {}).items():
            lines.append(
                f"| {mode} | {stats['runs']} | {stats['generations']} | {stats['accepted_generations']} | {stats['acceptance_rate']:.2%} | {stats['best_anchor_delta']:.4f} | {stats['best_full_delta']:.4f} |"
            )
        lines.append("")
        lines.append("### Top Runs")
        lines.append("")
        lines.append("| Source | Mode | Run | Gens | Best dA | Latest dA | Latest dF |")
        lines.append("|---|---|---|---:|---:|---:|---:|")
        for run in payload.get("top_runs_by_anchor", []):
            lines.append(
                f"| {run['source']} | {run['mode']} | {run['run_id']} | {run['generations']} | {run['best_anchor_delta']:.4f} | {run['latest_anchor_delta']:.4f} | {run['latest_full_delta']:.4f} |"
            )
        lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build generalized experiment ledger index")
    parser.add_argument(
        "--self-train-root",
        type=Path,
        default=Path("data") / "sol_self_train_runs",
        help="Root directory for self_train canonical runs",
    )
    parser.add_argument(
        "--resonance-phase1-root",
        type=Path,
        default=Path("data") / "thinking_engine_resonance",
        help="Root directory for resonance phase1 runs",
    )
    parser.add_argument(
        "--resonance-phase2-root",
        type=Path,
        default=Path("data") / "thinking_engine_resonance_phase2",
        help="Root directory for resonance phase2 runs",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data") / "experiment_ledger",
        help="Output directory for generalized ledger artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    records.extend(_discover_self_train_records(args.self_train_root))
    records.extend(_discover_resonance_records(args.resonance_phase1_root, args.resonance_phase2_root))
    records.sort(key=lambda r: (r.experiment, r.source, r.mode, r.run_id, r.generation))
    run_summaries = _aggregate_runs(records)
    index = _build_index(records, run_summaries)

    records_jsonl = args.out_dir / "records.jsonl"
    index_json = args.out_dir / "index.json"
    ledger_md = args.out_dir / "ledger.md"

    with records_jsonl.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    index_json.write_text(json.dumps(index, indent=2), encoding="utf-8")
    ledger_md.write_text(_render_markdown(index), encoding="utf-8")

    print(f"[experiment-ledger] records={len(records)} runs={len(run_summaries)}")
    print(f"[experiment-ledger] records_jsonl={records_jsonl}")
    print(f"[experiment-ledger] index_json={index_json}")
    print(f"[experiment-ledger] ledger_md={ledger_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
