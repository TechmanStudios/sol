#!/usr/bin/env python3
"""
SOL Hippocampus — Dream Cycle Engine

Periodic replay of recent cortex experiments through the manifold.
Dreams run compressed versions of prior sessions through the memory-augmented
graph, discovering stable attractors (basins) and reinforcing or decaying
memory traces based on what persists.

Algorithm:
1. Score & select recent cortex sessions for replay
2. Generate compressed "dream protocols" from session hypotheses
3. Execute replays through the memory-augmented manifold
4. Extract basin signatures from replay results
5. Consolidate: reinforce stable basins, decay absent ones, create new traces

Usage:
    from sol_hippocampus.dream_cycle import DreamCycle
    dc = DreamCycle()
    dc.run()
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_SOL_ROOT = _THIS_DIR.parent.parent
_SOL_CORE = _SOL_ROOT / "tools" / "sol-core"
_CONFIG_PATH = _THIS_DIR / "config.json"

if str(_SOL_CORE) not in sys.path:
    sys.path.insert(0, str(_SOL_CORE))
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from sol_engine import SOLEngine
from memory_overlay import MemoryOverlay
from memory_store import (
    MemoryNode, MemoryEdge, write_trace, load_memory_graph,
    compact as compact_memory, memory_stats,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Basin Signature
# ---------------------------------------------------------------------------

def _basin_signature(engine: SOLEngine, top_k: int = 5) -> dict:
    """
    Extract a basin signature from the engine's current state.

    A basin is characterized by:
    - rhoMaxId: the dominant node
    - top-K ρ nodes (sorted)
    - entropy band (quantized to 0.1 intervals)
    - mass distribution hash
    """
    metrics = engine.compute_metrics()
    states = engine.get_node_states()

    # Sort by ρ descending, take top K
    by_rho = sorted(states, key=lambda s: s["rho"], reverse=True)
    top_nodes = [s["id"] for s in by_rho[:top_k]]

    # Entropy band (quantized)
    entropy = metrics.get("entropy", 0)
    entropy_band = round(entropy * 10) / 10  # quantize to 0.1

    # Mass distribution hash (coarse fingerprint)
    rho_quant = [round(s["rho"], 1) for s in by_rho[:20]]
    mass_hash = hashlib.md5(json.dumps(rho_quant).encode()).hexdigest()[:8]

    return {
        "rhoMaxId": metrics.get("rhoMaxId"),
        "top_nodes": top_nodes,
        "entropy_band": entropy_band,
        "mass": round(metrics.get("mass", 0), 2),
        "mass_hash": mass_hash,
        "activeCount": metrics.get("activeCount", 0),
    }


def _signature_key(sig: dict) -> str:
    """Create a hashable key from a basin signature."""
    return f"{sig['rhoMaxId']}:{','.join(map(str, sig['top_nodes']))}:{sig['entropy_band']}"


# ---------------------------------------------------------------------------
# Session Scoring
# ---------------------------------------------------------------------------

def _score_session(summary: dict, now: datetime, cfg: dict) -> float:
    """
    Score a cortex session for dream replay priority.

    Score = recency × novelty × significance
    """
    dream_cfg = cfg.get("dream_cycle", {})
    half_life = dream_cfg.get("recency_half_life_days", 7.0)

    # Recency
    completed = summary.get("completed_at", "")
    try:
        completed_dt = datetime.fromisoformat(completed.replace("Z", "+00:00"))
        age_days = (now - completed_dt).total_seconds() / 86400
    except (ValueError, TypeError):
        age_days = 30.0
    recency = math.exp(-0.693 * age_days / half_life)  # ln(2)/half_life

    # Significance (sanity-based)
    sanity_results = summary.get("sanity_results", [])
    if not sanity_results:
        significance = 0.3
    else:
        pass_rate = sum(1 for r in sanity_results if r.get("sanity_passed")) / len(sanity_results)
        has_anomalies = any(r.get("anomalies") for r in sanity_results)
        if pass_rate >= 0.8 and not has_anomalies:
            significance = 1.0
        elif pass_rate >= 0.5:
            significance = 0.5 if has_anomalies else 0.7
        else:
            significance = 0.2

    # Novelty (approximation: more protocols = more material)
    protocols_run = summary.get("protocols_run", 0)
    novelty = min(1.0, 0.3 + 0.2 * protocols_run)

    return recency * novelty * significance


def _load_sessions(sessions_dir: Path) -> list[tuple[str, dict, dict | None]]:
    """Load all cortex sessions with their summaries and hypotheses."""
    sessions = []
    if not sessions_dir.exists():
        return sessions
    for sd in sorted(sessions_dir.iterdir()):
        if not sd.is_dir():
            continue
        summary_path = sd / "summary.json"
        hyp_path = sd / "hypotheses.json"
        if not summary_path.exists():
            continue
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        # Skip dry runs
        if summary.get("dry_run", False):
            continue
        hypotheses = None
        if hyp_path.exists():
            try:
                with open(hyp_path, "r", encoding="utf-8") as f:
                    hypotheses = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        sessions.append((sd.name, summary, hypotheses))
    return sessions


# ---------------------------------------------------------------------------
# Dream Protocol Generation
# ---------------------------------------------------------------------------

def _generate_dream_protocol(hypothesis: dict, cfg: dict) -> dict:
    """Convert a hypothesis into a compressed dream protocol."""
    dream_cfg = cfg.get("dream_cycle", {})
    compression = dream_cfg.get("dream_compression_factor", 0.5)
    reps = dream_cfg.get("dream_reps", 3)

    orig_steps = hypothesis.get("steps", 200)
    dream_steps = max(20, int(orig_steps * compression))

    knob = hypothesis.get("knob", "c_press")
    knob_values = hypothesis.get("knob_values", [0.1])

    injection = hypothesis.get("injection", {"label": "grail", "amount": 50})

    protocol = {
        "meta": {
            "name": f"dream_{hypothesis.get('id', 'unknown')}",
            "description": f"Dream replay of {hypothesis.get('id', 'unknown')}: {hypothesis.get('question', '')}",
            "type": "dream_replay",
            "source_hypothesis": hypothesis.get("id", ""),
        },
        "invariants": {
            "dt": 0.12,
            "damping": 0.2,
            "rng_seed": 42,
        },
        "knobs": {knob: knob_values},
        "injections": [
            {"label": injection.get("label", "grail"),
             "amount": injection.get("amount", 50),
             "at_step": 0}
        ],
        "run": {
            "steps": dream_steps,
            "reps": reps,
            "metrics_every": max(1, dream_steps // 10),
            "baseline": "fresh",
        },
    }

    return protocol


# ---------------------------------------------------------------------------
# Dream Cycle
# ---------------------------------------------------------------------------

class DreamCycle:
    """
    The dream cycle engine — periodic replay and memory consolidation.

    Selects top-scoring cortex sessions, replays compressed versions through
    the memory-augmented manifold, extracts basin signatures, and updates
    the memory layer based on what persists.
    """

    def __init__(self, *, max_sessions: int | None = None,
                 dry_run: bool = False):
        self._cfg = _load_config()
        dream_cfg = self._cfg.get("dream_cycle", {})
        self._max_sessions = max_sessions or dream_cfg.get("max_sessions_per_dream", 5)
        self._dry_run = dry_run
        self._stability_threshold = dream_cfg.get("stability_threshold", 2)
        self._fade_threshold = dream_cfg.get("fade_miss_threshold", 3)
        self._sessions_dir = _SOL_ROOT / "data" / "cortex_sessions"
        self._dream_dir = _SOL_ROOT / "data" / "dream_sessions"
        self._overlay = MemoryOverlay()

    def run(self) -> dict:
        """
        Execute a full dream cycle.

        Returns a summary dict with basins discovered, reinforced, decayed.
        """
        now = datetime.now(timezone.utc)
        session_id = f"DS-{now.strftime('%Y%m%d-%H%M%S')}"

        print(f"\n{'='*60}")
        print(f"Dream Cycle: {session_id}")
        print(f"{'='*60}")

        # 1. Load and score sessions
        sessions = _load_sessions(self._sessions_dir)
        scored = []
        for sid, summary, hypotheses in sessions:
            score = _score_session(summary, now, self._cfg)
            scored.append((score, sid, summary, hypotheses))
        scored.sort(reverse=True)

        selected = scored[:self._max_sessions]
        print(f"\n  Selected {len(selected)} sessions for replay:")
        for score, sid, _, _ in selected:
            print(f"    {sid} (score={score:.3f})")

        if self._dry_run:
            print("\n  [DRY RUN] Would replay the above sessions.")
            return {"session_id": session_id, "dry_run": True,
                    "selected": [s[1] for s in selected]}

        # 2. Generate dream protocols and replay
        all_basins: list[dict] = []
        dream_log: list[dict] = []
        replay_count = 0

        for score, sid, summary, hypotheses in selected:
            if not hypotheses:
                continue
            for hyp in hypotheses:
                protocol = _generate_dream_protocol(hyp, self._cfg)
                basins_for_hyp = self._replay(protocol, hyp, session_id)
                all_basins.extend(basins_for_hyp)
                replay_count += 1

                dream_log.append({
                    "source_session": sid,
                    "hypothesis_id": hyp.get("id"),
                    "protocol_name": protocol["meta"]["name"],
                    "basins_found": len(basins_for_hyp),
                    "score": score,
                })

        # 3. Consolidate basins into memory
        consolidation = self._consolidate_basins(all_basins, session_id)

        # 4. Compact memory
        compact_memory()

        # 5. Save dream session output
        output_dir = self._dream_dir / session_id
        output_dir.mkdir(parents=True, exist_ok=True)

        dream_summary = {
            "session_id": session_id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "sessions_replayed": len(selected),
            "replays_run": replay_count,
            "basins_discovered": consolidation["new"],
            "basins_reinforced": consolidation["reinforced"],
            "basins_decayed": consolidation["decayed"],
            "memory_stats": memory_stats(),
        }

        with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(dream_summary, f, indent=2)
        with open(output_dir / "dream_log.jsonl", "w", encoding="utf-8") as f:
            for entry in dream_log:
                f.write(json.dumps(entry) + "\n")
        with open(output_dir / "basin_signatures.json", "w", encoding="utf-8") as f:
            json.dump(all_basins, f, indent=2)

        print(f"\n  Dream cycle complete:")
        print(f"    Replays: {replay_count}")
        print(f"    New basins: {consolidation['new']}")
        print(f"    Reinforced: {consolidation['reinforced']}")
        print(f"    Decayed: {consolidation['decayed']}")
        print(f"    Output: {output_dir.relative_to(_SOL_ROOT)}")

        return dream_summary

    def _replay(self, protocol: dict, hypothesis: dict, dream_session_id: str) -> list[dict]:
        """
        Replay a dream protocol through the memory-augmented manifold.

        Returns a list of basin signatures extracted from the replays.
        """
        reps = protocol["run"]["reps"]
        steps = protocol["run"]["steps"]
        knobs = protocol.get("knobs", {})
        injections = protocol.get("injections", [])
        invariants = protocol.get("invariants", {})

        dt = invariants.get("dt", 0.12)
        damping = invariants.get("damping", 0.2)

        basins = []

        # Iterate over knob combinations
        knob_name = list(knobs.keys())[0] if knobs else None
        knob_values = knobs.get(knob_name, [0.1]) if knob_name else [0.1]

        for kv in knob_values:
            rep_basins = []
            for rep in range(reps):
                # Create a fresh memory-augmented engine per rep
                kw = {"dt": dt, "damping": damping, "rng_seed": 42 + rep}
                if knob_name:
                    kw[knob_name] = kv
                engine = self._overlay.create_engine(**kw)

                # Apply injections
                for inj in injections:
                    engine.inject(inj.get("label", "grail"), inj.get("amount", 50))

                # Run steps
                c_press = kv if knob_name == "c_press" else invariants.get("c_press", 0.1)
                d = kv if knob_name == "damping" else damping

                for _ in range(steps):
                    engine.step(dt=dt, c_press=c_press, damping=d)

                # Extract basin signature
                sig = _basin_signature(engine)
                sig["knob_value"] = kv
                sig["rep"] = rep
                sig["source_hypothesis"] = hypothesis.get("id", "")
                rep_basins.append(sig)

            # Check stability across reps
            key_counts = Counter(_signature_key(b) for b in rep_basins)
            for basin in rep_basins:
                key = _signature_key(basin)
                basin["stability"] = key_counts[key]
                basin["is_stable"] = key_counts[key] >= self._stability_threshold

            basins.extend(rep_basins)

        return basins

    def _consolidate_basins(self, basins: list[dict], dream_session_id: str) -> dict:
        """
        Update memory based on basin observations.

        - New stable basins → create memory nodes
        - Known basins seen again → reinforce
        - Known basins not seen → decay / increment miss count
        """
        stats = {"new": 0, "reinforced": 0, "decayed": 0}

        # Get existing memory nodes
        existing_basins: dict[str, dict] = {}
        for mn in self._overlay.memory_nodes:
            tags = mn.get("tags", [])
            for tag in tags:
                if tag.startswith("basin:"):
                    existing_basins[tag] = mn

        # Extract unique stable basins
        seen_keys: set[str] = set()
        stable_basins = [b for b in basins if b.get("is_stable")]

        for basin in stable_basins:
            key = _signature_key(basin)
            basin_tag = f"basin:{key}"

            if basin_tag in seen_keys:
                continue
            seen_keys.add(basin_tag)

            if basin_tag in existing_basins:
                # Reinforce existing memory
                mn = existing_basins[basin_tag]
                self._overlay.reinforce(mn["id"], dream_session_id, 0.1)
                stats["reinforced"] += 1
            else:
                # Create new memory node
                rho_max_id = basin.get("rhoMaxId")
                top_nodes = basin.get("top_nodes", [])
                connected = [rho_max_id] if rho_max_id else []
                connected.extend([n for n in top_nodes[:3] if n != rho_max_id and n < 1000])

                self._overlay.add_finding(
                    label=f"basin:{key}",
                    session_id=dream_session_id,
                    hypothesis_id=basin.get("source_hypothesis", ""),
                    tags=[basin_tag, f"rhoMax:{basin.get('rhoMaxId')}",
                          f"entropy:{basin.get('entropy_band')}"],
                    confidence=0.3 + 0.1 * basin.get("stability", 1),
                    connected_core_ids=connected,
                    rationale=f"Stable attractor discovered in dream replay (stability={basin.get('stability')})",
                )
                stats["new"] += 1

        # Decay basins that weren't seen
        seen_basin_tags = seen_keys
        for tag, mn in existing_basins.items():
            if tag not in seen_basin_tags:
                self._overlay.decay(mn["id"], dream_session_id)
                stats["decayed"] += 1

        return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SOL Hippocampus — Dream Cycle")
    parser.add_argument("--sessions", type=int, default=None,
                        help="Max sessions to replay")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be replayed without executing")
    args = parser.parse_args()

    dc = DreamCycle(max_sessions=args.sessions, dry_run=args.dry_run)
    dc.run()


if __name__ == "__main__":
    main()
