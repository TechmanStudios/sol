from __future__ import annotations

import json
import sys
from pathlib import Path


_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_ANALYSIS_DIR = _SOL_ROOT / "tools" / "analysis"

if str(_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS_DIR))

from experiment_ledger import (
    _aggregate_dream_findings,
    _aggregate_runs,
    _build_index,
    _discover_cortex_records,
    _discover_dream_records,
    _discover_resonance_records,
    _load_dream_session_details,
)


def test_discover_cortex_records_extracts_domains_and_signals(tmp_path):
    cortex_root = tmp_path / "cortex_sessions"
    session_dir = cortex_root / "CX-20260326-000000"
    session_dir.mkdir(parents=True)

    (session_dir / "summary.json").write_text(
        json.dumps(
            {
                "session_id": "CX-20260326-000000",
                "completed_at": "2026-03-26T00:00:00Z",
                "protocols_run": 4,
                "hypotheses_generated": 2,
                "total_steps": 1200,
                "sanity_results": [
                    {"hypothesis": "H-001", "sanity_passed": True, "anomalies": []},
                    {"hypothesis": "H-002", "sanity_passed": True, "anomalies": []},
                ],
                "dry_run": False,
            }
        ),
        encoding="utf-8",
    )
    (session_dir / "hypotheses.json").write_text(
        json.dumps(
            [
                {
                    "id": "H-001",
                    "question": "At what damping threshold does basin migration signal topological reorganization?",
                    "knob": "damping",
                    "injection": {"label": "grail", "amount": 50},
                    "source_gap": {
                        "gap_type": "open_question",
                        "description": "Open Q: Does basin migration reveal unknown mechanics?",
                        "metadata": {"param": "damping"},
                    },
                },
                {
                    "id": "H-002",
                    "question": "How does psi diffusion affect emergence on the sol manifold?",
                    "knob": "psi_diffusion",
                    "source_gap": {
                        "gap_type": "unexplored_param",
                        "description": "Investigate potential emergence signatures in the unexplored regime",
                        "metadata": {"param": "psi_diffusion"},
                    },
                },
            ]
        ),
        encoding="utf-8",
    )

    records = _discover_cortex_records(cortex_root)

    assert len(records) == 1
    record = records[0]
    assert record.experiment == "cortex"
    assert record.mode == "mixed"
    assert record.accepted is True
    assert record.metrics["delta_anchor"] == 1.0
    assert "sol_manifold" in record.knowledge_domains
    assert "damping" in record.knowledge_domains
    assert "psi_diffusion" in record.knowledge_domains
    assert "injection:grail" in record.knowledge_domains
    assert "threshold_transition" in record.emergence_signals
    assert "basin_migration" in record.emergence_signals
    assert "topological_reorganization" in record.emergence_signals
    assert "stable_replay" in record.emergence_signals
    assert "open_question" in record.unknown_mechanics
    assert "unknown_mechanics" in record.unknown_mechanics
    assert "mechanistic_gap" in record.unknown_mechanics


def test_build_index_summarizes_new_domain_and_signal_annotations(tmp_path):
    resonance_phase1 = tmp_path / "thinking_engine_resonance"
    resonance_phase2 = tmp_path / "thinking_engine_resonance_phase2"
    run_dir = resonance_phase1 / "20260326_000000"
    run_dir.mkdir(parents=True)
    resonance_phase2.mkdir(parents=True)

    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "metric_means": {
                    "phonon_memory": 0.9,
                    "thought_vibration": 0.8,
                    "semantic_entanglement": 0.7,
                    "manifold_potential": 0.6,
                    "resonance_index": 0.65,
                },
                "best_trial": {
                    "resonance_index": 0.72,
                    "unique_basins": 7,
                    "final_basin_label": "christic",
                },
            }
        ),
        encoding="utf-8",
    )

    records = _discover_resonance_records(resonance_phase1, resonance_phase2)
    summaries = _aggregate_runs(records)
    index = _build_index(records, summaries)

    assert index["experiments"]["resonance"]["runs"] == 1
    assert index["knowledge_domains"]["phonon_memory"]["records"] == 1
    assert index["knowledge_domains"]["basin:christic"]["experiments"] == ["resonance"]
    assert index["potential_emergence"]["high_resonance"]["records"] == 1
    assert index["potential_emergence"]["multi_basin"]["accepted_generations"] == 1
    assert index["unknown_mechanics"] == {}

def _write_dream_session(
    dream_root: Path,
    session_id: str,
    *,
    summary: dict,
    log_rows: list[dict],
    basins: list[dict],
) -> None:
    session_dir = dream_root / session_id
    session_dir.mkdir(parents=True)
    (session_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with (session_dir / "dream_log.jsonl").open("w", encoding="utf-8") as f:
        for row in log_rows:
            f.write(json.dumps(row) + "\n")
    (session_dir / "basin_signatures.json").write_text(json.dumps(basins), encoding="utf-8")


def _basin(mass_hash: str, rho: int, top_nodes: list[int], *, is_stable: bool = True,
           entropy_band: float = 0.6, source_hyp: str = "H-001") -> dict:
    return {
        "rhoMaxId": rho,
        "top_nodes": top_nodes,
        "entropy_band": entropy_band,
        "mass": 42.0,
        "mass_hash": mass_hash,
        "activeCount": 100,
        "knob_value": 0.05,
        "rep": 0,
        "source_hypothesis": source_hyp,
        "stability": 3,
        "is_stable": is_stable,
    }


def test_discover_dream_records_emits_one_record_per_night_with_signals(tmp_path):
    dream_root = tmp_path / "dream_sessions"
    dream_root.mkdir()
    _write_dream_session(
        dream_root,
        "DS-20260420-050000",
        summary={
            "session_id": "DS-20260420-050000",
            "completed_at": "2026-04-20T05:00:00Z",
            "sessions_replayed": 2,
            "replays_run": 4,
            "basins_discovered": 3,
            "basins_reinforced": 2,
            "basins_decayed": 1,
            "memory_stats": {"node_count": 30, "avg_confidence": 0.6},
        },
        log_rows=[
            {"source_session": "CX-A", "hypothesis_id": "H-001", "score": 0.9, "basins_found": 5},
            {"source_session": "CX-A", "hypothesis_id": "H-002", "score": 0.9, "basins_found": 2},
            {"source_session": "CX-B", "hypothesis_id": "H-001", "score": 0.7, "basins_found": 4},
            {"source_session": "CX-B", "hypothesis_id": "H-002", "score": 0.7, "basins_found": 3},
        ],
        basins=[
            _basin("aaaa", 1090, [1090, 1081, 1083]),
            _basin("aaaa", 1090, [1090, 1081, 1083]),
            _basin("aaaa", 1090, [1090, 1081, 1083]),
            _basin("bbbb", 1090, [1090, 1081, 1084]),
            _basin("cccc", 1090, [1090, 1082, 1085], entropy_band=0.7),
        ],
    )

    records = _discover_dream_records(dream_root)

    assert len(records) == 1
    rec = records[0]
    assert rec.experiment == "dream"
    assert rec.run_id == "DS-20260420-050000"
    assert rec.mode == "mixed_consolidation"
    assert rec.accepted is True
    assert rec.metrics["basins_discovered"] == 3.0
    assert rec.metrics["basins_reinforced"] == 2.0
    assert rec.metrics["unique_basins"] == 3.0
    assert rec.metrics["replay_score_max"] == 0.9
    assert "dream_replay" in rec.knowledge_domains
    assert "source:cx_a" in rec.knowledge_domains
    assert "basin:aaaa" in rec.knowledge_domains
    assert "rho:1090" in rec.knowledge_domains
    assert "new_basin_discovered" in rec.emergence_signals
    assert "basin_reinforced" in rec.emergence_signals
    assert "reinforcement_dominant" in rec.emergence_signals
    assert "stable_basin_present" in rec.emergence_signals
    assert "dominant_rho_persistent" in rec.emergence_signals
    assert "high_replay_yield" in rec.emergence_signals


def test_discover_dream_records_flags_decay_only_mode(tmp_path):
    dream_root = tmp_path / "dream_sessions"
    dream_root.mkdir()
    _write_dream_session(
        dream_root,
        "DS-20260420-060000",
        summary={
            "session_id": "DS-20260420-060000",
            "completed_at": "2026-04-20T06:00:00Z",
            "sessions_replayed": 1,
            "replays_run": 1,
            "basins_discovered": 0,
            "basins_reinforced": 0,
            "basins_decayed": 5,
        },
        log_rows=[
            {"source_session": "CX-Z", "hypothesis_id": "H-001", "score": 0.1, "basins_found": 0},
        ],
        basins=[],
    )

    records = _discover_dream_records(dream_root)
    assert len(records) == 1
    rec = records[0]
    assert rec.mode == "decay_only"
    assert rec.accepted is False
    assert "decay_dominant" in rec.unknown_mechanics
    assert "no_basins_observed" in rec.unknown_mechanics


def test_aggregate_dream_findings_promotes_only_multi_night_recurrence(tmp_path):
    dream_root = tmp_path / "dream_sessions"
    dream_root.mkdir()
    # Three nights: basin "aaaa" recurs on all three from different cortex sources;
    # basin "bbbb" only appears on one night.
    for idx, (sid, sources) in enumerate([
        ("DS-20260418-050000", ["CX-A", "CX-B"]),
        ("DS-20260419-050000", ["CX-B", "CX-C"]),
        ("DS-20260420-050000", ["CX-C", "CX-D"]),
    ]):
        log_rows = [
            {"source_session": s, "hypothesis_id": "H-001", "score": 0.6, "basins_found": 3}
            for s in sources
        ]
        basins = [_basin("aaaa", 1090, [1090, 1081, 1083])]
        if idx == 0:
            basins.append(_basin("bbbb", 1, [1, 2, 3]))
        _write_dream_session(
            dream_root,
            sid,
            summary={
                "session_id": sid,
                "completed_at": f"2026-04-{18 + idx}T05:00:00Z",
                "sessions_replayed": len(sources),
                "replays_run": len(log_rows),
                "basins_discovered": 1,
                "basins_reinforced": 1,
                "basins_decayed": 0,
            },
            log_rows=log_rows,
            basins=basins,
        )

    details = _load_dream_session_details(dream_root)
    findings = _aggregate_dream_findings(details)

    by_id = {f.finding_id: f for f in findings}

    # Recurring basin "aaaa" appears in 3 nights / 4 sources ⇒ promote.
    aaaa = by_id["basin:aaaa"]
    assert aaaa.is_stable is True
    assert aaaa.promote_to_canonical is True
    assert len(aaaa.nights) == 3
    assert len(aaaa.source_sessions) == 4

    # Single-night basin "bbbb" must NOT be promoted to canonical.
    bbbb = by_id["basin:bbbb"]
    assert bbbb.promote_to_canonical is False

    # Recurring source CX-B appears on 2 nights ⇒ stable but not canonical (need 3).
    src_b = by_id["source:CX-B"]
    assert src_b.is_stable is True
    assert src_b.promote_to_canonical is False

    # Reinforcement/decay balance finding is always present once min_nights met.
    balance = by_id["reinforcement_vs_decay"]
    assert balance.is_stable is True
    assert balance.metrics["basins_reinforced"] == 3.0
    assert balance.metrics["basins_decayed"] == 0.0

    # Top-node-set persistence emitted only when set recurs on ≥2 nights.
    persistent_top = by_id["top_nodes:1081_1083_1090"]
    assert persistent_top.is_stable is True
    assert len(persistent_top.nights) == 3

    # Basin turnover finding present (dominant basin is "aaaa" all three nights).
    turnover = by_id["dominant_basin_turnover"]
    assert turnover.metrics["turnover_nights"] == 0.0
