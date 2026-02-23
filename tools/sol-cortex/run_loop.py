"""
SOL Cortex — Autonomous Run Loop
==================================
The core orchestration loop for the sol-cortex scientist agent.

    scan_knowledge → rank_gaps → generate_hypothesis → build_protocol
    → execute_protocol → analyze → decide_next

Produces a session log (JSONL) and tracks budget (total_steps consumed).

Usage (CLI):
    python run_loop.py                       # Full cycle, 1 gap
    python run_loop.py --max-protocols 3     # Up to 3 protocols
    python run_loop.py --dry-run             # Generate but don't execute
    python run_loop.py --gap-type unexplored_param  # Target specific gap type

Usage (Python API):
    from run_loop import CortexSession
    session = CortexSession()
    session.run()
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Resolve imports
_HERE = Path(__file__).parent
_SOL_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
sys.path.insert(0, str(_SOL_ROOT / "tools"))

from gap_detector import scan_knowledge, rank_gaps, Gap, summarize_gaps
from hypothesis_templates import generate_hypothesis, Hypothesis
from protocol_gen import (
    generate_protocol,
    validate_protocol,
    save_protocol,
    ProtocolValidationError,
    GUARD_RAILS,
)
from sol_engine import SOLEngine
from sol_intuition import get_intuition

# ---------------------------------------------------------------------------
# Optional hippocampus integration (additive — cortex runs fine without it)
# ---------------------------------------------------------------------------
_HIPPOCAMPUS_AVAILABLE = False
try:
    _HIPPO_DIR = str(_SOL_ROOT / "tools" / "sol-hippocampus")
    if _HIPPO_DIR not in sys.path:
        sys.path.insert(0, _HIPPO_DIR)
    from memory_overlay import MemoryOverlay
    from retrieval import MemoryQuery
    from meta_learner import MetaLearner
    _HIPPOCAMPUS_AVAILABLE = True
except ImportError:
    pass


def _gap_to_dict(gap: Gap) -> dict:
    """Convert a Gap dataclass to a dict for hypothesis_templates."""
    return {
        "gap_type": gap.gap_type,
        "priority": gap.priority,
        "claim_id": gap.claim_id,
        "description": gap.description,
        "suggested_action": gap.suggested_action,
        "metadata": gap.metadata,
    }


# ---------------------------------------------------------------------------
# Session configuration
# ---------------------------------------------------------------------------

@dataclass
class SessionConfig:
    """Runtime configuration for a cortex session."""
    max_protocols: int = GUARD_RAILS["max_protocols_per_session"]
    max_total_steps: int = GUARD_RAILS["max_total_steps_per_session"]
    gap_type_filter: str | None = None      # Only pursue this gap type
    dry_run: bool = False                    # Generate but don't execute
    out_dir: Path = field(default_factory=lambda: _SOL_ROOT / "data" / "cortex_sessions")
    strict_guardrails: bool = True
    verbose: bool = True


# ---------------------------------------------------------------------------
# Session log entries
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    """A single event in the session log."""
    ts: str
    event: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"ts": self.ts, "event": self.event, **self.data}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ---------------------------------------------------------------------------
# Decision functions
# ---------------------------------------------------------------------------

def should_continue(session_steps: int, protocols_run: int, config: SessionConfig) -> tuple[bool, str]:
    """Budget check: should we run another protocol?"""
    if protocols_run >= config.max_protocols:
        return False, f"max_protocols reached ({protocols_run}/{config.max_protocols})"
    if session_steps >= config.max_total_steps:
        return False, f"step budget exhausted ({session_steps}/{config.max_total_steps})"
    return True, "OK"


def select_gap(ranked_gaps: list[Gap], completed_gap_ids: set[str],
               gap_type_filter: str | None = None, engine: SOLEngine | None = None) -> Gap | None:
    """Pick the next gap to pursue, skipping already-addressed ones.
    If an engine is provided, uses the intuition subroutine to pick the most resonant gap.
    """
    valid_gaps = []
    for gap in ranked_gaps:
        gap_id = f"{gap.gap_type}:{gap.claim_id or gap.description[:40]}"
        if gap_id in completed_gap_ids:
            continue
        if gap_type_filter and gap.gap_type != gap_type_filter:
            continue
        valid_gaps.append(gap)
        
    if not valid_gaps:
        return None
        
    if len(valid_gaps) == 1 or engine is None:
        return valid_gaps[0]
        
    # Use intuition to pick the best gap
    # We'll inject the gap types and claim IDs as context nodes
    best_gap = valid_gaps[0]
    highest_confidence = -1.0
    
    # To avoid running intuition on too many gaps, limit to top 5
    for gap in valid_gaps[:5]:
        context_nodes = [gap.gap_type]
        if gap.claim_id:
            context_nodes.append(gap.claim_id)
        # Add some keywords from description
        words = [w.strip(".,!?") for w in gap.description.split() if len(w) > 4]
        context_nodes.extend(words[:3])
        
        intuition = get_intuition(engine, context_nodes, signal_strength=50.0)
        if intuition["confidence"] > highest_confidence:
            highest_confidence = intuition["confidence"]
            best_gap = gap
            
    return best_gap


def interpret_results(results: dict) -> dict:
    """Extract key signals from an execute_protocol result."""
    sanity = results.get("sanity", {})
    summary = results.get("summary", {})
    comparison = results.get("comparison", {})

    interpretation = {
        "sanity_passed": sanity.get("all_passed", False),
        "sanity_failures": sanity.get("failures", 0),
        "total_conditions": summary.get("total_conditions", 0),
        "runtime_sec": summary.get("runtime_sec", 0),
        "total_steps": summary.get("total_steps", 0),
    }

    # Per-condition final entropy and flux for quick comparison
    conditions = results.get("conditions", {})
    cond_summary = {}
    for label, data in conditions.items():
        fm = data.get("final_metrics", {})
        cond_summary[label] = {
            "entropy": fm.get("entropy", 0),
            "totalFlux": fm.get("totalFlux", 0),
            "mass": fm.get("mass", 0),
            "activeCount": fm.get("activeCount", 0),
            "rhoMax": fm.get("rhoMax", 0),
        }
    interpretation["conditions"] = cond_summary

    # Check for anomalies
    anomalies = []
    for label, cs in cond_summary.items():
        if cs.get("mass", 0) < 0.01:
            anomalies.append(f"{label}: near-zero mass")
        if cs.get("entropy", 0) == 0:
            anomalies.append(f"{label}: zero entropy")
    interpretation["anomalies"] = anomalies
    interpretation["has_anomalies"] = len(anomalies) > 0

    return interpretation


# ---------------------------------------------------------------------------
# CortexSession — the main loop
# ---------------------------------------------------------------------------

class CortexSession:
    """An autonomous scientist session.
    
    Lifecycle:
        1. init() — scan knowledge, rank gaps
        2. run()  — loop: pick gap → hypothesis → protocol → execute → log
        3. save() — write session log + summary
    """

    def __init__(self, config: SessionConfig | None = None):
        self.config = config or SessionConfig()
        self.session_id = datetime.now(timezone.utc).strftime("CX-%Y%m%d-%H%M%S")
        self.session_dir = self.config.out_dir / self.session_id
        self.log: list[LogEntry] = []
        self.protocols_run = 0
        self.total_steps = 0
        self.completed_gaps: set[str] = set()
        self.hypotheses: list[dict] = []
        self.results: list[dict] = []
        self._gaps: list[Gap] = []

        # Hippocampus integration (additive, never required)
        self._memory: MemoryOverlay | None = None
        self._query: MemoryQuery | None = None
        self._meta: MetaLearner | None = None
        if _HIPPOCAMPUS_AVAILABLE:
            try:
                self._memory = MemoryOverlay()
                self._query = MemoryQuery()
                self._meta = MetaLearner()
            except Exception:
                pass  # graceful degradation

    def _log(self, event: str, **data):
        entry = LogEntry(ts=_now(), event=event, data=data)
        self.log.append(entry)
        if self.config.verbose:
            print(f"  [{event}] {json.dumps(data, default=str)[:200]}")

    def init(self) -> list[Gap]:
        """Scan knowledge base and rank gaps."""
        self._log("session_start", session_id=self.session_id,
                  config={k: str(v) for k, v in asdict(self.config).items()})

        all_gaps = scan_knowledge()
        self._gaps = rank_gaps(all_gaps)
        self._log("knowledge_scan", total_gaps=len(self._gaps),
                  by_type={g.gap_type: sum(1 for x in self._gaps if x.gap_type == g.gap_type)
                           for g in self._gaps})

        if self.config.verbose:
            print(f"\n{summarize_gaps(self._gaps)}")

        return self._gaps

    def run(self) -> dict:
        """Execute the full cortex loop. Returns session summary."""
        if not self._gaps:
            self.init()

        hypothesis_counter = 0

        while True:
            # Budget check
            ok, reason = should_continue(self.total_steps, self.protocols_run, self.config)
            if not ok:
                self._log("budget_stop", reason=reason)
                break

            # Select next gap
            engine = SOLEngine.from_default_graph()
            gap = select_gap(self._gaps, self.completed_gaps,
                             self.config.gap_type_filter, engine=engine)
            if gap is None:
                self._log("no_gaps_remaining")
                break

            gap_id = f"{gap.gap_type}:{gap.claim_id or gap.description[:40]}"
            self._log("gap_selected", gap_id=gap_id, gap_type=gap.gap_type,
                      priority=gap.priority, description=gap.description[:120])

            # Enrich gap with memory context (hippocampus integration)
            gap_dict = _gap_to_dict(gap)
            if self._query:
                try:
                    gap_dict = self._query.enrich_gap(gap_dict)
                    mem_ctx = gap_dict.get("memory_context", "")
                    if mem_ctx:
                        self._log("gap_enriched", gap_id=gap_id,
                                  memory_context=str(mem_ctx)[:200])
                except Exception:
                    pass  # memory enrichment is optional

            # Generate hypothesis
            hypothesis_counter += 1
            h_id = f"H-{hypothesis_counter:03d}"
            try:
                hypothesis = generate_hypothesis(
                    gap_dict, h_id, prior_hypotheses=self.hypotheses
                )
            except Exception as e:
                self._log("hypothesis_error", gap_id=gap_id, error=str(e))
                self.completed_gaps.add(gap_id)
                continue

            self._log("hypothesis_generated", hypothesis_id=h_id,
                      template=hypothesis.template, question=hypothesis.question[:120])
            self.hypotheses.append(asdict(hypothesis))

            # Augment hypothesis with memory-informed falsifiers (hippocampus)
            if self._query:
                try:
                    hyp_dict = self.hypotheses[-1]
                    augmented = self._query.augment_hypothesis(hyp_dict)
                    self.hypotheses[-1] = augmented
                    self._log("hypothesis_augmented", hypothesis_id=h_id,
                              memory_falsifiers=len(augmented.get("falsifiers", [])))
                except Exception:
                    pass  # augmentation is optional

            # Generate protocol
            try:
                protocol = generate_protocol(
                    hypothesis, strict=self.config.strict_guardrails)
            except ProtocolValidationError as e:
                self._log("protocol_rejected", hypothesis_id=h_id, error=str(e))
                self.completed_gaps.add(gap_id)
                continue

            warnings = protocol.pop("_guard_rail_warnings", [])
            if warnings:
                self._log("guardrail_warnings", hypothesis_id=h_id, warnings=warnings)

            # Save protocol
            protocol_dir = self.session_dir / "protocols"
            protocol_path = save_protocol(protocol, protocol_dir)
            self._log("protocol_saved", path=str(protocol_path))

            # Execute (or skip in dry-run mode)
            if self.config.dry_run:
                self._log("dry_run_skip", hypothesis_id=h_id)
                self.completed_gaps.add(gap_id)
                self.protocols_run += 1
                continue

            # Late import to avoid loading engine unless needed
            from auto_run import execute_protocol as _execute

            run_out_dir = self.session_dir / "runs" / protocol["seriesName"]
            self._log("execution_start", hypothesis_id=h_id,
                      series=protocol["seriesName"])

            t0 = time.time()
            try:
                results = _execute(protocol, run_out_dir)
            except Exception as e:
                self._log("execution_error", hypothesis_id=h_id, error=str(e))
                self.completed_gaps.add(gap_id)
                self.protocols_run += 1
                continue

            elapsed = time.time() - t0

            # Interpret results
            interpretation = interpret_results(results)
            self.total_steps += interpretation.get("total_steps", 0)
            self.protocols_run += 1
            self.completed_gaps.add(gap_id)

            self._log("execution_complete", hypothesis_id=h_id,
                      elapsed_sec=round(elapsed, 2),
                      sanity_passed=interpretation["sanity_passed"],
                      anomalies=interpretation["anomalies"],
                      total_session_steps=self.total_steps)

            # Store slim results (no trace data)
            self.results.append({
                "hypothesis_id": h_id,
                "gap_id": gap_id,
                "series": protocol["seriesName"],
                "interpretation": interpretation,
                "exports": {k: str(v) for k, v in results.get("exports", {}).items()},
            })

            # Record in meta-learner (hippocampus integration)
            if self._meta:
                try:
                    hyp_for_meta = asdict(hypothesis)
                    interp_for_meta = {
                        "sanity_passed": interpretation["sanity_passed"],
                        "novel_basin_discovered": not interpretation.get("has_anomalies", False),
                        "proof_packet_promoted": False,
                        "informative_variation": interpretation.get("total_conditions", 0) > 1,
                    }
                    self._meta.record(self.session_id, hyp_for_meta, interp_for_meta)
                    self._log("meta_recorded", hypothesis_id=h_id,
                              template=hypothesis.template, gap_type=gap.gap_type)
                except Exception:
                    pass  # meta-learning is optional

            # Add finding to memory overlay
            if self._memory and interpretation["sanity_passed"]:
                try:
                    cond_data = interpretation.get("conditions", {})
                    for label, cs in cond_data.items():
                        self._memory.add_finding(
                            session_id=self.session_id,
                            label=f"{h_id}_{label}",
                            tags=[hypothesis.template, gap.gap_type, hypothesis.knob],
                            basin_node_id=None,  # set during dream cycle
                            confidence=0.5,
                        )
                    self._log("memory_trace_added", hypothesis_id=h_id,
                              conditions=len(cond_data))
                except Exception:
                    pass  # memory overlay is optional

            # Check for problems that warrant stopping
            if interpretation.get("has_anomalies"):
                self._log("anomaly_detected",
                          anomalies=interpretation["anomalies"],
                          action="continue (non-fatal)")

            if not interpretation["sanity_passed"]:
                self._log("sanity_failure",
                          failures=interpretation["sanity_failures"],
                          action="continue (logged for review)")

        # Save session
        summary = self._build_summary()
        self._save_session(summary)
        return summary

    def _build_summary(self) -> dict:
        """Build final session summary."""
        return {
            "session_id": self.session_id,
            "completed_at": _now(),
            "protocols_run": self.protocols_run,
            "total_steps": self.total_steps,
            "hypotheses_generated": len(self.hypotheses),
            "gaps_addressed": list(self.completed_gaps),
            "sanity_results": [
                {
                    "hypothesis": r["hypothesis_id"],
                    "series": r["series"],
                    "sanity_passed": r["interpretation"]["sanity_passed"],
                    "anomalies": r["interpretation"]["anomalies"],
                }
                for r in self.results
            ],
            "dry_run": self.config.dry_run,
        }

    def _save_session(self, summary: dict):
        """Write session log and summary to disk."""
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Session log (JSONL)
        log_path = self.session_dir / "session.jsonl"
        with open(log_path, "w", encoding="utf-8") as f:
            for entry in self.log:
                f.write(json.dumps(entry.to_dict(), default=str) + "\n")

        # Summary
        summary_path = self.session_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, default=str),
                                encoding="utf-8")

        # Hypotheses
        hyp_path = self.session_dir / "hypotheses.json"
        hyp_path.write_text(json.dumps(self.hypotheses, indent=2, default=str),
                            encoding="utf-8")

        if self.config.verbose:
            print(f"\n{'='*60}")
            print(f"Session {self.session_id} complete")
            print(f"  Protocols run:  {summary['protocols_run']}")
            print(f"  Total steps:    {summary['total_steps']}")
            print(f"  Hypotheses:     {summary['hypotheses_generated']}")
            print(f"  Gaps addressed: {len(summary['gaps_addressed'])}")
            if self._memory:
                ms = self._memory.summary()
                print(f"  Memory nodes:   {ms['memory_nodes']}")
            print(f"  Output:         {self.session_dir}")
            print(f"{'='*60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SOL Cortex — Autonomous Scientist Run Loop")
    parser.add_argument("--max-protocols", type=int, default=3,
                        help=f"Max protocols per session (default: 3, max: {GUARD_RAILS['max_protocols_per_session']})")
    parser.add_argument("--max-steps", type=int, default=None,
                        help=f"Total step budget (default: {GUARD_RAILS['max_total_steps_per_session']})")
    parser.add_argument("--gap-type", type=str, default=None,
                        choices=["unpromoted", "weak_evidence", "unfalsified",
                                 "replication", "headless_baseline", "unexplored_param"],
                        help="Only pursue gaps of this type")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate hypotheses & protocols without executing")
    parser.add_argument("--out-dir", type=str, default=None,
                        help="Output directory for session data")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress verbose output")
    args = parser.parse_args()

    config = SessionConfig(
        max_protocols=min(args.max_protocols, GUARD_RAILS["max_protocols_per_session"]),
        max_total_steps=args.max_steps or GUARD_RAILS["max_total_steps_per_session"],
        gap_type_filter=args.gap_type,
        dry_run=args.dry_run,
        verbose=not args.quiet,
    )
    if args.out_dir:
        config.out_dir = Path(args.out_dir)

    session = CortexSession(config)
    summary = session.run()

    if args.quiet:
        print(json.dumps(summary, indent=2, default=str))

    sys.exit(0)


if __name__ == "__main__":
    main()
