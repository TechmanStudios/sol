"""
Tests for memory_overlay.py — graph composition, engine creation, mutations.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from memory_store import MemoryNode, MemoryEdge, write_trace, compact, save_memory_graph, load_memory_graph
from memory_overlay import MemoryOverlay


# ======================================================================
# Helpers
# ======================================================================

def _core_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ======================================================================
# Core graph loading
# ======================================================================

class TestCoreGraph:
    def test_core_nodes_count(self, core_graph_path):
        overlay = MemoryOverlay(core_graph_path=core_graph_path)
        assert overlay.core_node_count == 140

    def test_core_edges_count(self, core_graph_path):
        overlay = MemoryOverlay(core_graph_path=core_graph_path)
        assert len(overlay.core_edges) == 845


# ======================================================================
# Empty memory overlay (identity operation)
# ======================================================================

class TestEmptyOverlay:
    def test_merged_nodes_equals_core(self, tmp_data, core_graph_path):
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        merged = overlay.merged_nodes()
        assert len(merged) == 140  # no memory nodes

    def test_merged_edges_equals_core(self, tmp_data, core_graph_path):
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        merged = overlay.merged_edges()
        assert len(merged) == 845

    def test_engine_creation_empty(self, tmp_data, core_graph_path):
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        engine = overlay.create_engine()
        engine.inject("grail", 10.0)
        engine.run(steps=50)
        m = engine.compute_metrics()
        assert m["mass"] > 0
        assert 0 <= m["entropy"] <= 1


# ======================================================================
# Overlay with memory nodes
# ======================================================================

class TestOverlayWithMemory:
    def _seed_memory(self, tmp_data):
        """Write a memory graph with 1 node + 2 edges directly."""
        mg = {
            "meta": {"version": 1, "last_compacted": "", "trace_count": 0},
            "nodes": [
                {
                    "id": 1000, "label": "test_basin", "group": "memory",
                    "confidence": 0.8, "tags": ["damping"],
                    "rho": 0.0, "p": 0.0, "psi": 0.0, "psi_bias": 0.0,
                    "semanticMass": 1.0, "semanticMass0": 1.0,
                }
            ],
            "edges": [
                {"from_id": 1000, "to_id": 1, "w0": 0.18, "kind": "memory"},
                {"from_id": 1000, "to_id": 82, "w0": 0.18, "kind": "memory"},
            ],
            "id_counter": 1001,
        }
        save_memory_graph(mg)

    def test_merged_nodes_adds_memory(self, tmp_data, core_graph_path):
        self._seed_memory(tmp_data)
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        merged = overlay.merged_nodes()
        assert len(merged) == 141  # 140 core + 1 memory

    def test_memory_node_has_required_fields(self, tmp_data, core_graph_path):
        self._seed_memory(tmp_data)
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        merged = overlay.merged_nodes()
        mem_node = [n for n in merged if n.get("group") == "memory"][0]
        for field in ("id", "label", "group", "rho", "psi", "semanticMass"):
            assert field in mem_node

    def test_semantic_mass_scales_with_confidence(self, tmp_data, core_graph_path):
        self._seed_memory(tmp_data)
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        merged = overlay.merged_nodes()
        mem_node = [n for n in merged if n.get("group") == "memory"][0]
        # conf=0.8 → semanticMass = 0.5 + 0.8*1.5 = 1.7
        assert mem_node["semanticMass"] == pytest.approx(1.7, abs=0.01)

    def test_merged_edges_adds_memory(self, tmp_data, core_graph_path):
        self._seed_memory(tmp_data)
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        merged = overlay.merged_edges()
        assert len(merged) == 847  # 845 core + 2 memory

    def test_engine_with_memory_runs(self, tmp_data, core_graph_path):
        self._seed_memory(tmp_data)
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        engine = overlay.create_engine()
        engine.inject("grail", 10.0)
        engine.run(steps=100)
        m = engine.compute_metrics()
        assert m["mass"] > 0
        assert m["activeCount"] >= 1

    def test_memory_node_ids_above_1000(self, tmp_data, core_graph_path):
        self._seed_memory(tmp_data)
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        for n in overlay.memory_nodes:
            assert n["id"] >= 1000


# ======================================================================
# Core immutability
# ======================================================================

class TestCoreImmutability:
    def test_core_graph_unchanged_after_overlay(self, tmp_data, core_graph_path):
        hash_before = _core_hash(core_graph_path)
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        # Do operations
        engine = overlay.create_engine()
        engine.inject("grail", 50.0)
        engine.run(steps=200)
        engine.compute_metrics()
        hash_after = _core_hash(core_graph_path)
        assert hash_before == hash_after

    def test_core_nodes_not_mutated(self, tmp_data, core_graph_path):
        with open(core_graph_path, "r", encoding="utf-8") as f:
            original = json.load(f)
        original_ids = {n["id"] for n in original["rawNodes"]}

        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        merged = overlay.merged_nodes()
        for n in merged:
            if n["id"] in original_ids:
                # Core node — should be unchanged
                assert n.get("group") != "memory"


# ======================================================================
# Mutation methods
# ======================================================================

class TestOverlayMutations:
    def test_add_finding(self, tmp_data, core_graph_path):
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        node = overlay.add_finding(
            label="test_finding",
            session_id="CX-TEST",
            hypothesis_id="H-001",
            tags=["damping"],
            confidence=0.6,
            connected_core_ids=[1, 82],
        )
        assert node.id >= 1000
        assert node.group == "memory"
        assert overlay.memory_node_count == 1
        assert len(overlay.memory_edges) == 2

    def test_reinforce(self, tmp_data, core_graph_path):
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        overlay.add_finding(
            label="to_reinforce",
            session_id="CX-TEST",
            hypothesis_id="H-001",
            confidence=0.5,
        )
        overlay.reinforce(1000, "CX-TEST-2", confidence_boost=0.2)
        node = overlay.memory_nodes[0]
        assert node["confidence"] == pytest.approx(0.7, abs=0.01)

    def test_decay(self, tmp_data, core_graph_path):
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        overlay.add_finding(
            label="to_decay",
            session_id="CX-TEST",
            hypothesis_id="H-001",
            confidence=0.5,
        )
        overlay.decay(1000, "CX-TEST-2", amount=0.3)
        node = overlay.memory_nodes[0]
        assert node["confidence"] == pytest.approx(0.2, abs=0.01)

    def test_summary(self, tmp_data, core_graph_path):
        overlay = MemoryOverlay(
            core_graph_path=core_graph_path,
            memory_graph_path=tmp_data["memory_graph"],
        )
        s = overlay.summary()
        assert s["core_nodes"] == 140
        assert s["core_edges"] == 845
        assert s["memory_nodes"] == 0
        assert s["total_nodes"] == 140
