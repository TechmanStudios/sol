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
class DreamFinding:
    """A cross-night dream finding suitable for promotion to solKnowledge."""

    finding_class: str
    finding_id: str
    description: str
    nights: list[str] = field(default_factory=list)
    source_sessions: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    is_stable: bool = False
    promote_to_canonical: bool = False


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


def _discover_dream_records(dream_root: Path) -> list[ExperimentRecord]:
    """Adapter for nightly hippocampus dream sessions under data/dream_sessions/DS-*.

    Each dream session directory contains:
      - summary.json          (aggregate counts + memory_stats)
      - dream_log.jsonl       (per-replay rows: source_session, hypothesis_id, score, basins_found)
      - basin_signatures.json (basin attractors observed during replay)

    One ExperimentRecord is emitted per dream session.
    """
    records: list[ExperimentRecord] = []
    if not dream_root.exists():
        return records

    for summary_path in sorted(dream_root.glob("DS-*/summary.json")):
        try:
            session_dir = summary_path.parent
            session_id = session_dir.name
            payload = _load_json_file(summary_path)
            dream_log = _load_jsonl_rows(session_dir / "dream_log.jsonl")
            basins = _load_optional_json_list(session_dir / "basin_signatures.json")

            sessions_replayed = int(payload.get("sessions_replayed", 0) or 0)
            replays_run = int(payload.get("replays_run", len(dream_log)) or len(dream_log) or 0)
            basins_discovered = int(payload.get("basins_discovered", 0) or 0)
            basins_reinforced = int(payload.get("basins_reinforced", 0) or 0)
            basins_decayed = int(payload.get("basins_decayed", 0) or 0)

            memory_stats_raw = payload.get("memory_stats")
            memory_stats = memory_stats_raw if isinstance(memory_stats_raw, dict) else {}

            # Replay log aggregations (sources, scores, yield-per-hypothesis).
            source_sessions: list[str] = []
            scores: list[float] = []
            basins_found_per_replay: list[float] = []
            hypothesis_ids: list[str] = []
            for row in dream_log:
                src = row.get("source_session")
                if isinstance(src, str) and src and src not in source_sessions:
                    source_sessions.append(src)
                hyp = row.get("hypothesis_id")
                if isinstance(hyp, str) and hyp and hyp not in hypothesis_ids:
                    hypothesis_ids.append(hyp)
                score = _safe_float(row.get("score"))
                if score:
                    scores.append(score)
                bf = _safe_float(row.get("basins_found"))
                if bf:
                    basins_found_per_replay.append(bf)

            score_mean = sum(scores) / len(scores) if scores else 0.0
            score_max = max(scores) if scores else 0.0
            replay_yield_mean = (
                sum(basins_found_per_replay) / len(basins_found_per_replay)
                if basins_found_per_replay
                else 0.0
            )

            # Basin-signature aggregations.
            stable_basins = [b for b in basins if b.get("is_stable")]
            unique_mass_hashes = sorted({
                str(b.get("mass_hash"))
                for b in basins
                if b.get("mass_hash") is not None
            })
            unique_rho_ids = sorted({
                int(b.get("rhoMaxId"))
                for b in basins
                if isinstance(b.get("rhoMaxId"), (int, float))
            })
            unique_top_node_sets = {
                tuple(sorted(int(n) for n in b.get("top_nodes", []) if isinstance(n, (int, float))))
                for b in basins
                if isinstance(b.get("top_nodes"), list)
            }
            unique_top_node_sets.discard(())
            entropy_bands = sorted({
                round(_safe_float(b.get("entropy_band")), 3)
                for b in basins
                if b.get("entropy_band") is not None
            })

            # Dominant rhoMaxId by occurrence count.
            rho_counts: dict[int, int] = {}
            for b in basins:
                rid = b.get("rhoMaxId")
                if isinstance(rid, (int, float)):
                    rho_counts[int(rid)] = rho_counts.get(int(rid), 0) + 1
            dominant_rho_id = max(rho_counts.items(), key=lambda kv: kv[1])[0] if rho_counts else 0
            dominant_rho_share = (
                rho_counts.get(dominant_rho_id, 0) / max(1, len(basins)) if basins else 0.0
            )

            # Knowledge domain annotations.
            knowledge_domains: list[str] = ["sol_manifold", "dream_replay"]
            for src in source_sessions:
                _append_token(knowledge_domains, src, prefix="source")
            for mh in unique_mass_hashes:
                _append_token(knowledge_domains, mh, prefix="basin")
            if dominant_rho_id:
                _append_token(knowledge_domains, dominant_rho_id, prefix="rho")
            for band in entropy_bands:
                _append_token(knowledge_domains, f"{band:.2f}".replace(".", "p"), prefix="entropy_band")

            # Dream-specific emergence / unknown-mechanics signals.
            emergence_signals: list[str] = []
            unknown_mechanics: list[str] = []

            if basins_discovered > 0:
                _append_token(emergence_signals, "new_basin_discovered")
            if basins_reinforced > 0:
                _append_token(emergence_signals, "basin_reinforced")
            if basins_reinforced > 0 and basins_reinforced >= basins_decayed:
                _append_token(emergence_signals, "reinforcement_dominant")
            if stable_basins:
                _append_token(emergence_signals, "stable_basin_present")
            if dominant_rho_share >= 0.6 and len(basins) >= 5:
                _append_token(emergence_signals, "dominant_rho_persistent")
            if len(source_sessions) >= 2 and len(unique_mass_hashes) <= max(1, len(source_sessions)):
                # Few basins shared across many source sessions ⇒ candidate transfer signature.
                _append_token(emergence_signals, "cross_source_basin_transfer")
            if score_max > 0 and score_mean > 0 and replay_yield_mean > 0:
                # Strong replay scores AND non-zero yield ⇒ replay-yield-vs-score signal.
                if score_mean >= 0.5 and replay_yield_mean >= 1.0:
                    _append_token(emergence_signals, "high_replay_yield")

            if basins_decayed > 0 and basins_decayed > basins_reinforced + basins_discovered:
                _append_token(unknown_mechanics, "decay_dominant")
            if replays_run > 0 and not basins:
                _append_token(unknown_mechanics, "no_basins_observed")
            if len(unique_top_node_sets) >= max(3, len(basins) // 2) and len(basins) >= 4:
                _append_token(unknown_mechanics, "top_node_set_drift")
            if len(entropy_bands) >= 3:
                _append_token(unknown_mechanics, "entropy_band_drift")

            # Mode classification.
            if payload.get("dry_run", False):
                mode = "dry_run"
            elif basins_reinforced > 0 and basins_discovered == 0:
                mode = "reinforcement"
            elif basins_discovered > 0 and basins_reinforced == 0:
                mode = "discovery"
            elif basins_discovered > 0 and basins_reinforced > 0:
                mode = "mixed_consolidation"
            elif basins_decayed > 0 and basins_discovered == 0 and basins_reinforced == 0:
                mode = "decay_only"
            else:
                mode = "nightly_consolidation"

            primary_source = source_sessions[0] if source_sessions else "unknown-source"

            reason_parts = [
                f"sessions_replayed={sessions_replayed}",
                f"replays_run={replays_run}",
                f"new={basins_discovered}",
                f"reinforced={basins_reinforced}",
                f"decayed={basins_decayed}",
                f"unique_basins={len(unique_mass_hashes)}",
            ]

            accepted = (
                not bool(payload.get("dry_run", False))
                and replays_run > 0
                and (basins_discovered + basins_reinforced) > 0
            )

            records.append(
                ExperimentRecord(
                    experiment="dream",
                    source=primary_source,
                    mode=mode,
                    run_id=session_id,
                    generation=max(1, replays_run),
                    accepted=accepted,
                    metrics={
                        # Map onto the shared metric names so the existing index
                        # aggregations remain meaningful.
                        "delta_anchor": float(basins_reinforced + basins_discovered),
                        "delta_full": score_max,
                        "sessions_replayed": float(sessions_replayed),
                        "replays_run": float(replays_run),
                        "basins_discovered": float(basins_discovered),
                        "basins_reinforced": float(basins_reinforced),
                        "basins_decayed": float(basins_decayed),
                        "unique_basins": float(len(unique_mass_hashes)),
                        "unique_rho_ids": float(len(unique_rho_ids)),
                        "unique_top_node_sets": float(len(unique_top_node_sets)),
                        "stable_basins": float(len(stable_basins)),
                        "dominant_rho_share": float(dominant_rho_share),
                        "replay_score_mean": float(score_mean),
                        "replay_score_max": float(score_max),
                        "replay_yield_mean": float(replay_yield_mean),
                        "memory_node_count": float(memory_stats.get("node_count", 0) or 0),
                        "memory_avg_confidence": float(memory_stats.get("avg_confidence", 0.0) or 0.0),
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


def _load_dream_session_details(dream_root: Path) -> list[dict[str, Any]]:
    """Load lightweight per-night detail dicts for cross-night aggregation."""
    details: list[dict[str, Any]] = []
    if not dream_root.exists():
        return details

    for summary_path in sorted(dream_root.glob("DS-*/summary.json")):
        try:
            session_dir = summary_path.parent
            payload = _load_json_file(summary_path)
            dream_log = _load_jsonl_rows(session_dir / "dream_log.jsonl")
            basins = _load_optional_json_list(session_dir / "basin_signatures.json")

            mass_hashes = sorted({
                str(b.get("mass_hash"))
                for b in basins
                if b.get("mass_hash") is not None
            })
            stable_mass_hashes = sorted({
                str(b.get("mass_hash"))
                for b in basins
                if b.get("mass_hash") is not None and b.get("is_stable")
            })
            rho_ids = sorted({
                int(b.get("rhoMaxId"))
                for b in basins
                if isinstance(b.get("rhoMaxId"), (int, float))
            })
            top_node_sets = sorted({
                tuple(sorted(int(n) for n in b.get("top_nodes", []) if isinstance(n, (int, float))))
                for b in basins
                if isinstance(b.get("top_nodes"), list) and b.get("top_nodes")
            })
            entropy_bands = sorted({
                round(_safe_float(b.get("entropy_band")), 3)
                for b in basins
                if b.get("entropy_band") is not None
            })

            source_sessions: list[str] = []
            scores: list[float] = []
            for row in dream_log:
                src = row.get("source_session")
                if isinstance(src, str) and src and src not in source_sessions:
                    source_sessions.append(src)
                score = _safe_float(row.get("score"))
                if score:
                    scores.append(score)

            # Per-source max basins_found and score (replay yield per source session).
            source_replay: dict[str, dict[str, float]] = {}
            for row in dream_log:
                src = row.get("source_session")
                if not isinstance(src, str) or not src:
                    continue
                bucket = source_replay.setdefault(src, {"score": 0.0, "yield": 0.0, "replays": 0.0})
                bucket["score"] = max(bucket["score"], _safe_float(row.get("score")))
                bucket["yield"] = max(bucket["yield"], _safe_float(row.get("basins_found")))
                bucket["replays"] += 1.0

            # Per-source mass_hash mapping (which basins were yielded by each source).
            source_to_mass: dict[str, set[str]] = {}
            for b in basins:
                src = b.get("source_hypothesis")
                # source_hypothesis is just an id like H-001 in this dataset; we don't
                # have per-basin source-session attribution. Track at the hypothesis level.
                if isinstance(src, str) and b.get("mass_hash") is not None:
                    source_to_mass.setdefault(src, set()).add(str(b.get("mass_hash")))

            details.append({
                "session_id": session_dir.name,
                "completed_at": payload.get("completed_at", ""),
                "sessions_replayed": int(payload.get("sessions_replayed", 0) or 0),
                "replays_run": int(payload.get("replays_run", len(dream_log)) or len(dream_log) or 0),
                "basins_discovered": int(payload.get("basins_discovered", 0) or 0),
                "basins_reinforced": int(payload.get("basins_reinforced", 0) or 0),
                "basins_decayed": int(payload.get("basins_decayed", 0) or 0),
                "mass_hashes": mass_hashes,
                "stable_mass_hashes": stable_mass_hashes,
                "rho_ids": rho_ids,
                "top_node_sets": [list(t) for t in top_node_sets],
                "entropy_bands": entropy_bands,
                "source_sessions": source_sessions,
                "score_mean": sum(scores) / len(scores) if scores else 0.0,
                "score_max": max(scores) if scores else 0.0,
                "source_replay": source_replay,
                "hypothesis_to_mass": {k: sorted(v) for k, v in source_to_mass.items()},
            })
        except Exception:
            continue

    details.sort(key=lambda d: d.get("session_id", ""))
    return details


def _aggregate_dream_findings(
    details: list[dict[str, Any]],
    *,
    min_nights: int = 2,
    min_sources: int = 2,
    canonical_min_nights: int = 3,
) -> list[DreamFinding]:
    """Build cross-night dream findings prioritized for transfer-oriented hypotheses.

    Findings are flagged ``is_stable`` when observed across at least
    ``min_nights`` distinct nights or ``min_sources`` source cortex sessions, and
    ``promote_to_canonical`` when they additionally clear ``canonical_min_nights``
    nights so single-night anomalies stay as follow-up candidates rather than
    canonical claims.
    """
    findings: list[DreamFinding] = []
    if not details:
        return findings

    # 1. Recurring basin identity by mass_hash across nights.
    basin_to_nights: dict[str, list[str]] = {}
    basin_to_sources: dict[str, set[str]] = {}
    basin_stable_nights: dict[str, list[str]] = {}
    for d in details:
        sid = d["session_id"]
        for mh in d.get("mass_hashes", []):
            basin_to_nights.setdefault(mh, []).append(sid)
            basin_to_sources.setdefault(mh, set()).update(d.get("source_sessions", []))
        for mh in d.get("stable_mass_hashes", []):
            basin_stable_nights.setdefault(mh, []).append(sid)

    for mh, nights in sorted(basin_to_nights.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        sources = sorted(basin_to_sources.get(mh, set()))
        stable_n = basin_stable_nights.get(mh, [])
        is_stable = len(set(nights)) >= min_nights or len(sources) >= min_sources
        promote = (
            len(set(nights)) >= canonical_min_nights
            and len(stable_n) >= min_nights
        )
        findings.append(
            DreamFinding(
                finding_class="recurring_basin",
                finding_id=f"basin:{mh}",
                description=(
                    f"Basin mass_hash={mh} observed on {len(set(nights))} night(s) "
                    f"across {len(sources)} source cortex session(s); "
                    f"stable on {len(stable_n)} night(s)."
                ),
                nights=sorted(set(nights)),
                source_sessions=sources,
                metrics={
                    "night_count": float(len(set(nights))),
                    "source_count": float(len(sources)),
                    "stable_night_count": float(len(stable_n)),
                },
                is_stable=is_stable,
                promote_to_canonical=promote,
            )
        )

    # 2. Recurring source cortex sessions across nights (which sources keep
    #    re-emerging as informative replay seeds).
    source_to_nights: dict[str, list[str]] = {}
    source_to_scores: dict[str, list[float]] = {}
    source_to_yield: dict[str, list[float]] = {}
    for d in details:
        sid = d["session_id"]
        replay = d.get("source_replay", {})
        for src in d.get("source_sessions", []):
            source_to_nights.setdefault(src, []).append(sid)
            bucket = replay.get(src, {})
            if bucket.get("score"):
                source_to_scores.setdefault(src, []).append(float(bucket["score"]))
            if bucket.get("yield"):
                source_to_yield.setdefault(src, []).append(float(bucket["yield"]))

    for src, nights in sorted(source_to_nights.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        scores = source_to_scores.get(src, [])
        yields = source_to_yield.get(src, [])
        is_stable = len(set(nights)) >= min_nights
        promote = len(set(nights)) >= canonical_min_nights
        findings.append(
            DreamFinding(
                finding_class="recurring_source",
                finding_id=f"source:{src}",
                description=(
                    f"Source cortex session {src} replayed on {len(set(nights))} night(s) "
                    f"with mean replay score {(sum(scores)/len(scores)) if scores else 0.0:.3f}."
                ),
                nights=sorted(set(nights)),
                source_sessions=[src],
                metrics={
                    "night_count": float(len(set(nights))),
                    "score_mean": float(sum(scores) / len(scores)) if scores else 0.0,
                    "score_max": float(max(scores)) if scores else 0.0,
                    "yield_mean": float(sum(yields) / len(yields)) if yields else 0.0,
                },
                is_stable=is_stable,
                promote_to_canonical=promote,
            )
        )

    # 3. Replay-yield → stable-attractor predictivity.
    #    Compare per-night mean replay score against the proportion of stable
    #    basins observed that night, and report a simple Pearson-like coefficient.
    paired_x: list[float] = []
    paired_y: list[float] = []
    for d in details:
        score = float(d.get("score_mean", 0.0))
        unique_basins = len(d.get("mass_hashes", []))
        stable_basins = len(d.get("stable_mass_hashes", []))
        if unique_basins == 0:
            continue
        paired_x.append(score)
        paired_y.append(stable_basins / max(1, unique_basins))

    if len(paired_x) >= max(2, min_nights):
        n = len(paired_x)
        mean_x = sum(paired_x) / n
        mean_y = sum(paired_y) / n
        num = sum((paired_x[i] - mean_x) * (paired_y[i] - mean_y) for i in range(n))
        den_x = sum((paired_x[i] - mean_x) ** 2 for i in range(n)) ** 0.5
        den_y = sum((paired_y[i] - mean_y) ** 2 for i in range(n)) ** 0.5
        corr = num / (den_x * den_y) if den_x > 0 and den_y > 0 else 0.0
        findings.append(
            DreamFinding(
                finding_class="replay_yield_correlation",
                finding_id="replay_score_vs_stable_share",
                description=(
                    f"Across {n} night(s), Pearson(replay_score_mean, stable_basin_share)={corr:.3f}."
                ),
                nights=[d["session_id"] for d in details if d.get("mass_hashes")],
                source_sessions=[],
                metrics={
                    "night_count": float(n),
                    "correlation": float(corr),
                    "score_mean": float(mean_x),
                    "stable_share_mean": float(mean_y),
                },
                is_stable=n >= min_nights and abs(corr) >= 0.4,
                promote_to_canonical=n >= canonical_min_nights and abs(corr) >= 0.5,
            )
        )

    # 4. Reinforcement / decay balance across nights.
    total_disc = sum(d.get("basins_discovered", 0) for d in details)
    total_reinf = sum(d.get("basins_reinforced", 0) for d in details)
    total_decay = sum(d.get("basins_decayed", 0) for d in details)
    nights_total = len(details)
    if nights_total >= min_nights:
        balance_nights = sum(
            1
            for d in details
            if (d.get("basins_reinforced", 0) + d.get("basins_discovered", 0))
            >= d.get("basins_decayed", 0)
        )
        findings.append(
            DreamFinding(
                finding_class="reinforcement_decay_balance",
                finding_id="reinforcement_vs_decay",
                description=(
                    f"Across {nights_total} night(s): discovered={total_disc}, "
                    f"reinforced={total_reinf}, decayed={total_decay}; "
                    f"reinforcement≥decay on {balance_nights}/{nights_total} nights."
                ),
                nights=[d["session_id"] for d in details],
                source_sessions=[],
                metrics={
                    "night_count": float(nights_total),
                    "basins_discovered": float(total_disc),
                    "basins_reinforced": float(total_reinf),
                    "basins_decayed": float(total_decay),
                    "reinforcement_balance_nights": float(balance_nights),
                    "reinforcement_balance_share": float(balance_nights) / float(nights_total),
                },
                is_stable=nights_total >= min_nights,
                promote_to_canonical=(
                    nights_total >= canonical_min_nights
                    and (balance_nights / nights_total) >= 0.66
                ),
            )
        )

    # 5. Top-node-set persistence: same top-node tuple recurring across nights.
    top_to_nights: dict[tuple[int, ...], list[str]] = {}
    for d in details:
        sid = d["session_id"]
        for tns in d.get("top_node_sets", []):
            key = tuple(int(x) for x in tns)
            top_to_nights.setdefault(key, []).append(sid)
    for key, nights in sorted(top_to_nights.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(set(nights)) < min_nights:
            continue
        findings.append(
            DreamFinding(
                finding_class="top_node_set_persistence",
                finding_id="top_nodes:" + "_".join(str(n) for n in key),
                description=(
                    f"Top-node set {list(key)} recurred on {len(set(nights))} night(s)."
                ),
                nights=sorted(set(nights)),
                source_sessions=[],
                metrics={
                    "night_count": float(len(set(nights))),
                    "set_size": float(len(key)),
                },
                is_stable=True,
                promote_to_canonical=len(set(nights)) >= canonical_min_nights,
            )
        )

    # 6. Entropy-band persistence.
    band_to_nights: dict[float, list[str]] = {}
    for d in details:
        for band in d.get("entropy_bands", []):
            band_to_nights.setdefault(float(band), []).append(d["session_id"])
    for band, nights in sorted(band_to_nights.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(set(nights)) < min_nights:
            continue
        findings.append(
            DreamFinding(
                finding_class="entropy_band_persistence",
                finding_id=f"entropy_band:{band:.3f}",
                description=(
                    f"Entropy band {band:.3f} present on {len(set(nights))} night(s)."
                ),
                nights=sorted(set(nights)),
                source_sessions=[],
                metrics={
                    "night_count": float(len(set(nights))),
                    "entropy_band": float(band),
                },
                is_stable=True,
                promote_to_canonical=len(set(nights)) >= canonical_min_nights,
            )
        )

    # 7. Basin turnover: nights where the dominant basin shifts vs the previous night.
    if nights_total >= max(2, min_nights):
        prev_dominant: str | None = None
        turnover_nights: list[str] = []
        shifts: list[tuple[str, str | None, str]] = []
        for d in details:
            mhs = d.get("mass_hashes", [])
            dominant = mhs[0] if mhs else None
            if prev_dominant is not None and dominant is not None and dominant != prev_dominant:
                turnover_nights.append(d["session_id"])
                shifts.append((d["session_id"], prev_dominant, dominant))
            if dominant is not None:
                prev_dominant = dominant
        findings.append(
            DreamFinding(
                finding_class="basin_turnover",
                finding_id="dominant_basin_turnover",
                description=(
                    f"Dominant basin shifted on {len(turnover_nights)}/{nights_total} nights."
                ),
                nights=turnover_nights,
                source_sessions=[],
                metrics={
                    "night_count": float(nights_total),
                    "turnover_nights": float(len(turnover_nights)),
                    "turnover_share": (
                        float(len(turnover_nights)) / float(nights_total)
                    ) if nights_total else 0.0,
                },
                is_stable=nights_total >= min_nights,
                promote_to_canonical=False,
            )
        )

    return findings


def _render_dream_ledger_markdown(
    details: list[dict[str, Any]],
    findings: list[DreamFinding],
) -> str:
    """Compact human-readable nightly dream ledger.

    Highlights the three triage buckets called out in the task:
    "new stable basin", "shifted dominant basin", and
    "possible information-transfer mechanism".
    """
    lines: list[str] = []
    lines.append("# Dream Ledger")
    lines.append("")
    lines.append(f"Generated: {_utc_now_iso()}")
    lines.append(f"Nights analyzed: {len(details)} | Cross-night findings: {len(findings)}")
    lines.append("")

    if details:
        lines.append("## Latest nights")
        lines.append("")
        lines.append(
            "| Night | Sources | Replays | New | Reinf | Decay | Unique basins | Stable | Score (mean / max) |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
        for d in details[-10:][::-1]:
            lines.append(
                f"| {d['session_id']} | {len(d.get('source_sessions', []))} | "
                f"{d.get('replays_run', 0)} | {d.get('basins_discovered', 0)} | "
                f"{d.get('basins_reinforced', 0)} | {d.get('basins_decayed', 0)} | "
                f"{len(d.get('mass_hashes', []))} | {len(d.get('stable_mass_hashes', []))} | "
                f"{d.get('score_mean', 0.0):.3f} / {d.get('score_max', 0.0):.3f} |"
            )
        lines.append("")

    def _section(title: str, classes: tuple[str, ...]) -> None:
        rows = [f for f in findings if f.finding_class in classes]
        if not rows:
            return
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Finding | Class | Stable | Promote | Nights | Sources | Description |")
        lines.append("|---|---|:-:|:-:|---:|---:|---|")
        for f in rows[:20]:
            lines.append(
                f"| `{f.finding_id}` | {f.finding_class} | "
                f"{'✓' if f.is_stable else '·'} | {'★' if f.promote_to_canonical else '·'} | "
                f"{len(f.nights)} | {len(f.source_sessions)} | {f.description} |"
            )
        lines.append("")

    _section(
        "New / recurring stable basins",
        ("recurring_basin", "top_node_set_persistence", "entropy_band_persistence"),
    )
    _section("Shifted dominant basin", ("basin_turnover",))
    _section(
        "Possible information-transfer mechanisms",
        ("recurring_source", "replay_yield_correlation", "reinforcement_decay_balance"),
    )

    return "\n".join(lines)


def _render_dream_candidates_markdown(findings: list[DreamFinding]) -> str:
    """Markdown for solKnowledge/working: candidate / follow-up findings."""
    lines: list[str] = []
    lines.append("# Dream Findings — Candidates")
    lines.append("")
    lines.append(f"Generated: {_utc_now_iso()}")
    lines.append("")
    lines.append(
        "Single-night anomalies and findings not yet stable across multiple nights "
        "or source sessions. These are follow-up candidates, not canonical claims."
    )
    lines.append("")
    lines.append("| Finding | Class | Nights | Sources | Description |")
    lines.append("|---|---|---:|---:|---|")
    for f in findings:
        if f.promote_to_canonical:
            continue
        lines.append(
            f"| `{f.finding_id}` | {f.finding_class} | {len(f.nights)} | "
            f"{len(f.source_sessions)} | {f.description} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_dream_consolidated_markdown(findings: list[DreamFinding]) -> str:
    """Markdown for solKnowledge/consolidated: promoted findings only."""
    lines: list[str] = []
    lines.append("# Dream Findings — Consolidated")
    lines.append("")
    lines.append(f"Generated: {_utc_now_iso()}")
    lines.append("")
    lines.append(
        "Findings stable across multiple nights or source cortex sessions, eligible "
        "as proof-packet candidates. Each row links back to the originating dream "
        "session ids under `data/dream_sessions/`."
    )
    lines.append("")
    promoted = [f for f in findings if f.promote_to_canonical]
    if not promoted:
        lines.append("_No findings have cleared the multi-night promotion threshold yet._")
        lines.append("")
        return "\n".join(lines)
    lines.append("| Finding | Class | Nights | Sources | Description | Originating sessions |")
    lines.append("|---|---|---:|---:|---|---|")
    for f in promoted:
        sessions = ", ".join(f"`data/dream_sessions/{n}`" for n in f.nights[:5])
        if len(f.nights) > 5:
            sessions += f", … (+{len(f.nights) - 5} more)"
        lines.append(
            f"| `{f.finding_id}` | {f.finding_class} | {len(f.nights)} | "
            f"{len(f.source_sessions)} | {f.description} | {sessions} |"
        )
    lines.append("")
    return "\n".join(lines)


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
        help="Root directory for nightly hippocampus dream sessions",
    )
    parser.add_argument(
        "--solknowledge-root",
        type=Path,
        default=Path("solKnowledge"),
        help=(
            "Root for solKnowledge promotion of dream findings "
            "(working/ for candidates, consolidated/ for promoted findings)"
        ),
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

    # Cross-night dream-specific outputs.
    dream_details = _load_dream_session_details(args.dream_root)
    dream_findings = _aggregate_dream_findings(dream_details)
    dream_findings_json = args.out_dir / "dream_findings.json"
    dream_ledger_md = args.out_dir / "dream_ledger.md"
    dream_findings_json.write_text(
        json.dumps(
            {
                "generated_at": _utc_now_iso(),
                "nights": len(dream_details),
                "findings": [asdict(f) for f in dream_findings],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    dream_ledger_md.write_text(
        _render_dream_ledger_markdown(dream_details, dream_findings),
        encoding="utf-8",
    )

    # Promote stable findings to solKnowledge; keep single-night anomalies as
    # follow-up candidates rather than canonical claims.
    if dream_details:
        sk_root = args.solknowledge_root
        working_dir = sk_root / "working"
        consolidated_dir = sk_root / "consolidated"
        working_dir.mkdir(parents=True, exist_ok=True)
        consolidated_dir.mkdir(parents=True, exist_ok=True)
        (working_dir / "dream_findings_candidates.md").write_text(
            _render_dream_candidates_markdown(dream_findings), encoding="utf-8"
        )
        (consolidated_dir / "dream_findings.md").write_text(
            _render_dream_consolidated_markdown(dream_findings), encoding="utf-8"
        )

    print(f"[experiment-ledger] records={len(records)} runs={len(run_summaries)}")
    print(f"[experiment-ledger] dream_nights={len(dream_details)} dream_findings={len(dream_findings)}")
    print(f"[experiment-ledger] records_jsonl={records_jsonl}")
    print(f"[experiment-ledger] index_json={index_json}")
    print(f"[experiment-ledger] ledger_md={ledger_md}")
    print(f"[experiment-ledger] dream_findings_json={dream_findings_json}")
    print(f"[experiment-ledger] dream_ledger_md={dream_ledger_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
