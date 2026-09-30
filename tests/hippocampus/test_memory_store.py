"""
Tests for memory_store.py — persistence, compaction, node IDs, limits.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory_store import (
    MemoryEdge,
    MemoryNode,
    compact,
    load_memory_graph,
    memory_stats,
    next_node_id,
    read_traces,
    save_memory_graph,
    write_trace,
)


# ======================================================================
# Data models
# ======================================================================

class TestMemoryNode:
    def test_round_trip(self):
        n = MemoryNode(id=1001, label="test", confidence=0.8, tags=["a", "b"])
        d = n.to_dict()
        n2 = MemoryNode.from_dict(d)
        assert n2.id == 1001
        assert n2.label == "test"
        assert n2.confidence == 0.8
        assert n2.tags == ["a", "b"]
        assert n2.group == "memory"

    def test_from_dict_ignores_extra_keys(self):
        d = {"id": 1002, "label": "x", "unknown_field": 99}
        n = MemoryNode.from_dict(d)
        assert n.id == 1002
        assert not hasattr(n, "unknown_field")

    def test_defaults(self):
        n = MemoryNode(id=1000, label="x")
        assert n.group == "memory"
        assert n.confidence == 0.5
        assert n.decay_rate == 0.02
        assert n.rho == 0.0


class TestMemoryEdge:
    def test_round_trip(self):
        e = MemoryEdge(from_id=1000, to_id=5, w0=0.25, kind="memory")
        d = e.to_dict()
        e2 = MemoryEdge.from_dict(d)
        assert e2.from_id == 1000
        assert e2.to_id == 5
        assert e2.w0 == 0.25

    def test_from_graph_edge_keys(self):
        """from_dict should handle 'from'/'to' keys (as stored in graph JSON)."""
        d = {"from": 1000, "to": 42, "w0": 0.3, "kind": "memory"}
        e = MemoryEdge.from_dict(d)
        assert e.from_id == 1000
        assert e.to_id == 42

    def test_to_graph_edge(self):
        e = MemoryEdge(from_id=1000, to_id=82, w0=0.18)
        ge = e.to_graph_edge()
        assert ge["from"] == 1000
        assert ge["to"] == 82
        assert ge["w0"] == 0.18


# ======================================================================
# Trace I/O
# ======================================================================

class TestTraceIO:
    def test_write_and_read(self, tmp_data, sample_node, sample_edges):
        sid = "CX-TEST-TRACE"
        write_trace(sid, "add", sample_node, sample_edges)
        entries = read_traces(sid)
        assert len(entries) == 1
        assert entries[0]["action"] == "add"
        assert entries[0]["node"]["id"] == 1000
        assert len(entries[0]["edges"]) == 2

    def test_read_empty_session(self, tmp_data):
        entries = read_traces("CX-NONEXISTENT")
        assert entries == []

    def test_append_multiple(self, tmp_data, sample_node):
        sid = "CX-TEST-MULTI"
        write_trace(sid, "add", sample_node)
        write_trace(sid, "reinforce", sample_node)
        entries = read_traces(sid)
        assert len(entries) == 2
        assert entries[0]["action"] == "add"
        assert entries[1]["action"] == "reinforce"

    def test_action_without_node(self, tmp_data):
        sid = "CX-TEST-BARE"
        write_trace(sid, "finding:H-001:damping")
        entries = read_traces(sid)
        assert len(entries) == 1
        assert entries[0]["action"] == "finding:H-001:damping"
        assert "node" not in entries[0]


# ======================================================================
# Memory graph persistence
# ======================================================================

class TestMemoryGraphPersistence:
    def test_empty_graph(self, tmp_data):
        g = load_memory_graph()
        assert g["nodes"] == []
        assert g["edges"] == []
        assert g["id_counter"] == 1000

    def test_save_and_load(self, tmp_data):
        g = load_memory_graph()
        g["nodes"].append({"id": 1000, "label": "test"})
        g["id_counter"] = 1001
        save_memory_graph(g)

        g2 = load_memory_graph()
        assert len(g2["nodes"]) == 1
        assert g2["id_counter"] == 1001

    def test_next_node_id_empty(self, tmp_data):
        assert next_node_id() == 1000

    def test_next_node_id_after_save(self, tmp_data):
        g = load_memory_graph()
        g["id_counter"] = 1005
        save_memory_graph(g)
        assert next_node_id() == 1005


# ======================================================================
# Compaction
# ======================================================================

class TestCompaction:
    def test_compact_empty(self, tmp_data):
        result = compact()
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_compact_add_node(self, tmp_data, sample_node, sample_edges):
        write_trace("CX-COMPACT", "add", sample_node, sample_edges)
        result = compact()
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["id"] == 1000
        assert len(result["edges"]) == 2
        assert result["id_counter"] == 1001

    def test_compact_reinforce(self, tmp_data, sample_node):
        write_trace("CX-COMPACT", "add", sample_node)
        # Reinforce with higher confidence
        boosted = MemoryNode(id=1000, label="test", confidence=0.9)
        write_trace("CX-COMPACT", "reinforce", boosted)
        result = compact()
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["confidence"] == 0.9  # max of original and boost
        assert result["nodes"][0]["miss_count"] == 0

    def test_compact_decay(self, tmp_data, sample_node):
        write_trace("CX-COMPACT", "add", sample_node)
        decayed = MemoryNode(id=1000, label="test", decay_rate=0.3)
        write_trace("CX-COMPACT", "decay", decayed)
        result = compact()
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["confidence"] < 0.7  # was 0.7, decayed by 0.3

    def test_compact_prune_below_floor(self, tmp_data):
        weak = MemoryNode(id=1000, label="weak", confidence=0.03)
        write_trace("CX-COMPACT", "add", weak)
        result = compact()
        assert len(result["nodes"]) == 0  # below 0.05 floor

    def test_compact_remove(self, tmp_data, sample_node, sample_edges):
        write_trace("CX-COMPACT", "add", sample_node, sample_edges)
        remove_node = MemoryNode(id=1000, label="test")
        write_trace("CX-COMPACT", "remove", remove_node)
        result = compact()
        assert len(result["nodes"]) == 0
        assert len(result["edges"]) == 0

    def test_compact_preserves_graph_on_disk(self, tmp_data, sample_node):
        write_trace("CX-COMPACT", "add", sample_node)
        compact()
        g = load_memory_graph()
        assert len(g["nodes"]) == 1

    def test_compact_id_counter_advances(self, tmp_data):
        n1 = MemoryNode(id=1000, label="a", confidence=0.5)
        n2 = MemoryNode(id=1005, label="b", confidence=0.5)
        write_trace("CX-COMPACT", "add", n1)
        write_trace("CX-COMPACT", "add", n2)
        result = compact()
        assert result["id_counter"] == 1006


# ======================================================================
# Memory stats
# ======================================================================

class TestMemoryStats:
    def test_stats_empty(self, tmp_data):
        stats = memory_stats()
        assert stats["node_count"] == 0
        assert stats["edge_count"] == 0
        assert stats["avg_confidence"] == 0

    def test_stats_after_compact(self, tmp_data, sample_node, sample_edges):
        write_trace("CX-STATS", "add", sample_node, sample_edges)
        compact()
        stats = memory_stats()
        assert stats["node_count"] == 1
        assert stats["edge_count"] == 2
        assert stats["avg_confidence"] == pytest.approx(0.7, abs=0.01)
        assert stats["id_counter"] == 1001
        assert stats["trace_files"] == 1
