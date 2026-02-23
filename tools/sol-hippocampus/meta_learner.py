#!/usr/bin/env python3
"""
SOL Hippocampus — Meta-Learning Tracker

Tracks which experiment types yield the most insight and biases future
hypothesis generation toward productive patterns.

Uses exponential moving average (EMA) scoring — no ML dependencies.

Usage:
    from sol_hippocampus.meta_learner import MetaLearner
    ml = MetaLearner()
    ml.record(session_id, hypothesis, interpretation)
    scores = ml.template_scores()
    suggestion = ml.suggest_template(gap)
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_SOL_ROOT = _THIS_DIR.parent.parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
from sol_engine import SOLEngine
from sol_intuition import get_intuition

_META_LOG = _SOL_ROOT / "data" / "meta_learning_log.jsonl"
_CONFIG_PATH = _THIS_DIR / "config.json"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Insight Scoring
# ---------------------------------------------------------------------------

def compute_insight_score(interpretation: dict, cfg: dict | None = None) -> float:
    """
    Compute an insight score for an experiment result.

    Heuristic scoring (no ML):
    - +1.0 if proof packet was promoted
    - +0.5 if novel basin discovered
    - +0.3 if informative variation observed
    - +0.1 if sanity passed but results were expected
    - 0.0 if sanity failed

    Returns a score in [0.0, 1.0].
    """
    if cfg is None:
        cfg = _load_config()
    weights = cfg.get("meta_learning", {}).get("insight_weights", {})

    if not interpretation.get("sanity_passed", False):
        return weights.get("sanity_failed", 0.0)

    score = 0.0

    if interpretation.get("proof_packet_promoted"):
        score = max(score, weights.get("proof_packet_promoted", 1.0))
    elif interpretation.get("novel_basin_discovered"):
        score = max(score, weights.get("novel_basin_discovered", 0.5))
    elif interpretation.get("informative_variation"):
        score = max(score, weights.get("informative_variation", 0.3))
    else:
        score = max(score, weights.get("expected_redundant", 0.1))

    return min(1.0, score)


# ---------------------------------------------------------------------------
# Meta-Learning Log
# ---------------------------------------------------------------------------

def _load_log() -> list[dict]:
    """Load the meta-learning log."""
    entries = []
    if _META_LOG.exists():
        with open(_META_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return entries


def _append_log(entry: dict):
    """Append an entry to the meta-learning log."""
    _META_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_META_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Meta-Learner
# ---------------------------------------------------------------------------

class MetaLearner:
    """
    Tracks experiment effectiveness and biases future hypothesis selection.

    Uses exponential moving average (EMA) of insight scores per template
    and per gap type.  No ML framework dependencies.
    """

    def __init__(self):
        self._cfg = _load_config()
        self._alpha = self._cfg.get("meta_learning", {}).get("ema_alpha", 0.30)
        self._cold_start = self._cfg.get("meta_learning", {}).get("cold_start_threshold", 5)
        self._log = _load_log()

    def reload(self):
        """Reload the log from disk."""
        self._log = _load_log()

    # ---- Recording ----

    def record(self, session_id: str, hypothesis: dict,
               interpretation: dict) -> dict:
        """
        Record the outcome of an experiment for meta-learning.

        Args:
            session_id: Cortex session ID
            hypothesis: The hypothesis dict (from hypothesis_templates)
            interpretation: Dict with keys like sanity_passed, novel_basin_discovered,
                           informative_variation, proof_packet_promoted, etc.

        Returns:
            The log entry that was recorded.
        """
        score = compute_insight_score(interpretation, self._cfg)

        # Extract param region
        knob = hypothesis.get("knob", "")
        knob_values = hypothesis.get("knob_values", [])
        param_region = {knob: knob_values} if knob else {}

        entry = {
            "session_id": session_id,
            "hypothesis_id": hypothesis.get("id", ""),
            "template": hypothesis.get("template", "unknown"),
            "gap_type": hypothesis.get("source_gap", {}).get("gap_type", "unknown"),
            "param_region": param_region,
            "sanity_passed": interpretation.get("sanity_passed", False),
            "novel_finding": interpretation.get("novel_basin_discovered", False),
            "proof_packet_promoted": interpretation.get("proof_packet_promoted", False),
            "informative_variation": interpretation.get("informative_variation", False),
            "insight_score": score,
            "basin_discovered": interpretation.get("basin_id"),
            "convergence_rate": interpretation.get("convergence_rate", 0),
            "runtime_sec": interpretation.get("runtime_sec", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        _append_log(entry)
        self._log.append(entry)

        return entry

    # ---- Scoring ----

    def template_scores(self) -> dict[str, float]:
        """
        Compute EMA of insight scores per template name.

        Returns:
            Dict mapping template name → EMA score.
        """
        return self._compute_ema("template")

    def gap_type_scores(self) -> dict[str, float]:
        """
        Compute EMA of insight scores per gap type.

        Returns:
            Dict mapping gap type → EMA score.
        """
        return self._compute_ema("gap_type")

    def _compute_ema(self, group_key: str) -> dict[str, float]:
        """Compute EMA scores grouped by a field."""
        ema: dict[str, float] = {}
        counts: dict[str, int] = defaultdict(int)

        for entry in self._log:
            key = entry.get(group_key, "unknown")
            score = entry.get("insight_score", 0)
            counts[key] += 1

            if key not in ema:
                ema[key] = score
            else:
                ema[key] = self._alpha * score + (1 - self._alpha) * ema[key]

        # Attach observation counts
        return {k: round(v, 4) for k, v in ema.items()}

    def observation_counts(self) -> dict[str, int]:
        """How many observations per template."""
        counts: dict[str, int] = defaultdict(int)
        for entry in self._log:
            counts[entry.get("template", "unknown")] += 1
        return dict(counts)

    # ---- Suggestions ----

    def suggest_template(self, gap: dict) -> str | None:
        """
        Suggest the best template for a gap based on historical insight scores.

        Uses weighted random selection biased toward higher-scoring templates.
        Falls back to intuition if insufficient data (< cold_start_threshold
        observations for the gap type).

        Args:
            gap: A gap dict from gap_detector.

        Returns:
            Template name or None (caller should use deterministic fallback).
        """
        gap_type = gap.get("gap_type", "")

        # Check if we have enough data
        relevant = [e for e in self._log if e.get("gap_type") == gap_type]
        if len(relevant) < self._cold_start:
            # Use intuition for cold start
            try:
                engine = SOLEngine.from_default_graph()
                context_nodes = [gap_type]
                if gap.get("claim_id"):
                    context_nodes.append(gap["claim_id"])
                intuition = get_intuition(engine, context_nodes, signal_strength=50.0)
                if intuition["confidence"] > 0.5 and intuition["hunch"]:
                    # Return the label of the top hunch node as a suggested template
                    return intuition["hunch"][0]["label"]
            except Exception:
                pass
            return None

        # Get template scores
        scores = self.template_scores()
        if not scores:
            return None

        # Weighted random selection
        templates = list(scores.keys())
        weights = [max(0.01, scores[t]) for t in templates]
        total = sum(weights)
        probs = [w / total for w in weights]

        # Random selection weighted by insight scores
        r = random.random()
        cumulative = 0
        for template, prob in zip(templates, probs):
            cumulative += prob
            if r <= cumulative:
                return template

        return templates[-1]

    def suggest_gap_priority_boost(self, gaps: list[dict]) -> list[dict]:
        """
        Re-rank gaps by combining original priority with gap type insight scores.

        Higher-yielding gap types get priority boosts.

        Args:
            gaps: List of gap dicts from gap_detector.

        Returns:
            Same gaps sorted by boosted priority (descending).
        """
        gt_scores = self.gap_type_scores()
        boosted = []
        for gap in gaps:
            gap = dict(gap)
            gt = gap.get("gap_type", "")
            base_priority = gap.get("priority", 0)
            insight_boost = gt_scores.get(gt, 0.1)
            gap["boosted_priority"] = base_priority + insight_boost * 3
            gap["meta_insight_score"] = insight_boost
            boosted.append(gap)

        boosted.sort(key=lambda g: g["boosted_priority"], reverse=True)
        return boosted

    # ---- Analysis ----

    def cold_regions(self) -> list[dict]:
        """
        Find parameter regions with low coverage and non-zero insight.

        These are ripe exploration targets — prior experiments show
        the area is interesting but under-explored.
        """
        # Group by param name
        param_data: dict[str, list[dict]] = defaultdict(list)
        for entry in self._log:
            for param, values in entry.get("param_region", {}).items():
                if param and values:
                    param_data[param].append({
                        "values": values,
                        "insight": entry.get("insight_score", 0),
                        "session": entry.get("session_id", ""),
                    })

        cold = []
        for param, entries in param_data.items():
            all_values = set()
            avg_insight = 0
            for e in entries:
                if isinstance(e["values"], list):
                    all_values.update(e["values"])
                avg_insight += e["insight"]
            avg_insight /= max(1, len(entries))

            if len(entries) <= 2 and avg_insight > 0.1:
                cold.append({
                    "param": param,
                    "sessions": len(entries),
                    "values_tested": sorted(all_values),
                    "avg_insight": round(avg_insight, 3),
                    "recommendation": "under-explored, likely productive",
                })

        cold.sort(key=lambda c: c["avg_insight"], reverse=True)
        return cold

    def report(self) -> str:
        """Human-readable meta-learning report."""
        lines = [
            "=" * 50,
            "SOL Meta-Learning Report",
            "=" * 50,
            "",
            f"Total observations: {len(self._log)}",
            "",
        ]

        # Template scores
        t_scores = self.template_scores()
        t_counts = self.observation_counts()
        if t_scores:
            lines.append("Template Effectiveness (EMA):")
            for t, s in sorted(t_scores.items(), key=lambda x: x[1], reverse=True):
                count = t_counts.get(t, 0)
                bar = "█" * int(s * 20)
                lines.append(f"  {t:<25} {s:.3f} {bar} (n={count})")

        # Gap type scores
        gt_scores = self.gap_type_scores()
        if gt_scores:
            lines.append("")
            lines.append("Gap Type Yield (EMA):")
            for gt, s in sorted(gt_scores.items(), key=lambda x: x[1], reverse=True):
                bar = "█" * int(s * 20)
                lines.append(f"  {gt:<25} {s:.3f} {bar}")

        # Cold regions
        cold = self.cold_regions()
        if cold:
            lines.append("")
            lines.append("Under-Explored Regions:")
            for c in cold:
                lines.append(
                    f"  {c['param']}: {c['sessions']} sessions, "
                    f"values={c['values_tested']}, "
                    f"avg_insight={c['avg_insight']}"
                )

        # Recent trends
        if len(self._log) >= 5:
            recent = self._log[-5:]
            avg_recent = sum(e.get("insight_score", 0) for e in recent) / 5
            lines.append("")
            lines.append(f"Recent trend (last 5): avg insight = {avg_recent:.3f}")

        lines.append("")
        return "\n".join(lines)
