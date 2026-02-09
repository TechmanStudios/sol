"""
Tests for dream_cycle.py — session scoring, basin signatures, dream replay,
and memory consolidation.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest


# ======================================================================
# Helper: reference functions re-imported so monkeypatch can target them
# ======================================================================

class TestBasinSignature:
    """_basin_signature extracts a deterministic fingerprint from engine state."""

    def test_returns_expected_keys(self, core_graph):
        from sol_engine import SOLEngine
        from dream_cycle import _basin_signature

        engine = SOLEngine.from_default_graph()
        engine.inject("grail", 50)
        for _ in range(20):
            engine.step(dt=0.12, c_press=0.1, damping=0.2)

        sig = _basin_signature(engine, top_k=5)
        for key in ("rhoMaxId", "top_nodes", "entropy_band", "mass", "mass_hash", "activeCount"):
            assert key in sig, f"Missing key '{key}' in basin signature"

    def test_top_nodes_length(self, core_graph):
        from sol_engine import SOLEngine
        from dream_cycle import _basin_signature

        engine = SOLEngine.from_default_graph()
        engine.inject("grail", 50)
        for _ in range(20):
            engine.step(dt=0.12, c_press=0.1, damping=0.2)

        sig = _basin_signature(engine, top_k=3)
        assert len(sig["top_nodes"]) == 3

    def test_deterministic(self, core_graph):
        """Same inputs → same signature."""
        from sol_engine import SOLEngine
        from dream_cycle import _basin_signature

        def run_and_sig():
            engine = SOLEngine.from_default_graph(rng_seed=42)
            engine.inject("grail", 50)
            for _ in range(50):
                engine.step(dt=0.12, c_press=0.1, damping=0.2)
            return _basin_signature(engine)

        s1 = run_and_sig()
        s2 = run_and_sig()
        assert s1["rhoMaxId"] == s2["rhoMaxId"]
        assert s1["top_nodes"] == s2["top_nodes"]
        assert s1["mass_hash"] == s2["mass_hash"]


class TestSignatureKey:
    def test_format(self):
        from dream_cycle import _signature_key
        sig = {"rhoMaxId": 42, "top_nodes": [42, 10, 3], "entropy_band": 0.5}
        key = _signature_key(sig)
        assert key == "42:42,10,3:0.5"


class TestSessionScoring:
    """Score = recency × novelty × significance."""

    def _cfg(self):
        return {"dream_cycle": {"recency_half_life_days": 7.0}}

    def test_recent_high_quality(self):
        from dream_cycle import _score_session
        now = datetime.now(timezone.utc)
        summary = {
            "completed_at": now.isoformat(),
            "protocols_run": 2,
            "sanity_results": [{"sanity_passed": True}],
        }
        score = _score_session(summary, now, self._cfg())
        assert score > 0.5

    def test_old_session_decays(self):
        from dream_cycle import _score_session
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=30)).isoformat()
        summary = {
            "completed_at": old,
            "protocols_run": 1,
            "sanity_results": [{"sanity_passed": True}],
        }
        score = _score_session(summary, now, self._cfg())
        assert score < 0.2

    def test_sanity_fail_low_significance(self):
        from dream_cycle import _score_session
        now = datetime.now(timezone.utc)
        summary = {
            "completed_at": now.isoformat(),
            "protocols_run": 1,
            "sanity_results": [{"sanity_passed": False}],
        }
        score = _score_session(summary, now, self._cfg())
        # Significance should be low (0.2), reducing overall score
        assert score < 0.3

    def test_missing_completion_date(self):
        from dream_cycle import _score_session
        now = datetime.now(timezone.utc)
        summary = {"protocols_run": 1}
        score = _score_session(summary, now, self._cfg())
        # Should use default 30-day age
        assert score > 0


class TestDreamProtocolGeneration:
    def test_compressed_steps(self):
        from dream_cycle import _generate_dream_protocol
        cfg = {"dream_cycle": {"dream_compression_factor": 0.5, "dream_reps": 3}}
        hyp = {
            "id": "H-001", "knob": "damping", "knob_values": [0.01, 0.05],
            "steps": 200, "question": "Does damping affect basins?",
            "injection": {"label": "grail", "amount": 50},
        }
        proto = _generate_dream_protocol(hyp, cfg)
        assert proto["run"]["steps"] == 100  # 200 * 0.5
        assert proto["run"]["reps"] == 3
        assert proto["meta"]["type"] == "dream_replay"
        assert proto["knobs"]["damping"] == [0.01, 0.05]

    def test_minimum_steps(self):
        from dream_cycle import _generate_dream_protocol
        cfg = {"dream_cycle": {"dream_compression_factor": 0.01, "dream_reps": 1}}
        hyp = {"id": "H-002", "steps": 100, "knob": "c_press", "knob_values": [0.1]}
        proto = _generate_dream_protocol(hyp, cfg)
        assert proto["run"]["steps"] >= 20  # Minimum floor


class TestDreamCycleUnit:
    """Unit tests for individual DreamCycle methods (not full .run())."""

    def _make_dc(self, tmp_data, monkeypatch):
        """Create a DreamCycle wired to temp dirs."""
        import dream_cycle as dc_mod
        import memory_store as ms

        monkeypatch.setattr(dc_mod, "_SOL_ROOT", tmp_data["root"])
        monkeypatch.setattr(dc_mod, "_CONFIG_PATH", tmp_data["config"])
        monkeypatch.setattr(ms, "_MEMORY_GRAPH", tmp_data["memory_graph"])
        monkeypatch.setattr(ms, "_TRACES_DIR", tmp_data["traces_dir"])

        # Create cortex_sessions dir for loading
        sessions_dir = tmp_data["root"] / "data" / "cortex_sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Create dream_sessions dir for output
        dream_dir = tmp_data["root"] / "data" / "dream_sessions"
        dream_dir.mkdir(parents=True, exist_ok=True)

        return dc_mod, sessions_dir, dream_dir

    def test_dry_run_no_sessions(self, tmp_data, monkeypatch, core_graph):
        dc_mod, sessions_dir, _ = self._make_dc(tmp_data, monkeypatch)
        dc = dc_mod.DreamCycle(dry_run=True)
        # Redirect sessions and dream dirs
        dc._sessions_dir = sessions_dir
        result = dc.run()
        assert result["dry_run"] is True
        assert result["selected"] == []

    def test_dry_run_with_sessions(self, tmp_data, monkeypatch, core_graph):
        dc_mod, sessions_dir, _ = self._make_dc(tmp_data, monkeypatch)

        # Seed a fake session
        cx_dir = sessions_dir / "CX-20260101-000000"
        cx_dir.mkdir()
        now = datetime.now(timezone.utc)
        summary = {
            "completed_at": now.isoformat(),
            "protocols_run": 1,
            "sanity_results": [{"sanity_passed": True}],
        }
        with open(cx_dir / "summary.json", "w") as f:
            json.dump(summary, f)
        with open(cx_dir / "hypotheses.json", "w") as f:
            json.dump([{"id": "H-001", "knob": "damping", "knob_values": [0.05],
                        "steps": 100, "question": "test"}], f)

        dc = dc_mod.DreamCycle(dry_run=True)
        dc._sessions_dir = sessions_dir
        result = dc.run()
        assert result["dry_run"] is True
        assert len(result["selected"]) == 1

    def test_consolidate_basins_creates_nodes(self, tmp_data, monkeypatch, core_graph):
        """Stable basins should create new memory nodes."""
        dc_mod, _, _ = self._make_dc(tmp_data, monkeypatch)
        dc = dc_mod.DreamCycle()

        basins = [
            {
                "rhoMaxId": 82, "top_nodes": [82, 1, 42], "entropy_band": 0.5,
                "mass": 100.0, "mass_hash": "abc", "activeCount": 50,
                "stability": 3, "is_stable": True,
                "source_hypothesis": "H-001", "knob_value": 0.05, "rep": 0,
            },
        ]
        stats = dc._consolidate_basins(basins, "DS-TEST")
        assert stats["new"] >= 1

        # Verify memory node was created
        from memory_store import load_memory_graph, compact
        compact()
        mg = load_memory_graph()
        assert len(mg.get("nodes", [])) > 0
        assert mg["nodes"][0]["group"] == "memory"

    def test_consolidate_unstable_ignored(self, tmp_data, monkeypatch, core_graph):
        """Unstable basins should NOT create memory nodes."""
        dc_mod, _, _ = self._make_dc(tmp_data, monkeypatch)
        dc = dc_mod.DreamCycle()

        basins = [
            {
                "rhoMaxId": 82, "top_nodes": [82, 1, 42], "entropy_band": 0.5,
                "mass": 100.0, "mass_hash": "abc", "activeCount": 50,
                "stability": 1, "is_stable": False,
                "source_hypothesis": "H-001", "knob_value": 0.05, "rep": 0,
            },
        ]
        stats = dc._consolidate_basins(basins, "DS-TEST")
        assert stats["new"] == 0

    def test_consolidate_reinforces_existing(self, tmp_data, monkeypatch, core_graph):
        """Second encounter with same basin should reinforce, not duplicate."""
        dc_mod, _, _ = self._make_dc(tmp_data, monkeypatch)
        dc = dc_mod.DreamCycle()

        basin = {
            "rhoMaxId": 10, "top_nodes": [10, 20, 30], "entropy_band": 0.3,
            "mass": 80.0, "mass_hash": "xyz", "activeCount": 40,
            "stability": 3, "is_stable": True,
            "source_hypothesis": "H-002", "knob_value": 0.1, "rep": 0,
        }

        # First consolidation → new node
        stats1 = dc._consolidate_basins([basin], "DS-A")
        assert stats1["new"] == 1

        from memory_store import compact
        compact()

        # Re-create overlay for second pass
        from memory_overlay import MemoryOverlay
        dc._overlay = MemoryOverlay()

        # Second consolidation → reinforce
        stats2 = dc._consolidate_basins([basin], "DS-B")
        assert stats2["reinforced"] == 1
        assert stats2["new"] == 0
