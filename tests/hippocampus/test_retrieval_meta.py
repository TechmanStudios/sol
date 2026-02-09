"""
Tests for retrieval.py and meta_learner.py.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from memory_store import (
    MemoryNode, MemoryEdge, save_memory_graph, write_trace, compact,
)


# ======================================================================
# Retrieval — MemoryQuery
# ======================================================================

class TestMemoryQuery:
    def _seed(self, tmp_data):
        """Create a memory graph with tagged nodes for querying."""
        mg = {
            "meta": {"version": 1, "last_compacted": "", "trace_count": 0},
            "nodes": [
                {
                    "id": 1000, "label": "basin:82", "group": "memory",
                    "confidence": 0.8, "tags": ["damping", "rhoMax:82", "basin"],
                    "source_session": "CX-A",
                },
                {
                    "id": 1001, "label": "basin:1", "group": "memory",
                    "confidence": 0.4, "tags": ["c_press", "rhoMax:1"],
                    "source_session": "CX-B",
                },
            ],
            "edges": [
                {"from_id": 1000, "to_id": 82, "w0": 0.18, "kind": "memory"},
                {"from_id": 1001, "to_id": 1, "w0": 0.15, "kind": "memory"},
            ],
            "id_counter": 1002,
        }
        save_memory_graph(mg)

    def _seed_meta_log(self, tmp_data):
        """Create a meta-learning log."""
        log_path = tmp_data["root"] / "data" / "meta_learning_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entries = [
            {"session_id": "CX-A", "template": "threshold_scan",
             "gap_type": "unpromoted", "insight_score": 0.8,
             "param_region": {"damping": [0.01, 0.05, 0.1]}},
            {"session_id": "CX-B", "template": "parameter_sweep",
             "gap_type": "unexplored_param", "insight_score": 0.3,
             "param_region": {"c_press": [0.05, 0.1, 0.2]}},
        ]
        with open(log_path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def test_query_parameter_match(self, tmp_data, core_graph_path, monkeypatch):
        self._seed(tmp_data)
        import retrieval
        monkeypatch.setattr(retrieval, "_SOL_ROOT", tmp_data["root"])
        monkeypatch.setattr(retrieval, "_CONFIG_PATH", tmp_data["config"])

        # Patch load_memory_graph to use our tmp data
        import memory_store as ms
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_data["memory_graph"])

        from retrieval import MemoryQuery
        mq = MemoryQuery()
        results = mq.query_parameter("damping")
        assert len(results) >= 1
        assert results[0].confidence == 0.8

    def test_query_parameter_no_match(self, tmp_data, core_graph_path, monkeypatch):
        self._seed(tmp_data)
        import retrieval, memory_store as ms
        monkeypatch.setattr(retrieval, "_SOL_ROOT", tmp_data["root"])
        monkeypatch.setattr(retrieval, "_CONFIG_PATH", tmp_data["config"])
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_data["memory_graph"])

        from retrieval import MemoryQuery
        mq = MemoryQuery()
        results = mq.query_parameter("nonexistent_param")
        assert len(results) == 0

    def test_query_basin(self, tmp_data, core_graph_path, monkeypatch):
        self._seed(tmp_data)
        import retrieval, memory_store as ms
        monkeypatch.setattr(retrieval, "_SOL_ROOT", tmp_data["root"])
        monkeypatch.setattr(retrieval, "_CONFIG_PATH", tmp_data["config"])
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_data["memory_graph"])

        from retrieval import MemoryQuery
        mq = MemoryQuery()
        results = mq.query_basin(82)
        assert len(results) >= 1

    def test_query_experiment_history(self, tmp_data, monkeypatch):
        self._seed(tmp_data)
        self._seed_meta_log(tmp_data)
        import retrieval, memory_store as ms
        monkeypatch.setattr(retrieval, "_SOL_ROOT", tmp_data["root"])
        monkeypatch.setattr(retrieval, "_CONFIG_PATH", tmp_data["config"])
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_data["memory_graph"])

        from retrieval import MemoryQuery
        mq = MemoryQuery()
        history = mq.query_experiment_history(template="threshold_scan")
        assert len(history) == 1
        assert history[0]["session_id"] == "CX-A"

    def test_query_novel_regions(self, tmp_data, monkeypatch):
        self._seed(tmp_data)
        self._seed_meta_log(tmp_data)
        import retrieval, memory_store as ms
        monkeypatch.setattr(retrieval, "_SOL_ROOT", tmp_data["root"])
        monkeypatch.setattr(retrieval, "_CONFIG_PATH", tmp_data["config"])
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_data["memory_graph"])

        from retrieval import MemoryQuery
        mq = MemoryQuery()
        novel = mq.query_novel_regions("damping", known_values=[0.01, 0.1])
        assert isinstance(novel, list)
        # Should suggest midpoints between 0.01 and 0.1
        if novel:
            assert all(isinstance(v, float) for v in novel)

    def test_enrich_gap(self, tmp_data, monkeypatch):
        self._seed(tmp_data)
        import retrieval, memory_store as ms
        monkeypatch.setattr(retrieval, "_SOL_ROOT", tmp_data["root"])
        monkeypatch.setattr(retrieval, "_CONFIG_PATH", tmp_data["config"])
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_data["memory_graph"])

        from retrieval import MemoryQuery
        mq = MemoryQuery()
        gap = {
            "gap_type": "unpromoted",
            "description": "Sweep damping across range",
            "priority": 2,
        }
        enriched = mq.enrich_gap(gap)
        assert "memory_findings" in enriched
        assert "memory_context" in enriched
        # Original gap fields preserved
        assert enriched["gap_type"] == "unpromoted"

    def test_augment_hypothesis(self, tmp_data, monkeypatch):
        self._seed(tmp_data)
        import retrieval, memory_store as ms
        monkeypatch.setattr(retrieval, "_SOL_ROOT", tmp_data["root"])
        monkeypatch.setattr(retrieval, "_CONFIG_PATH", tmp_data["config"])
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_data["memory_graph"])

        from retrieval import MemoryQuery
        mq = MemoryQuery()
        hyp = {
            "id": "H-001",
            "template": "parameter_sweep",
            "knob": "damping",
            "knob_values": [0.01, 0.1],
            "falsifiers": ["mass should conserve"],
        }
        augmented = mq.augment_hypothesis(hyp)
        assert augmented.get("memory_augmented") is True
        assert len(augmented["falsifiers"]) > 1  # memory-informed added

    def test_memory_summary(self, tmp_data, monkeypatch):
        self._seed(tmp_data)
        import retrieval, memory_store as ms
        monkeypatch.setattr(retrieval, "_SOL_ROOT", tmp_data["root"])
        monkeypatch.setattr(retrieval, "_CONFIG_PATH", tmp_data["config"])
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_data["memory_graph"])

        from retrieval import MemoryQuery
        mq = MemoryQuery()
        summary = mq.memory_summary()
        assert "Memory nodes: 2" in summary


# ======================================================================
# Meta-Learner
# ======================================================================

class TestMetaLearner:
    def _patch(self, tmp_data, monkeypatch):
        import meta_learner
        log_path = tmp_data["root"] / "data" / "meta_learning_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(meta_learner, "_META_LOG", log_path)
        monkeypatch.setattr(meta_learner, "_CONFIG_PATH", tmp_data["config"])

    def test_record(self, tmp_data, monkeypatch):
        self._patch(tmp_data, monkeypatch)
        from meta_learner import MetaLearner
        ml = MetaLearner()
        hyp = {"id": "H-001", "template": "threshold_scan",
               "knob": "damping", "source_gap": {"gap_type": "unpromoted"}}
        interp = {"sanity_passed": True, "proof_packet_promoted": True}
        entry = ml.record("CX-TEST", hyp, interp)
        assert entry["session_id"] == "CX-TEST"
        assert entry["template"] == "threshold_scan"
        assert entry["insight_score"] > 0

    def test_template_scores_empty(self, tmp_data, monkeypatch):
        self._patch(tmp_data, monkeypatch)
        from meta_learner import MetaLearner
        ml = MetaLearner()
        scores = ml.template_scores()
        assert scores == {}

    def test_template_scores_with_data(self, tmp_data, monkeypatch):
        self._patch(tmp_data, monkeypatch)
        from meta_learner import MetaLearner
        ml = MetaLearner()
        # Record several experiments
        for i in range(5):
            hyp = {"id": f"H-{i}", "template": "threshold_scan",
                   "knob": "damping", "source_gap": {"gap_type": "unpromoted"}}
            interp = {"sanity_passed": True, "proof_packet_promoted": i % 2 == 0}
            ml.record(f"CX-{i}", hyp, interp)
        scores = ml.template_scores()
        assert "threshold_scan" in scores
        assert 0 <= scores["threshold_scan"] <= 1

    def test_gap_type_scores(self, tmp_data, monkeypatch):
        self._patch(tmp_data, monkeypatch)
        from meta_learner import MetaLearner
        ml = MetaLearner()
        for i in range(3):
            hyp = {"id": f"H-{i}", "template": "parameter_sweep",
                   "knob": "c_press", "source_gap": {"gap_type": "unexplored_param"}}
            ml.record(f"CX-{i}", hyp, {"sanity_passed": True})
        scores = ml.gap_type_scores()
        assert "unexplored_param" in scores

    def test_suggest_template(self, tmp_data, monkeypatch):
        self._patch(tmp_data, monkeypatch)
        from meta_learner import MetaLearner
        ml = MetaLearner()
        for i in range(10):
            hyp = {"id": f"H-{i}", "template": "threshold_scan",
                   "knob": "damping", "source_gap": {"gap_type": "unpromoted"}}
            ml.record(f"CX-{i}", hyp,
                      {"sanity_passed": True, "proof_packet_promoted": True})
        gap = {"gap_type": "unpromoted"}
        suggestion = ml.suggest_template(gap)
        assert isinstance(suggestion, (str, type(None)))

    def test_cold_regions(self, tmp_data, monkeypatch):
        self._patch(tmp_data, monkeypatch)
        from meta_learner import MetaLearner
        ml = MetaLearner()
        # Record one experiment — everything else is "cold"
        hyp = {"id": "H-1", "template": "threshold_scan",
               "knob": "damping", "knob_values": [0.01],
               "source_gap": {"gap_type": "unpromoted"}}
        ml.record("CX-1", hyp, {"sanity_passed": True})
        cold = ml.cold_regions()
        assert isinstance(cold, list)

    def test_report(self, tmp_data, monkeypatch):
        self._patch(tmp_data, monkeypatch)
        from meta_learner import MetaLearner
        ml = MetaLearner()
        report = ml.report()
        assert "Meta-Learning Report" in report

    def test_insight_score_sanity_fail(self, tmp_data, monkeypatch):
        self._patch(tmp_data, monkeypatch)
        from meta_learner import compute_insight_score
        score = compute_insight_score({"sanity_passed": False})
        assert score == 0.0

    def test_insight_score_proof_packet(self, tmp_data, monkeypatch):
        self._patch(tmp_data, monkeypatch)
        from meta_learner import compute_insight_score
        score = compute_insight_score(
            {"sanity_passed": True, "proof_packet_promoted": True})
        assert score >= 0.9
