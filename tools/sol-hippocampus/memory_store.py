#!/usr/bin/env python3
"""
SOL Hippocampus — Memory Store

Append-only persistence layer for memory traces.  Each cortex / dream session
writes its own JSONL trace file.  The ``compact()`` function merges all traces
into the canonical ``data/memory_graph.json``.

Multi-agent safe: writes are per-session (no concurrent writers to the same
file); only ``compact()`` needs an advisory lock.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_SOL_ROOT = _THIS_DIR.parent.parent
_TRACES_DIR = _SOL_ROOT / "data" / "memory_traces"
_MEMORY_GRAPH = _SOL_ROOT / "data" / "memory_graph.json"
_LOCK_FILE = _SOL_ROOT / "data" / "memory_graph.lock"
_CONFIG_PATH = _THIS_DIR / "config.json"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class MemoryNode:
    """A single memory trace node — an additive record of a finding."""
    id: int
    label: str
    group: str = "memory"
    source_session: str = ""
    source_hypothesis: str = ""
    confidence: float = 0.5
    created_at: str = ""
    last_reinforced: str = ""
    decay_rate: float = 0.02
    tags: list[str] = field(default_factory=list)
    rho: float = 0.0
    p: float = 0.0
    psi: float = 0.0
    psi_bias: float = 0.0
    semanticMass: float = 1.0
    semanticMass0: float = 1.0
    miss_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryNode":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


@dataclass
class MemoryEdge:
    """A memory edge linking memory→core or memory→memory nodes."""
    from_id: int
    to_id: int
    w0: float = 0.3
    kind: str = "memory"
    source_session: str = ""
    rationale: str = ""

    def to_graph_edge(self) -> dict:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "w0": self.w0,
            "kind": self.kind,
        }

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEdge":
        # Handle serialized key names
        mapped = dict(d)
        if "from" in mapped and "from_id" not in mapped:
            mapped["from_id"] = mapped.pop("from")
        if "to" in mapped and "to_id" not in mapped:
            mapped["to_id"] = mapped.pop("to")
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in mapped.items() if k in known}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Trace files (per-session append-only JSONL)
# ---------------------------------------------------------------------------

def _trace_path(session_id: str) -> Path:
    _TRACES_DIR.mkdir(parents=True, exist_ok=True)
    return _TRACES_DIR / f"{session_id}_traces.jsonl"


def write_trace(session_id: str, action: str,
                node: MemoryNode | None = None,
                edges: list[MemoryEdge] | None = None):
    """Append a single trace entry to the session's trace file."""
    entry = {
        "action": action,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if node:
        entry["node"] = node.to_dict()
    if edges:
        entry["edges"] = [e.to_dict() for e in edges]
    path = _trace_path(session_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_traces(session_id: str) -> list[dict]:
    """Read all trace entries from a session's trace file."""
    path = _trace_path(session_id)
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


# ---------------------------------------------------------------------------
# Memory graph persistence
# ---------------------------------------------------------------------------

def _empty_graph() -> dict:
    return {
        "meta": {
            "version": 1,
            "last_compacted": "",
            "trace_count": 0,
        },
        "nodes": [],
        "edges": [],
        "id_counter": 1000,
    }


def load_memory_graph() -> dict:
    """Load the canonical memory graph, or return an empty one."""
    if not _MEMORY_GRAPH.exists():
        return _empty_graph()
    with open(_MEMORY_GRAPH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory_graph(graph: dict):
    """Save the canonical memory graph (atomic write via temp file)."""
    _MEMORY_GRAPH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _MEMORY_GRAPH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    tmp.replace(_MEMORY_GRAPH)


# ---------------------------------------------------------------------------
# Compaction
# ---------------------------------------------------------------------------

def compact(*, force: bool = False) -> dict:
    """
    Rebuild memory_graph.json from all trace files.

    Applies traces in timestamp order.  Returns the compacted graph.
    """
    cfg = _load_config()
    limits = cfg.get("memory_limits", {})
    max_nodes = limits.get("max_memory_nodes", 500)
    max_edges = limits.get("max_memory_edges", 2000)
    conf_floor = limits.get("memory_confidence_floor", 0.05)

    # Collect all trace entries from all sessions
    _TRACES_DIR.mkdir(parents=True, exist_ok=True)
    all_entries: list[dict] = []
    for tf in sorted(_TRACES_DIR.glob("*_traces.jsonl")):
        with open(tf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    all_entries.append(json.loads(line))

    # Sort by timestamp
    all_entries.sort(key=lambda e: e.get("ts", ""))

    # Replay traces to build the graph
    nodes_by_id: dict[int, dict] = {}
    edges: list[dict] = []
    id_counter = limits.get("memory_node_id_start", 1000)

    for entry in all_entries:
        action = entry.get("action", "")

        if action == "add":
            node_data = entry.get("node")
            if node_data:
                nid = node_data.get("id", id_counter)
                if nid >= id_counter:
                    id_counter = nid + 1
                nodes_by_id[nid] = node_data
            for ed in entry.get("edges", []):
                edges.append(ed)

        elif action == "reinforce":
            node_data = entry.get("node")
            if node_data:
                nid = node_data.get("id")
                if nid in nodes_by_id:
                    nodes_by_id[nid]["confidence"] = max(
                        nodes_by_id[nid].get("confidence", 0),
                        node_data.get("confidence", 0.5),
                    )
                    nodes_by_id[nid]["last_reinforced"] = entry.get("ts", "")
                    nodes_by_id[nid]["miss_count"] = 0

        elif action == "decay":
            node_data = entry.get("node")
            if node_data:
                nid = node_data.get("id")
                if nid in nodes_by_id:
                    rate = node_data.get("decay_rate", 0.02)
                    nodes_by_id[nid]["confidence"] = max(
                        0, nodes_by_id[nid].get("confidence", 0) - rate
                    )
                    nodes_by_id[nid]["miss_count"] = nodes_by_id[nid].get("miss_count", 0) + 1

        elif action == "remove":
            node_data = entry.get("node")
            if node_data:
                nid = node_data.get("id")
                nodes_by_id.pop(nid, None)
                edges = [e for e in edges
                         if e.get("from_id") != nid and e.get("to_id") != nid
                         and e.get("from") != nid and e.get("to") != nid]

    # Prune below confidence floor
    pruned_ids = set()
    for nid, nd in list(nodes_by_id.items()):
        if nd.get("confidence", 0) < conf_floor:
            pruned_ids.add(nid)
            del nodes_by_id[nid]

    edges = [e for e in edges
             if e.get("from_id") not in pruned_ids and e.get("to_id") not in pruned_ids
             and e.get("from") not in pruned_ids and e.get("to") not in pruned_ids]

    # Enforce limits (keep highest confidence)
    if len(nodes_by_id) > max_nodes:
        sorted_nodes = sorted(nodes_by_id.values(),
                              key=lambda n: n.get("confidence", 0), reverse=True)
        keep_ids = {n["id"] for n in sorted_nodes[:max_nodes]}
        nodes_by_id = {nid: nd for nid, nd in nodes_by_id.items() if nid in keep_ids}
        edges = [e for e in edges
                 if (e.get("from_id") in keep_ids or e.get("from") in keep_ids)
                 and (e.get("to_id") in keep_ids or e.get("to") in keep_ids)]

    if len(edges) > max_edges:
        edges = edges[:max_edges]

    # Build final graph
    graph = {
        "meta": {
            "version": 1,
            "last_compacted": datetime.now(timezone.utc).isoformat(),
            "trace_count": len(all_entries),
        },
        "nodes": list(nodes_by_id.values()),
        "edges": edges,
        "id_counter": id_counter,
    }

    save_memory_graph(graph)
    print(f"  [COMPACT] {len(nodes_by_id)} nodes, {len(edges)} edges, "
          f"{len(all_entries)} traces processed, {len(pruned_ids)} pruned")
    return graph


def next_node_id() -> int:
    """Get the next available memory node ID."""
    graph = load_memory_graph()
    return graph.get("id_counter", 1000)


def memory_stats() -> dict:
    """Return summary statistics about the memory graph."""
    graph = load_memory_graph()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    confidences = [n.get("confidence", 0) for n in nodes]
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
        "min_confidence": min(confidences) if confidences else 0,
        "max_confidence": max(confidences) if confidences else 0,
        "id_counter": graph.get("id_counter", 1000),
        "last_compacted": graph.get("meta", {}).get("last_compacted", "never"),
        "trace_files": len(list(_TRACES_DIR.glob("*_traces.jsonl"))) if _TRACES_DIR.exists() else 0,
    }
