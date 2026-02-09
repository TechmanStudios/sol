"""
Shared fixtures for sol-hippocampus test suite.

Every test runs against an isolated temp directory so it never touches
the real data/ or the immutable core graph on disk.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — make hippocampus + sol-core importable
# ---------------------------------------------------------------------------

_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_HIPPO_DIR = _SOL_ROOT / "tools" / "sol-hippocampus"
_CORE_DIR = _SOL_ROOT / "tools" / "sol-core"

for p in (_HIPPO_DIR, _CORE_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sol_root():
    """Return the resolved SOL repository root."""
    return _SOL_ROOT


@pytest.fixture()
def core_graph_path():
    """Path to the immutable default graph."""
    return _CORE_DIR / "default_graph.json"


@pytest.fixture()
def core_graph(core_graph_path):
    """Load the core graph as a dict (for read-only assertions)."""
    with open(core_graph_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture()
def tmp_data(tmp_path, monkeypatch):
    """
    Redirect all hippocampus I/O to a temp directory.

    Patches the module-level paths in memory_store so tests never write
    to the real ``data/`` folder.
    """
    import memory_store as ms

    traces_dir = tmp_path / "memory_traces"
    traces_dir.mkdir()
    mem_graph = tmp_path / "memory_graph.json"

    # Copy config so it's always available
    config_src = _HIPPO_DIR / "config.json"
    config_dst = tmp_path / "config.json"
    shutil.copy2(config_src, config_dst)

    monkeypatch.setattr(ms, "_TRACES_DIR", traces_dir)
    monkeypatch.setattr(ms, "_MEMORY_GRAPH", mem_graph)
    monkeypatch.setattr(ms, "_LOCK_FILE", tmp_path / "memory_graph.lock")
    monkeypatch.setattr(ms, "_CONFIG_PATH", config_dst)

    return {
        "root": tmp_path,
        "traces_dir": traces_dir,
        "memory_graph": mem_graph,
        "config": config_dst,
    }


@pytest.fixture()
def sample_node():
    """A minimal MemoryNode dict for testing."""
    from memory_store import MemoryNode
    return MemoryNode(
        id=1000,
        label="test_basin:82",
        group="memory",
        source_session="CX-TEST-001",
        source_hypothesis="H-001",
        confidence=0.7,
        tags=["damping", "basin", "rhoMax:82"],
    )


@pytest.fixture()
def sample_edges():
    """A pair of MemoryEdges for testing."""
    from memory_store import MemoryEdge
    return [
        MemoryEdge(from_id=1000, to_id=1, w0=0.18, kind="memory",
                   source_session="CX-TEST-001"),
        MemoryEdge(from_id=1000, to_id=82, w0=0.18, kind="memory",
                   source_session="CX-TEST-001"),
    ]
