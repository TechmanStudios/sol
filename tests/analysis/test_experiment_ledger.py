from __future__ import annotations

import json
import sys
from pathlib import Path


_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_ANALYSIS_DIR = _SOL_ROOT / "tools" / "analysis"

if str(_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS_DIR))

from experiment_ledger import (
    _aggregate_runs,
    _build_index,
    _discover_cortex_records,
    _discover_resonance_records,
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
