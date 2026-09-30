#!/usr/bin/env python3
"""
SOL Hippocampus — Retrieval-Augmented Experiment Design

Queries the memory layer before hypothesis generation so the cortex builds
on prior knowledge rather than re-exploring charted territory.

Inserted between ``gap_detector.rank_gaps()`` and ``generate_hypothesis()``
in the cortex loop.

Usage:
    from sol_hippocampus.retrieval import MemoryQuery
    mq = MemoryQuery()

    # Before hypothesis generation
    enriched_gap = mq.enrich_gap(gap)
    hypothesis = generate_hypothesis(enriched_gap)
    augmented = mq.augment_hypothesis(hypothesis)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_SOL_ROOT = _THIS_DIR.parent.parent

if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from memory_store import load_memory_graph, memory_stats

# KB index — lazy import to avoid circular / heavy load at import time
_kb_index_module = None


def _get_kb_module():
    global _kb_index_module
    if _kb_index_module is None:
        try:
            import kb_index as _m
            _kb_index_module = _m
        except ImportError:
            _kb_index_module = False       # mark as unavailable
    return _kb_index_module if _kb_index_module else None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CONFIG_PATH = _THIS_DIR / "config.json"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Memory Finding (lightweight result container)
# ---------------------------------------------------------------------------

class MemoryFinding:
    """A finding from the memory layer relevant to a query."""

    def __init__(self, node: dict, relevance: float = 1.0):
        self.node = node
        self.relevance = relevance

    @property
    def label(self) -> str:
        return self.node.get("label", "")

    @property
    def confidence(self) -> float:
        return self.node.get("confidence", 0.0)

    @property
    def tags(self) -> list[str]:
        return self.node.get("tags", [])

    @property
    def session(self) -> str:
        return self.node.get("source_session", "")

    def __repr__(self) -> str:
        return f"MemoryFinding({self.label!r}, conf={self.confidence:.2f}, rel={self.relevance:.2f})"


# ---------------------------------------------------------------------------
# Memory Query
# ---------------------------------------------------------------------------

class MemoryQuery:
    """
    Query interface for the memory layer.

    Provides retrieval methods that the cortex loop uses to enrich gaps
    and augment hypotheses with prior knowledge.
    """

    def __init__(self):
        self._graph = load_memory_graph()
        self._cfg = _load_config()
        self._max_results = self._cfg.get("retrieval", {}).get("max_findings_per_query", 20)
        self._nodes = self._graph.get("nodes", [])
        self._edges = self._graph.get("edges", [])
        self._meta_log = self._load_meta_log()
        self._kb_index = self._init_kb_index()

    def _init_kb_index(self):
        """Lazily load the KB index if available."""
        kb_mod = _get_kb_module()
        if kb_mod is None:
            return None
        try:
            return kb_mod.get_kb_index()
        except Exception:
            return None

    def _load_meta_log(self) -> list[dict]:
        """Load the meta-learning log for experiment history queries."""
        path = _SOL_ROOT / "data" / "meta_learning_log.jsonl"
        entries = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return entries

    def reload(self):
        """Reload the memory graph from disk."""
        self._graph = load_memory_graph()
        self._nodes = self._graph.get("nodes", [])
        self._edges = self._graph.get("edges", [])

    # ---- Core queries ----

    def query_parameter(self, param_name: str) -> list[MemoryFinding]:
        """
        Find memory nodes tagged with a specific parameter.

        Returns findings sorted by confidence (highest first).
        """
        results = []
        for n in self._nodes:
            tags = n.get("tags", [])
            label = n.get("label", "")
            if (param_name in tags
                    or any(param_name in t for t in tags)
                    or param_name in label):
                results.append(MemoryFinding(n, relevance=n.get("confidence", 0.5)))
        results.sort(key=lambda f: f.confidence, reverse=True)
        return results[:self._max_results]

    def query_basin(self, rho_max_id: int) -> list[MemoryFinding]:
        """
        Find memory nodes associated with a specific core node (basin).

        Searches both tags (``rhoMax:N``) and edge connectivity.
        """
        results = []
        tag_match = f"rhoMax:{rho_max_id}"

        # Tag search
        for n in self._nodes:
            tags = n.get("tags", [])
            if tag_match in tags:
                results.append(MemoryFinding(n, relevance=n.get("confidence", 0.5)))

        # Edge connectivity search
        connected_ids = set()
        for e in self._edges:
            from_id = e.get("from_id", e.get("from"))
            to_id = e.get("to_id", e.get("to"))
            if to_id == rho_max_id:
                connected_ids.add(from_id)
            if from_id == rho_max_id:
                connected_ids.add(to_id)

        for n in self._nodes:
            if n.get("id") in connected_ids and n not in [r.node for r in results]:
                results.append(MemoryFinding(n, relevance=n.get("confidence", 0.3)))

        results.sort(key=lambda f: f.confidence, reverse=True)
        return results[:self._max_results]

    def query_experiment_history(self, template: str | None = None,
                                 gap_type: str | None = None) -> list[dict]:
        """
        Find past experiment records matching template/gap_type.

        Returns condensed session summaries from the meta-learning log.
        """
        results = []
        for entry in self._meta_log:
            if template and entry.get("template") != template:
                continue
            if gap_type and entry.get("gap_type") != gap_type:
                continue
            results.append(entry)
        return results[-self._max_results:]  # most recent

    def query_novel_regions(self, param: str,
                            known_values: list[float] | None = None) -> list[float]:
        """
        Find untested values of a parameter.

        Cross-references memory traces with the parameter's tested range
        to identify exploration opportunities.
        """
        cfg = self._cfg.get("retrieval", {})
        tolerance = cfg.get("novelty_exclusion_tolerance", 0.05)

        # Collect all tested values from memory
        tested = set()
        for n in self._nodes:
            tags = n.get("tags", [])
            for tag in tags:
                if tag.startswith(f"{param}:"):
                    try:
                        val = float(tag.split(":")[1])
                        tested.add(val)
                    except (ValueError, IndexError):
                        pass

        # Also add known_values
        if known_values:
            tested.update(known_values)

        # Also search meta-learning log
        for entry in self._meta_log:
            region = entry.get("param_region", {})
            if param in region:
                vals = region[param]
                if isinstance(vals, list):
                    tested.update(vals)

        if not tested:
            return []

        # Generate candidate novel values
        tested_sorted = sorted(tested)
        lo = tested_sorted[0]
        hi = tested_sorted[-1]
        # Extend range slightly
        lo = max(0.001, lo * 0.5)
        hi = hi * 1.5

        # Generate candidates at gaps
        novel = []
        for i in range(len(tested_sorted) - 1):
            gap = tested_sorted[i + 1] - tested_sorted[i]
            if gap > tolerance * 2:
                mid = (tested_sorted[i] + tested_sorted[i + 1]) / 2
                novel.append(round(mid, 6))

        # Boundary exploration
        novel.append(round(lo, 6))
        novel.append(round(hi, 6))

        return novel

    def memory_summary(self) -> str:
        """Human-readable summary of what the memory contains."""
        stats = memory_stats()
        lines = [
            f"Memory nodes: {stats['node_count']}",
            f"Memory edges: {stats['edge_count']}",
            f"Avg confidence: {stats['avg_confidence']:.3f}",
        ]

        # Group by tag prefix
        tag_counts: dict[str, int] = {}
        for n in self._nodes:
            for tag in n.get("tags", []):
                prefix = tag.split(":")[0] if ":" in tag else tag
                tag_counts[prefix] = tag_counts.get(prefix, 0) + 1

        if tag_counts:
            lines.append("Tags: " + ", ".join(f"{k}({v})" for k, v in sorted(tag_counts.items())))

        return " | ".join(lines)

    # ---- Gap enrichment ----

    def enrich_gap(self, gap: dict) -> dict:
        """
        Enrich a gap dict with memory context before hypothesis generation.

        Adds:
        - ``memory_findings``: relevant memory findings
        - ``tested_values``: values already tested for this parameter
        - ``novel_values``: suggested untested values
        - ``memory_context``: human-readable summary
        """
        enriched = dict(gap)
        description = gap.get("description", "")
        gap_type = gap.get("gap_type", "")

        # Try to extract parameter name from description
        param = None
        for word in description.split():
            if word in ("c_press", "damping", "dt", "conductance_gamma",
                        "psi_diffusion", "psi_relax_base", "phase_omega",
                        "mhd_build_rate", "jeans_critical"):
                param = word
                break

        findings = []
        tested = []
        novel = []

        if param:
            findings = self.query_parameter(param)
            novel = self.query_novel_regions(param)
            tested = [f.confidence for f in findings]  # proxy for tested

        # Basin-related enrichment
        if "basin" in description.lower() or "rhomaxid" in description.lower():
            for word in description.split():
                try:
                    basin_id = int(word)
                    if 1 <= basin_id <= 200:
                        findings.extend(self.query_basin(basin_id))
                except ValueError:
                    pass

        enriched["memory_findings"] = [
            {"label": f.label, "confidence": f.confidence, "tags": f.tags}
            for f in findings
        ]
        enriched["tested_values"] = tested
        enriched["novel_values"] = novel
        enriched["memory_context"] = self.memory_summary() if self._nodes else ""

        # --- KB passage enrichment ---
        kb_cfg = self._cfg.get("kb_index", {})
        kb_top_k = kb_cfg.get("enrich_top_k", 3)
        kb_passages = self._query_kb(description, top_k=kb_top_k)
        enriched["kb_passages"] = kb_passages

        return enriched

    # ---- Hypothesis augmentation ----

    def augment_hypothesis(self, hypothesis: dict) -> dict:
        """
        Refine a hypothesis based on memory knowledge.

        Modifications:
        - Exclude already-tested values (unless replication)
        - Add memory-informed falsifiers
        - Adjust step count based on known convergence
        """
        augmented = dict(hypothesis)
        knob = hypothesis.get("knob", "")
        template = hypothesis.get("template", "")

        if not knob:
            return augmented

        # Get existing knowledge about this parameter
        findings = self.query_parameter(knob)
        if findings:
            # Add memory-informed falsifiers
            augmented.setdefault("falsifiers", [])
            for f in findings[:3]:
                if f.confidence > 0.5:
                    augmented["falsifiers"].append(
                        f"Memory: Prior finding '{f.label}' (conf={f.confidence:.2f}) — "
                        f"verify consistency with memory-augmented manifold"
                    )

            # For non-replication templates, suggest novel values
            if template != "replication":
                novel = self.query_novel_regions(knob, hypothesis.get("knob_values", []))
                if novel:
                    augmented.setdefault("notes", "")
                    augmented["notes"] += f" | Novel regions for {knob}: {novel}"

        # Check experiment history for convergence info
        history = self.query_experiment_history(template=template)
        if history:
            avg_runtime = sum(h.get("runtime_sec", 0) for h in history) / len(history)
            if avg_runtime > 0:
                augmented.setdefault("notes", "")
                augmented["notes"] += f" | Avg runtime for {template}: {avg_runtime:.1f}s"

        # --- KB passage augmentation ---
        kb_cfg = self._cfg.get("kb_index", {})
        kb_top_k = kb_cfg.get("augment_top_k", 2)
        knob_desc = f"{knob} {template}"
        kb_passages = self._query_kb(knob_desc, top_k=kb_top_k)
        if kb_passages:
            augmented["kb_passages"] = kb_passages
            augmented.setdefault("notes", "")
            sections = ", ".join(p["section"] for p in kb_passages[:2])
            augmented["notes"] += f" | KB refs: {sections}"

        augmented["memory_augmented"] = True
        return augmented

    # ---- KB query helper ----

    def _query_kb(self, query_text: str, top_k: int = 3) -> list[dict]:
        """
        Query the ThothStream KB index and return passage dicts.

        Returns an empty list if the KB index is not available.
        Each dict contains: section, line_start, line_end, score,
        matched_terms, snippet.
        """
        if self._kb_index is None:
            return []
        try:
            hits = self._kb_index.query(query_text, top_k=top_k)
            return [h.to_dict() for h in hits]
        except Exception:
            return []

    def query_kb(self, query_text: str, top_k: int = 5) -> list[dict]:
        """Public KB query for CLI / external callers."""
        return self._query_kb(query_text, top_k=top_k)

    def kb_status(self) -> dict:
        """Return KB index status, or empty dict if unavailable."""
        if self._kb_index is None:
            return {"available": False}
        try:
            status = self._kb_index.status()
            status["available"] = True
            return status
        except Exception:
            return {"available": False}
