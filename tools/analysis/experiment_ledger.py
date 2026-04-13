from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict, field
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
    knowledge_domains: list[str] = field(default_factory=list)
    emergence_signals: list[str] = field(default_factory=list)
    unknown_mechanics: list[str] = field(default_factory=list)


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


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _load_json_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    return {}


def _load_optional_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    token = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
    if token in {"", "none", "null", "n_a"}:
        return ""
    return token


def _append_token(values: list[str], token: Any, *, prefix: str | None = None) -> None:
    normalized = _normalize_token(token)
    if not normalized:
        return
    text = f"{prefix}:{normalized}" if prefix else normalized
    if text not in values:
        values.append(text)


def _extract_text_tokens(text: str, mapping: dict[str, str]) -> list[str]:
    tokens: list[str] = []
    lowered = text.lower()
    for needle, label in mapping.items():
        if needle in lowered and label not in tokens:
            tokens.append(label)
    return tokens


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
            if source.startswith("_"):
                continue
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            knowledge_domains = ["policy_adaptation", "sol_manifold"]
            emergence_signals: list[str] = []
            if bool(payload.get("accepted", False)) and _safe_float(payload.get("delta_full", 0.0)) > 0.0:
                emergence_signals.append("accepted_candidate")

            unknown_mechanics: list[str] = []
            if not bool(payload.get("accepted", False)):
                unknown_mechanics.append("rejected_candidate")

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
                    knowledge_domains=knowledge_domains,
                    emergence_signals=emergence_signals,
                    unknown_mechanics=unknown_mechanics,
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
                knowledge_domains = [
                    domain
                    for metric_name, domain in {
                        "phonon_memory": "phonon_memory",
                        "thought_vibration": "thought_vibration",
                        "semantic_entanglement": "semantic_entanglement",
                        "manifold_potential": "manifold_potential",
                    }.items()
                    if metric_name in metric_means
                ]
                _append_token(knowledge_domains, best_trial.get("final_basin_label"), prefix="basin")

                primary_score = _safe_float(metric_means.get("resonance_index", 0.0))
                secondary_score = _safe_float(best_trial.get("resonance_index", 0.0))
                emergence_signals: list[str] = []
                if primary_score >= 0.6 or secondary_score >= 0.6:
                    emergence_signals.append("high_resonance")
                if int(best_trial.get("unique_basins", 0) or 0) >= 5:
                    emergence_signals.append("multi_basin")

                unknown_mechanics: list[str] = []
                if not best_trial.get("final_basin_label"):
                    unknown_mechanics.append("unidentified_basin")
                if str(payload.get("status", "")).lower() != "ok":
                    unknown_mechanics.append("run_status_not_ok")

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
                        knowledge_domains=knowledge_domains,
                        emergence_signals=emergence_signals,
                        unknown_mechanics=unknown_mechanics,
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
                knowledge_domains = [
                    domain
                    for metric_name, domain in {
                        "phonon_memory": "phonon_memory",
                        "thought_vibration": "thought_vibration",
                        "semantic_entanglement": "semantic_entanglement",
                        "manifold_potential": "manifold_potential",
                    }.items()
                    if metric_name in metric_means
                ]
                _append_token(knowledge_domains, best_trial.get("final_basin_label"), prefix="basin")

                delta_mean = _safe_float(phase1_ref.get("delta_mean_resonance", 0.0))
                delta_best = _safe_float(phase1_ref.get("delta_best_resonance", 0.0))
                emergence_signals: list[str] = []
                if _safe_float(metric_means.get("resonance_index", 0.0)) >= 0.6:
                    emergence_signals.append("high_resonance")
                if int(best_trial.get("unique_basins", 0) or 0) >= 5:
                    emergence_signals.append("multi_basin")
                if delta_mean > 0.0:
                    emergence_signals.append("phase2_gain")

                unknown_mechanics: list[str] = []
                if not best_trial.get("final_basin_label"):
                    unknown_mechanics.append("unidentified_basin")
                if delta_mean < 0.0:
                    unknown_mechanics.append("phase2_regression")
                if str(payload.get("status", "")).lower() != "ok":
                    unknown_mechanics.append("run_status_not_ok")

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
                        knowledge_domains=knowledge_domains,
                        emergence_signals=emergence_signals,
                        unknown_mechanics=unknown_mechanics,
                    )
                )
            except Exception:
                continue

    records.sort(key=lambda r: (r.experiment, r.source, r.mode, r.run_id, r.generation))
    return records


def _discover_rsi_records(rsi_root: Path) -> list[ExperimentRecord]:
    records: list[ExperimentRecord] = []
    if not rsi_root.exists():
        return records

    outcome_path = rsi_root / "outcome_ledger.jsonl"
    cycle_path = rsi_root / "cycle_log.jsonl"
    fitness_path = rsi_root / "fitness_ledger.jsonl"

    cycle_rows = _load_jsonl_rows(cycle_path)
    outcome_rows = _load_jsonl_rows(outcome_path)
    fitness_rows = _load_jsonl_rows(fitness_path)
    outcome_path_text = str(outcome_path).replace("\\", "/")
    fitness_path_text = str(fitness_path).replace("\\", "/")

    mode_by_cycle: dict[int, str] = {}
    for row in cycle_rows:
        cycle_id = int(row.get("cycle_id", 0) or 0)
        if cycle_id <= 0:
            continue
        plan_raw = row.get("plan")
        execution_raw = row.get("execution")
        plan: dict[str, Any] = plan_raw if isinstance(plan_raw, dict) else {}
        execution: dict[str, Any] = execution_raw if isinstance(execution_raw, dict) else {}
        mode = str(plan.get("mode") or execution.get("mode") or "persistent")
        mode_by_cycle[cycle_id] = mode

    fitness_by_cycle: dict[int, float] = {}
    ordered_fitness_rows: list[tuple[int, float]] = []
    for row in fitness_rows:
        cycle_id = int(row.get("cycle_id", 0) or 0)
        if cycle_id <= 0:
            continue
        fitness = _safe_float(row.get("fitness", 0.0))
        fitness_by_cycle[cycle_id] = fitness
        ordered_fitness_rows.append((cycle_id, fitness))

    seen_cycles: set[int] = set()

    for row in outcome_rows:
        cycle_id = int(row.get("cycle_id", 0) or 0)
        if cycle_id <= 0:
            continue

        pre_raw = row.get("pre")
        post_raw = row.get("post")
        delta_raw = row.get("delta")
        pre: dict[str, Any] = pre_raw if isinstance(pre_raw, dict) else {}
        post: dict[str, Any] = post_raw if isinstance(post_raw, dict) else {}
        delta: dict[str, Any] = delta_raw if isinstance(delta_raw, dict) else {}
        error = row.get("error")

        pre_fitness = _safe_float(pre.get("fitness", fitness_by_cycle.get(cycle_id, 0.0)))
        post_fitness = _safe_float(post.get("fitness", fitness_by_cycle.get(cycle_id, pre_fitness)))
        delta_fitness = _safe_float(delta.get("fitness", post_fitness - pre_fitness))
        experiments_executed = int(row.get("experiments_executed", 0) or 0)
        templates_raw = row.get("templates_planned")
        templates_planned: list[Any] = templates_raw if isinstance(templates_raw, list) else []

        if error:
            reason = str(error)
        else:
            reason = (
                f"experiments_executed={experiments_executed}; "
                f"templates_planned={len(templates_planned)}"
            )

        records.append(
            ExperimentRecord(
                experiment="rsi",
                source="legacy-local",
                mode=mode_by_cycle.get(cycle_id, "persistent"),
                run_id="rsi_engine",
                generation=cycle_id,
                accepted=not bool(error),
                metrics={
                    "delta_anchor": delta_fitness,
                    "delta_full": post_fitness,
                    "fitness_pre": pre_fitness,
                    "fitness_post": post_fitness,
                    "experiments_executed": float(experiments_executed),
                    "open_questions_delta": _safe_float(delta.get("open_q", 0.0)),
                },
                reason=reason,
                summary_path=(
                    f"{outcome_path_text}#cycle_id={cycle_id}"
                ),
                knowledge_domains=["adaptive_rsi", "open_questions"],
                emergence_signals=["fitness_gain"] if delta_fitness > 0 else [],
                unknown_mechanics=["cycle_error"] if error else [],
            )
        )
        seen_cycles.add(cycle_id)

    if not outcome_rows:
        ordered_fitness_rows.sort(key=lambda x: x[0])
        previous_fitness = 0.0
        for cycle_id, fitness in ordered_fitness_rows:
            records.append(
                ExperimentRecord(
                    experiment="rsi",
                    source="legacy-local",
                    mode=mode_by_cycle.get(cycle_id, "persistent"),
                    run_id="rsi_engine",
                    generation=cycle_id,
                    accepted=True,
                    metrics={
                        "delta_anchor": fitness - previous_fitness,
                        "delta_full": fitness,
                        "fitness_post": fitness,
                    },
                    reason="fitness_ledger_only",
                    summary_path=(
                        f"{fitness_path_text}#cycle_id={cycle_id}"
                    ),
                    knowledge_domains=["adaptive_rsi"],
                    emergence_signals=["fitness_gain"] if fitness - previous_fitness > 0 else [],
                    unknown_mechanics=[],
                )
            )
            previous_fitness = fitness
    else:
        ordered_fitness_rows.sort(key=lambda x: x[0])
        previous_fitness = 0.0
        for cycle_id, fitness in ordered_fitness_rows:
            if cycle_id in seen_cycles:
                previous_fitness = fitness
                continue
            records.append(
                ExperimentRecord(
                    experiment="rsi",
                    source="legacy-local",
                    mode=mode_by_cycle.get(cycle_id, "persistent"),
                    run_id="rsi_engine",
                    generation=cycle_id,
                    accepted=True,
                    metrics={
                        "delta_anchor": fitness - previous_fitness,
                        "delta_full": fitness,
                        "fitness_post": fitness,
                    },
                    reason="fitness_ledger_only",
                    summary_path=(
                        f"{fitness_path_text}#cycle_id={cycle_id}"
                    ),
                    knowledge_domains=["adaptive_rsi"],
                    emergence_signals=["fitness_gain"] if fitness - previous_fitness > 0 else [],
                    unknown_mechanics=[],
                )
            )
            previous_fitness = fitness

    records.sort(key=lambda r: (r.experiment, r.source, r.mode, r.run_id, r.generation))
    return records


def _discover_cortex_records(cortex_root: Path) -> list[ExperimentRecord]:
    records: list[ExperimentRecord] = []
    if not cortex_root.exists():
        return records

    emergence_keywords = {
        "emerg": "explicit_emergence",
        "threshold": "threshold_transition",
        "qualitatively change": "threshold_transition",
        "basin migration": "basin_migration",
        "topological reorganization": "topological_reorganization",
        "novel basin": "novel_basin",
        "symmetry": "symmetry_shift",
    }
    unknown_keywords = {
        "open q": "open_question",
        "unknown": "unknown_mechanics",
        "what happens": "unmapped_regime",
        "why": "causal_gap",
        "how": "mechanistic_gap",
        "not understood": "mechanistic_gap",
    }

    for summary_path in cortex_root.glob("*/summary.json"):
        try:
            session_dir = summary_path.parent
            payload = _load_json_file(summary_path)
            hypotheses = _load_optional_json_list(session_dir / "hypotheses.json")
            sanity_results = payload.get("sanity_results", [])
            sanity_rows = sanity_results if isinstance(sanity_results, list) else []
            protocols_run = int(payload.get("protocols_run", len(hypotheses)) or len(hypotheses) or 0)
            hypotheses_generated = int(payload.get("hypotheses_generated", len(hypotheses)) or len(hypotheses) or 0)
            total_steps = int(payload.get("total_steps", 0) or 0)
            anomalies_count = 0
            passing = 0
            for row in sanity_rows:
                if not isinstance(row, dict):
                    continue
                if row.get("sanity_passed"):
                    passing += 1
                anomalies = row.get("anomalies", [])
                if isinstance(anomalies, list):
                    anomalies_count += len(anomalies)
            pass_rate = passing / max(1, len(sanity_rows) or hypotheses_generated or protocols_run or 1)

            knowledge_domains: list[str] = ["sol_manifold"]
            emergence_signals: list[str] = []
            unknown_mechanics: list[str] = []

            for hypothesis in hypotheses:
                _append_token(knowledge_domains, hypothesis.get("knob"))
                source_gap_raw = hypothesis.get("source_gap")
                source_gap = source_gap_raw if isinstance(source_gap_raw, dict) else {}
                metadata_raw = source_gap.get("metadata")
                metadata = metadata_raw if isinstance(metadata_raw, dict) else {}
                _append_token(knowledge_domains, metadata.get("param"))
                injection_raw = hypothesis.get("injection")
                injection = injection_raw if isinstance(injection_raw, dict) else {}
                _append_token(knowledge_domains, injection.get("label"), prefix="injection")

                text_parts = [
                    str(hypothesis.get("question", "")),
                    str(hypothesis.get("notes", "")),
                    str(source_gap.get("description", "")),
                    str(source_gap.get("gap_type", "")),
                ]
                text = " ".join(part for part in text_parts if part).strip()
                for token in _extract_text_tokens(text, emergence_keywords):
                    _append_token(emergence_signals, token)
                for token in _extract_text_tokens(text, unknown_keywords):
                    _append_token(unknown_mechanics, token)

            if anomalies_count > 0:
                _append_token(unknown_mechanics, "observed_anomalies")
            if pass_rate >= 0.8 and protocols_run >= 3:
                _append_token(emergence_signals, "stable_replay")

            gap_types = {
                _normalize_token(
                    (hypothesis.get("source_gap") if isinstance(hypothesis.get("source_gap"), dict) else {}).get("gap_type", "")
                )
                for hypothesis in hypotheses
                if isinstance(hypothesis, dict)
            }
            gap_types.discard("")
            if payload.get("dry_run", False):
                mode = "dry_run"
            elif len(gap_types) == 1:
                mode = next(iter(gap_types))
            elif gap_types:
                mode = "mixed"
            else:
                mode = "autonomous"

            reason_parts = [
                f"protocols_run={protocols_run}",
                f"anomalies={anomalies_count}",
            ]
            if gap_types:
                reason_parts.append(f"gap_types={','.join(sorted(gap_types))}")

            records.append(
                ExperimentRecord(
                    experiment="cortex",
                    source="autonomous-session",
                    mode=mode,
                    run_id=session_dir.name,
                    generation=max(1, protocols_run or hypotheses_generated),
                    accepted=(
                        not bool(payload.get("dry_run", False))
                        and pass_rate > 0.0
                        and anomalies_count == 0
                    ),
                    metrics={
                        "delta_anchor": pass_rate,
                        "delta_full": float(protocols_run),
                        "protocols_run": float(protocols_run),
                        "hypotheses_generated": float(hypotheses_generated),
                        "total_steps": float(total_steps),
                        "anomaly_count": float(anomalies_count),
                    },
                    reason="; ".join(reason_parts),
                    summary_path=str(summary_path).replace("\\", "/"),
                    knowledge_domains=knowledge_domains,
                    emergence_signals=emergence_signals,
                    unknown_mechanics=unknown_mechanics,
                )
            )
        except Exception:
            continue

    records.sort(key=lambda r: (r.experiment, r.source, r.mode, r.run_id, r.generation))
    return records


def _discover_dream_records(dream_root: Path) -> list[ExperimentRecord]:
    records: list[ExperimentRecord] = []
    if not dream_root.exists():
        return records

    for summary_path in dream_root.glob("*/summary.json"):
        try:
            session_dir = summary_path.parent
            payload = _load_json_file(summary_path)
            dream_rows = _load_jsonl_rows(session_dir / "dream_log.jsonl")
            basin_signatures = _load_optional_json_list(session_dir / "basin_signatures.json")

            sessions_replayed = int(payload.get("sessions_replayed", 0) or 0)
            replays_run = int(payload.get("replays_run", len(dream_rows)) or len(dream_rows) or 0)
            basins_discovered = int(payload.get("basins_discovered", 0) or 0)
            basins_reinforced = int(payload.get("basins_reinforced", 0) or 0)
            basins_decayed = int(payload.get("basins_decayed", 0) or 0)

            stable_basins = 0
            recurring_mass_hashes: set[str] = set()
            seen_mass_hashes: set[str] = set()
            knowledge_domains: list[str] = ["hippocampal_replay"]
            emergence_signals: list[str] = []
            unknown_mechanics: list[str] = []

            source_sessions: set[str] = set()
            hypothesis_ids: set[str] = set()
            protocol_names: set[str] = set()

            for row in dream_rows:
                _append_token(knowledge_domains, row.get("source_session"), prefix="source_session")
                _append_token(knowledge_domains, row.get("hypothesis_id"), prefix="hypothesis")
                _append_token(knowledge_domains, row.get("protocol_name"), prefix="protocol")

                source_session = _normalize_token(row.get("source_session"))
                if source_session:
                    source_sessions.add(source_session)
                hypothesis_id = _normalize_token(row.get("hypothesis_id"))
                if hypothesis_id:
                    hypothesis_ids.add(hypothesis_id)
                protocol_name = _normalize_token(row.get("protocol_name"))
                if protocol_name:
                    protocol_names.add(protocol_name)

            for basin in basin_signatures:
                if basin.get("is_stable"):
                    stable_basins += 1
                _append_token(knowledge_domains, basin.get("source_hypothesis"), prefix="hypothesis")
                mass_hash = _normalize_token(basin.get("mass_hash"))
                if mass_hash:
                    if mass_hash in seen_mass_hashes:
                        recurring_mass_hashes.add(mass_hash)
                    seen_mass_hashes.add(mass_hash)

            if basins_discovered > 0:
                _append_token(emergence_signals, "basin_discovery")
            if basins_reinforced > 0:
                _append_token(emergence_signals, "basin_reinforcement")
            if stable_basins > 0:
                _append_token(emergence_signals, "stable_basin")
            if len(source_sessions) > 1:
                _append_token(emergence_signals, "cross_session_replay")
            if len(hypothesis_ids) > 1:
                _append_token(emergence_signals, "multi_hypothesis_replay")
            if recurring_mass_hashes:
                _append_token(emergence_signals, "recurring_basin_signature")

            if basins_decayed > 0:
                _append_token(unknown_mechanics, "basin_decay")
            if replays_run > 0 and stable_basins == 0:
                _append_token(unknown_mechanics, "unstable_replay")
            if replays_run > 0 and not dream_rows:
                _append_token(unknown_mechanics, "missing_dream_log")
            if replays_run > 0 and not basin_signatures:
                _append_token(unknown_mechanics, "missing_basin_signatures")

            reason_parts = [
                f"sessions_replayed={sessions_replayed}",
                f"replays_run={replays_run}",
                f"stable_basins={stable_basins}",
            ]
            if source_sessions:
                reason_parts.append(f"source_sessions={len(source_sessions)}")
            if hypothesis_ids:
                reason_parts.append(f"hypotheses={len(hypothesis_ids)}")

            records.append(
                ExperimentRecord(
                    experiment="dream",
                    source="hippocampus-nightly",
                    mode="dream_cycle",
                    run_id=session_dir.name,
                    generation=1,
                    accepted=replays_run > 0 and (basins_discovered > 0 or basins_reinforced > 0 or stable_basins > 0),
                    metrics={
                        "delta_anchor": stable_basins / max(1, replays_run),
                        "delta_full": float(replays_run),
                        "sessions_replayed": float(sessions_replayed),
                        "replays_run": float(replays_run),
                        "basins_discovered": float(basins_discovered),
                        "basins_reinforced": float(basins_reinforced),
                        "basins_decayed": float(basins_decayed),
                        "stable_basins": float(stable_basins),
                        "source_sessions": float(len(source_sessions)),
                        "hypotheses": float(len(hypothesis_ids)),
                        "protocols": float(len(protocol_names)),
                    },
                    reason="; ".join(reason_parts),
                    summary_path=str(summary_path).replace("\\", "/"),
                    knowledge_domains=knowledge_domains,
                    emergence_signals=emergence_signals,
                    unknown_mechanics=unknown_mechanics,
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

    def summarize_annotations(field_name: str) -> dict[str, dict[str, Any]]:
        summary: dict[str, dict[str, Any]] = {}
        for record in records:
            for value in getattr(record, field_name, []) or []:
                entry = summary.setdefault(
                    value,
                    {
                        "records": 0,
                        "accepted_generations": 0,
                        "experiments": set(),
                    },
                )
                entry["records"] += 1
                entry["accepted_generations"] += int(record.accepted)
                entry["experiments"].add(record.experiment)

        return {
            key: {
                "records": value["records"],
                "accepted_generations": value["accepted_generations"],
                "experiments": sorted(value["experiments"]),
            }
            for key, value in sorted(summary.items(), key=lambda item: (-item[1]["records"], item[0]))
        }

    return {
        "generated_at": _utc_now_iso(),
        "records": len(records),
        "runs": len(run_summaries),
        "experiments": by_experiment,
        "knowledge_domains": summarize_annotations("knowledge_domains"),
        "potential_emergence": summarize_annotations("emergence_signals"),
        "unknown_mechanics": summarize_annotations("unknown_mechanics"),
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

    def render_annotation_section(title: str, key: str) -> None:
        entries = index.get(key, {})
        if not entries:
            return
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Signal | Records | Accepted | Experiments |")
        lines.append("|---|---:|---:|---|")
        for signal, stats in entries.items():
            lines.append(
                f"| {signal} | {stats['records']} | {stats['accepted_generations']} | {', '.join(stats['experiments'])} |"
            )
        lines.append("")

    render_annotation_section("Knowledge Domains", "knowledge_domains")
    render_annotation_section("Potential Emergence", "potential_emergence")
    render_annotation_section("Unknown Mechanics", "unknown_mechanics")

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
        "--rsi-root",
        type=Path,
        default=Path("data") / "rsi",
        help="Root directory for RSI ledger files",
    )
    parser.add_argument(
        "--cortex-root",
        type=Path,
        default=Path("data") / "cortex_sessions",
        help="Root directory for cortex autonomous session summaries",
    )
    parser.add_argument(
        "--dream-root",
        type=Path,
        default=Path("data") / "dream_sessions",
        help="Root directory for hippocampal dream session summaries",
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
    records.extend(_discover_rsi_records(args.rsi_root))
    records.extend(_discover_cortex_records(args.cortex_root))
    records.extend(_discover_dream_records(args.dream_root))
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
