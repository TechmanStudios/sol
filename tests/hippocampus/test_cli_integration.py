"""
CLI smoke tests and end-to-end integration tests.

Integration tests verify:
- Full cycle: add_finding → compact → overlay → engine runs → core unchanged
- Core immutability: SHA256 of default_graph.json is stable
- CLI entry points: status, compact, meta print without error
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


# ======================================================================
# Core Immutability
# ======================================================================

_KNOWN_SHA256 = "b9800d5313886818c7c1980829e1ca5da7d63d9e2218e36c020df80db19b06fb"


class TestCoreImmutability:
    """The sacred default_graph.json must never change."""

    def test_sha256_matches(self, core_graph_path):
        """Hash of default_graph.json must equal the frozen constant."""
        data = core_graph_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        assert digest == _KNOWN_SHA256, (
            f"Core graph SHA256 mismatch!\n"
            f"  Expected: {_KNOWN_SHA256}\n"
            f"  Got:      {digest}\n"
            "  ⚠️  The sacred graph has been modified — this is forbidden."
        )

    def test_node_count(self, core_graph):
        assert len(core_graph["rawNodes"]) == 140

    def test_edge_count(self, core_graph):
        assert len(core_graph["rawEdges"]) == 845

    def test_no_memory_group_in_core(self, core_graph):
        """Core graph must never contain group='memory' nodes."""
        for n in core_graph["rawNodes"]:
            assert n.get("group") != "memory", (
                f"Node {n['id']} has group='memory' in the core graph — forbidden"
            )

    def test_core_unchanged_after_overlay_ops(self, tmp_data, core_graph_path, monkeypatch):
        """
        Run overlay operations, then verify core graph is byte-identical.
        """
        import memory_store as ms
        from memory_overlay import MemoryOverlay

        before_hash = hashlib.sha256(core_graph_path.read_bytes()).hexdigest()

        overlay = MemoryOverlay()
        overlay.add_finding(
            label="test_finding",
            session_id="CX-IMMUTABILITY",
            hypothesis_id="H-000",
            tags=["test"],
            confidence=0.5,
            connected_core_ids=[1, 2, 3],
        )

        # Create and run engine
        engine = overlay.create_engine()
        engine.inject("grail", 50)
        for _ in range(100):
            engine.step(dt=0.12, c_press=0.1, damping=0.2)

        after_hash = hashlib.sha256(core_graph_path.read_bytes()).hexdigest()
        assert before_hash == after_hash, "Core graph was MODIFIED during overlay operations!"


# ======================================================================
# Integration: Full Cycle
# ======================================================================

class TestFullCycleIntegration:
    """End-to-end: add_finding → compact → overlay → engine → verify."""

    def test_finding_survives_compact(self, tmp_data, monkeypatch):
        from memory_store import compact, load_memory_graph
        from memory_overlay import MemoryOverlay

        overlay = MemoryOverlay()
        overlay.add_finding(
            label="integration_test",
            session_id="CX-INT",
            hypothesis_id="H-INT",
            tags=["integration", "damping"],
            confidence=0.75,
            connected_core_ids=[82],
        )

        compact()
        mg = load_memory_graph()

        assert len(mg["nodes"]) == 1
        assert mg["nodes"][0]["label"] == "integration_test"
        assert mg["nodes"][0]["confidence"] == 0.75
        assert mg["nodes"][0]["group"] == "memory"
        assert mg["nodes"][0]["id"] >= 1000

    def test_overlay_engine_includes_memory(self, tmp_data, monkeypatch):
        from memory_store import compact
        from memory_overlay import MemoryOverlay

        overlay = MemoryOverlay()
        overlay.add_finding(
            label="engine_test_node",
            session_id="CX-ENG",
            hypothesis_id="H-ENG",
            tags=["engine_test"],
            confidence=0.8,
            connected_core_ids=[1],
        )
        compact()

        # Create engine from overlay
        overlay2 = MemoryOverlay()
        engine = overlay2.create_engine()
        metrics = engine.compute_metrics()

        # Should have 140 core + 1 memory = 141 nodes
        states = engine.get_node_states()
        assert len(states) == 141

    def test_reinforce_increases_confidence(self, tmp_data, monkeypatch):
        from memory_store import compact, load_memory_graph
        from memory_overlay import MemoryOverlay

        overlay = MemoryOverlay()
        overlay.add_finding(
            label="reinforce_test",
            session_id="CX-R1",
            hypothesis_id="H-R1",
            tags=["reinforce"],
            confidence=0.5,
            connected_core_ids=[1],
        )
        compact()

        # Reinforce
        mg = load_memory_graph()
        node_id = mg["nodes"][0]["id"]
        overlay2 = MemoryOverlay()
        overlay2.reinforce(node_id, "CX-R2", confidence_boost=0.15)
        compact()

        mg2 = load_memory_graph()
        new_conf = mg2["nodes"][0]["confidence"]
        assert new_conf > 0.5

    def test_decay_decreases_confidence(self, tmp_data, monkeypatch):
        from memory_store import compact, load_memory_graph
        from memory_overlay import MemoryOverlay

        overlay = MemoryOverlay()
        overlay.add_finding(
            label="decay_test",
            session_id="CX-D1",
            hypothesis_id="H-D1",
            tags=["decay"],
            confidence=0.8,
            connected_core_ids=[1],
        )
        compact()

        mg = load_memory_graph()
        node_id = mg["nodes"][0]["id"]
        overlay2 = MemoryOverlay()
        overlay2.decay(node_id, "CX-D2")
        compact()

        mg2 = load_memory_graph()
        new_conf = mg2["nodes"][0]["confidence"]
        assert new_conf < 0.8

    def test_meta_learner_records_across_sessions(self, tmp_data, monkeypatch):
        import meta_learner as ml_mod
        log_path = tmp_data["root"] / "data" / "meta_learning_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ml_mod, "_META_LOG", log_path)
        monkeypatch.setattr(ml_mod, "_CONFIG_PATH", tmp_data["config"])

        from meta_learner import MetaLearner
        ml = MetaLearner()

        # Record multiple experiments
        for i in range(5):
            hyp = {"id": f"H-{i}", "template": "threshold_scan",
                   "knob": "damping", "source_gap": {"gap_type": "unpromoted"}}
            interp = {"sanity_passed": True, "proof_packet_promoted": i < 3}
            ml.record(f"CX-{i}", hyp, interp)

        scores = ml.template_scores()
        assert "threshold_scan" in scores
        report = ml.report()
        assert "Meta-Learning Report" in report


# ======================================================================
# CLI Smoke Tests (subprocess)
# ======================================================================

_CLI_PATH = Path(__file__).resolve().parent.parent.parent / "tools" / "sol-hippocampus" / "cli.py"
_PYTHON = sys.executable


class TestCLISmoke:
    """Run CLI commands via subprocess to verify they don't crash."""

    @pytest.mark.skipif(not _CLI_PATH.exists(), reason="CLI not found")
    def test_status(self):
        result = subprocess.run(
            [_PYTHON, str(_CLI_PATH), "status"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "Hippocampus" in result.stdout or "Core" in result.stdout

    @pytest.mark.skipif(not _CLI_PATH.exists(), reason="CLI not found")
    def test_compact(self):
        result = subprocess.run(
            [_PYTHON, str(_CLI_PATH), "compact"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0

    @pytest.mark.skipif(not _CLI_PATH.exists(), reason="CLI not found")
    def test_meta_report(self):
        env = {**__import__('os').environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(
            [_PYTHON, str(_CLI_PATH), "meta"],
            capture_output=True, text=True, timeout=30, env=env,
        )
        assert result.returncode == 0

    @pytest.mark.skipif(not _CLI_PATH.exists(), reason="CLI not found")
    def test_query_no_args(self):
        result = subprocess.run(
            [_PYTHON, str(_CLI_PATH), "query"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0

    @pytest.mark.skipif(not _CLI_PATH.exists(), reason="CLI not found")
    def test_help(self):
        result = subprocess.run(
            [_PYTHON, str(_CLI_PATH), "--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "dream" in result.stdout
