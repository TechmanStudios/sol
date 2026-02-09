#!/usr/bin/env python3
"""
SOL Hippocampus — Memory Overlay

Merges the immutable core graph (default_graph.json) with additive memory
traces to produce a composite graph.  The SOLEngine is created via
``SOLEngine.from_graph()`` — the engine never knows about the overlay.

The core graph is NEVER modified.  Memory nodes (id >= 1000, group="memory")
layer on top like hippocampal neuronal projections.

Usage:
    from sol_hippocampus.memory_overlay import MemoryOverlay

    overlay = MemoryOverlay()
    engine = overlay.create_engine(dt=0.12, c_press=0.1)

    # With memory-augmented dynamics
    engine.inject("grail", 50)
    engine.step()
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_store import (
    MemoryEdge,
    MemoryNode,
    load_memory_graph,
    next_node_id,
    write_trace,
)

import sys
_SOL_CORE = Path(__file__).resolve().parent.parent / "sol-core"
if str(_SOL_CORE) not in sys.path:
    sys.path.insert(0, str(_SOL_CORE))

from sol_engine import SOLEngine, DEFAULT_GRAPH_PATH


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_CONFIG_PATH = _THIS_DIR / "config.json"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Memory Overlay
# ---------------------------------------------------------------------------

class MemoryOverlay:
    """
    Composes the immutable core graph with additive memory traces.

    The core graph (140 nodes, 845 edges) remains byte-identical on disk.
    Memory nodes and edges are loaded from ``data/memory_graph.json`` and
    appended to the node/edge lists before engine creation.

    Memory nodes have:
    - ``group: "memory"`` → always-active (like bridge nodes)
    - ``psi_bias: 0.0`` → neutral, unless set by finding nature
    - ``id >= 1000`` → no collision with core node IDs (1–140)
    """

    def __init__(self, *, core_graph_path: str | Path | None = None,
                 memory_graph_path: str | Path | None = None):
        self._core_path = Path(core_graph_path) if core_graph_path else DEFAULT_GRAPH_PATH
        self._memory_path = Path(memory_graph_path) if memory_graph_path else None

        # Load core graph (immutable reference)
        with open(self._core_path, "r", encoding="utf-8") as f:
            self._core = json.load(f)

        # Load memory graph (additive layer)
        if self._memory_path and self._memory_path.exists():
            with open(self._memory_path, "r", encoding="utf-8") as f:
                self._memory = json.load(f)
        else:
            self._memory = load_memory_graph()

        self._cfg = _load_config()
        self._coupling = self._cfg.get("memory_limits", {}).get("memory_coupling_w0", 0.30)

    # ---- Property accessors ----

    @property
    def core_nodes(self) -> list[dict]:
        return list(self._core.get("rawNodes", []))

    @property
    def core_edges(self) -> list[dict]:
        return list(self._core.get("rawEdges", []))

    @property
    def memory_nodes(self) -> list[dict]:
        return list(self._memory.get("nodes", []))

    @property
    def memory_edges(self) -> list[dict]:
        return list(self._memory.get("edges", []))

    @property
    def core_node_count(self) -> int:
        return len(self._core.get("rawNodes", []))

    @property
    def memory_node_count(self) -> int:
        return len(self._memory.get("nodes", []))

    # ---- Graph composition ----

    def merged_nodes(self) -> list[dict]:
        """Return core nodes + memory nodes (core unchanged)."""
        core = self.core_nodes
        mem = []
        for mn in self.memory_nodes:
            # Ensure memory node has engine-required fields
            node = dict(mn)
            node.setdefault("group", "memory")
            node.setdefault("rho", 0.0)
            node.setdefault("p", 0.0)
            node.setdefault("psi", 0.0)
            node.setdefault("psi_bias", 0.0)
            node.setdefault("semanticMass", 1.0)
            node.setdefault("semanticMass0", 1.0)
            # Scale semantic mass by confidence — higher confidence = more
            # gravitational pull in the manifold
            conf = node.get("confidence", 0.5)
            node["semanticMass"] = 0.5 + conf * 1.5  # range: 0.5–2.0
            node["semanticMass0"] = node["semanticMass"]
            mem.append(node)
        return core + mem

    def merged_edges(self) -> list[dict]:
        """Return core edges + memory edges (core unchanged)."""
        core = self.core_edges
        mem = []
        for me in self.memory_edges:
            edge = {}
            # Normalize key names
            edge["from"] = me.get("from_id", me.get("from"))
            edge["to"] = me.get("to_id", me.get("to"))
            # Scale w0 by confidence of source node
            base_w0 = me.get("w0", self._coupling)
            edge["w0"] = base_w0
            edge["kind"] = me.get("kind", "memory")
            mem.append(edge)
        return core + mem

    def create_engine(self, **kwargs) -> SOLEngine:
        """
        Create a SOLEngine with the memory-augmented graph.

        Drop-in replacement for ``SOLEngine.from_default_graph()``.
        When no memory nodes exist, produces identical results to the
        core engine (identity operation).

        All keyword arguments are passed through to ``SOLEngine.from_graph()``.
        """
        nodes = self.merged_nodes()
        edges = self.merged_edges()
        return SOLEngine.from_graph(nodes, edges, **kwargs)

    # ---- Memory mutation (additive only) ----

    def add_finding(self, *,
                    label: str,
                    session_id: str,
                    hypothesis_id: str,
                    tags: list[str] | None = None,
                    confidence: float = 0.5,
                    connected_core_ids: list[int] | None = None,
                    rationale: str = "") -> MemoryNode:
        """
        Create a new memory node (and optionally edges to core nodes).

        The node is written to the session's trace file.  Call ``compact()``
        to merge it into the canonical memory graph.
        """
        now = datetime.now(timezone.utc).isoformat()
        nid = next_node_id()

        node = MemoryNode(
            id=nid,
            label=label,
            group="memory",
            source_session=session_id,
            source_hypothesis=hypothesis_id,
            confidence=confidence,
            created_at=now,
            last_reinforced=now,
            decay_rate=self._cfg.get("memory_limits", {}).get("memory_decay_rate_default", 0.02),
            tags=tags or [],
        )

        edges = []
        for cid in (connected_core_ids or []):
            edges.append(MemoryEdge(
                from_id=nid,
                to_id=cid,
                w0=self._coupling * confidence,
                kind="memory",
                source_session=session_id,
                rationale=rationale,
            ))

        write_trace(session_id, "add", node, edges)

        # Update in-memory state
        self._memory.setdefault("nodes", []).append(node.to_dict())
        for e in edges:
            self._memory.setdefault("edges", []).append(e.to_dict())
        self._memory["id_counter"] = nid + 1

        return node

    def reinforce(self, node_id: int, session_id: str, confidence_boost: float = 0.1):
        """Reinforce an existing memory node (bump confidence)."""
        now = datetime.now(timezone.utc).isoformat()
        for n in self._memory.get("nodes", []):
            if n.get("id") == node_id:
                n["confidence"] = min(1.0, n.get("confidence", 0) + confidence_boost)
                n["last_reinforced"] = now
                n["miss_count"] = 0
                write_trace(session_id, "reinforce",
                            MemoryNode.from_dict(n))
                return

    def decay(self, node_id: int, session_id: str, amount: float | None = None):
        """Apply decay to a memory node."""
        for n in self._memory.get("nodes", []):
            if n.get("id") == node_id:
                rate = amount or n.get("decay_rate", 0.02)
                n["confidence"] = max(0, n.get("confidence", 0) - rate)
                n["miss_count"] = n.get("miss_count", 0) + 1
                write_trace(session_id, "decay",
                            MemoryNode.from_dict(n))
                return

    def decay_all(self, session_id: str, dt: float = 1.0):
        """Apply time-based decay to all memory nodes."""
        for n in self._memory.get("nodes", []):
            rate = n.get("decay_rate", 0.02)
            n["confidence"] = max(0, n.get("confidence", 0) * math.exp(-rate * dt))

    # ---- Query helpers ----

    def find_by_tag(self, tag: str) -> list[dict]:
        """Find memory nodes with a specific tag."""
        return [n for n in self.memory_nodes
                if tag in n.get("tags", [])]

    def find_by_session(self, session_id: str) -> list[dict]:
        """Find memory nodes from a specific session."""
        return [n for n in self.memory_nodes
                if n.get("source_session") == session_id]

    def find_by_basin(self, rho_max_id: int) -> list[dict]:
        """Find memory nodes connected to a specific core node."""
        connected = set()
        for e in self.memory_edges:
            from_id = e.get("from_id", e.get("from"))
            to_id = e.get("to_id", e.get("to"))
            if to_id == rho_max_id:
                connected.add(from_id)
            if from_id == rho_max_id:
                connected.add(to_id)
        return [n for n in self.memory_nodes if n.get("id") in connected]

    def summary(self) -> dict:
        """Return a summary of the overlay state."""
        mem_nodes = self.memory_nodes
        confidences = [n.get("confidence", 0) for n in mem_nodes]
        return {
            "core_nodes": self.core_node_count,
            "core_edges": len(self.core_edges),
            "memory_nodes": len(mem_nodes),
            "memory_edges": len(self.memory_edges),
            "total_nodes": self.core_node_count + len(mem_nodes),
            "total_edges": len(self.core_edges) + len(self.memory_edges),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
        }
