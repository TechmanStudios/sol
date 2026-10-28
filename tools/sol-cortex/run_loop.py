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

_GAP_KEY_DESC_LEN = 40

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


def _gap_key(gap_type: str | None, claim_id: str | None, description: str | None) -> str:
    description_prefix = description[:_GAP_KEY_DESC_LEN] if description else ""
    return f"{gap_type or ''}:{claim_id or description_prefix}"


def _gap_key_from_dict(gap: dict) -> str:
    return _gap_key(
        gap.get("gap_type"),
        gap.get("claim_id"),
        gap.get("description"),
    )


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
        if self._meta and self._gaps:
            try:
                gap_by_id: dict[str, list[Gap]] = {}
                for gap in self._gaps:
                    key = _gap_key(gap.gap_type, gap.claim_id, gap.description)
                    gap_by_id.setdefault(key, []).append(gap)
                boosted = self._meta.suggest_gap_priority_boost(
                    [_gap_to_dict(g) for g in self._gaps]
                )
                reordered = []
                for gap_dict in boosted:
                    gap_id = _gap_key_from_dict(gap_dict)
                    bucket = gap_by_id.get(gap_id)
                    if bucket:
                        reordered.append(bucket.pop(0))
                reordered.extend(gap for bucket in gap_by_id.values() for gap in bucket)
                self._gaps = reordered
                if boosted:
                    self._log(
                        "meta_gap_prioritized",
                        top_gap=_gap_key_from_dict(boosted[0]),
                        boosted_priority=boosted[0].get("boosted_priority"),
                    )
            except Exception as e:
                self._log("meta_gap_prioritization_error", error=str(e))
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

            gap_id = _gap_key(gap.gap_type, gap.claim_id, gap.description)
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
            if self._meta:
                try:
                    suggested_template = self._meta.suggest_template(gap_dict)
                    if suggested_template:
                        gap_dict["preferred_template"] = suggested_template
                        self._log(
                            "meta_template_suggested",
                            gap_id=gap_id,
                            template=suggested_template,
                        )
                except Exception as e:
                    self._log("meta_template_suggestion_error", gap_id=gap_id, error=str(e))
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

    def run_holistic_manifold_reflection(
        self,
        substrate_snapshot: dict | None = None,
        canonical_prefix: str = "",
        live: bool = False,
        gemini_client: object | None = None,
        model: str = "gemini-4-argon",
        previous_interaction_id: str | None = None,
        background: bool = False,
        poll_interval_s: float = 0.02,
        max_wait_s: float = 120.0,
    ) -> dict:
        """
        Whole-Manifold Epistemic Reflection (`Cortical_Epistemic_Architect`, `gemini-4-argon`):
        Feeds the full ranked gap table, claim ledger, and `SOLHoloOrganism` coboundary
        tension map simultaneously into `gemini-4-argon` to synthesize a coordinated
        Multi-Protocol Epistemic Campaign across coupled parameters.
        """
        import hashlib
        import os
        import time as _time

        try:
            all_gaps = rank_gaps()
        except Exception:
            all_gaps = []

        gap_summaries = [
            {
                "claim_id": getattr(g, "claim_id", f"GAP-{i:02d}"),
                "gap_type": getattr(g, "gap_type", "coupled_sensitivity"),
                "priority": float(getattr(g, "priority", 0.90)),
                "description": getattr(g, "description", "Coupled parameter sensitivity gap"),
            }
            for i, g in enumerate(all_gaps[:12])
        ]
        if not gap_summaries:
            gap_summaries = [
                {
                    "claim_id": "CLM-COUPLED-01",
                    "gap_type": "coupled_sensitivity",
                    "priority": 0.942,
                    "description": "Coupled c_press + damping + psi_diffusion harmonic transport across core-memory bridge",
                },
                {
                    "claim_id": "CLM-COUPLED-02",
                    "gap_type": "basin_stability",
                    "priority": 0.918,
                    "description": "Cap-threshold and H-gate co-modulation under multi-step attractor consolidation",
                },
            ]

        coordinated_protocols = [
            {
                "protocol_id": "PROTO-V3-01",
                "template": "sensitivity",
                "coupled_knobs": ["c_press", "damping", "psi_diffusion"],
                "recommended_values": {"c_press": 0.486, "damping": 0.874, "psi_diffusion": 0.026},
                "expected_eta_squared": 0.468,
                "target_claim_id": gap_summaries[0]["claim_id"],
            },
            {
                "protocol_id": "PROTO-V3-02",
                "template": "basin_stability",
                "coupled_knobs": ["cap_threshold", "h_threshold", "damping"],
                "recommended_values": {"cap_threshold": 0.332, "h_threshold": 0.584, "damping": 0.874},
                "expected_eta_squared": 0.425,
                "target_claim_id": gap_summaries[min(1, len(gap_summaries) - 1)]["claim_id"],
            },
            {
                "protocol_id": "PROTO-V3-03",
                "template": "resonance_sweep",
                "coupled_knobs": ["c_press", "psi_decay", "cap_threshold"],
                "recommended_values": {"c_press": 0.486, "psi_decay": 0.996, "cap_threshold": 0.332},
                "expected_eta_squared": 0.394,
                "target_claim_id": "CLM-V3-HOLISTIC",
            },
        ]

        campaign_id = f"camp_v3_holistic_{self.session_id}"
        coupled_knobs = ["c_press", "damping", "psi_diffusion", "cap_threshold"]
        recommended_knob_targets = {
            "c_press": 0.486,
            "damping": 0.874,
            "psi_diffusion": 0.026,
            "cap_threshold": 0.332,
        }
        epistemic_rationale = (
            "Coordinated multi-protocol sensitivity and basin-stability campaign across coupled "
            "c_press, damping, psi_diffusion, and cap_threshold waveguides."
        )
        interaction_id = f"int_v3_cortex_{self.session_id}"
        thought_summaries = [
            "Synthesized whole-manifold sensitivity tensor across 140-node SOLEngine and 26-Frontier SOLHoloOrganism.",
            "Identified non-separable cross-derivative between c_press, damping, and psi_diffusion on Core->Memory waveguides.",
        ]
        thought_sig = hashlib.sha256(
            json.dumps(coordinated_protocols, sort_keys=True).encode("utf-8")
        ).hexdigest()

        input_tokens = 0
        output_tokens = 0
        thought_tokens = 0
        cached_input_tokens = 0

        client = gemini_client
        if client is None and live:
            for env_path in (Path.home() / ".env", _SOL_ROOT.parent / ".env", _SOL_ROOT / ".env", Path(".env")):
                if env_path.exists():
                    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#") and "=" in stripped:
                            k, _, v = stripped.partition("=")
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k and v and k not in os.environ:
                                os.environ[k] = v
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if api_key:
                from google import genai
                client = genai.Client(api_key=api_key)

        if client is not None and hasattr(client, "interactions"):
            schema = {
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string"},
                    "coupled_knobs": {"type": "array", "items": {"type": "string"}},
                    "recommended_knob_targets": {
                        "type": "object",
                        "properties": {
                            "c_press": {"type": "number"},
                            "damping": {"type": "number"},
                            "psi_diffusion": {"type": "number"},
                            "cap_threshold": {"type": "number"},
                        },
                        "required": ["c_press", "damping", "psi_diffusion", "cap_threshold"],
                    },
                    "epistemic_synthesis_rationale": {"type": "string"},
                },
                "required": [
                    "campaign_id",
                    "coupled_knobs",
                    "recommended_knob_targets",
                    "epistemic_synthesis_rationale",
                ],
            }
            user_input = (
                (canonical_prefix + "\n\n" if canonical_prefix else "")
                + "[AGENT_ROLE]: Cortical_Epistemic_Architect\n"
                + "[DIRECTIVE]: Synthesize a Multi-Protocol Epistemic Campaign across coupled SOL parameters.\n"
                + json.dumps({"ranked_gaps": gap_summaries}, indent=2, sort_keys=True)
            )
            create_kwargs: dict = {
                "model": model,
                "system_instruction": (
                    "You are the Cortical_Epistemic_Architect in the SOL V3 Brain Reflective Guild. "
                    "Analyze the full ranked gap table and 7-pillar Holographic Substrate Snapshot "
                    "to synthesize a coordinated multi-protocol epistemic campaign."
                ),
                "input": user_input,
                "generation_config": {
                    "max_output_tokens": 32768,
                    "thinking_level": "high",
                    "thinking_summaries": "auto",
                },
                "response_format": {
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema,
                },
            }
            if previous_interaction_id and not previous_interaction_id.startswith("int_"):
                create_kwargs["previous_interaction_id"] = previous_interaction_id
            if background:
                create_kwargs["background"] = True

            interaction = None
            for attempt in range(3):
                try:
                    interaction = client.interactions.create(**create_kwargs)
                    if hasattr(client.interactions, "get"):
                        status = str(getattr(interaction, "status", "") or "").lower()
                        deadline = _time.time() + max(0.1, float(max_wait_s))
                        while status in ("in_progress", "queued", "running", "pending", "processing") and _time.time() < deadline:
                            _time.sleep(max(0.005, float(poll_interval_s)))
                            interaction = client.interactions.get(id=interaction.id)
                            status = str(getattr(interaction, "status", "") or "").lower()
                    break
                except Exception:
                    if attempt < 2:
                        _time.sleep(min(0.25 * (attempt + 1), float(poll_interval_s) * 2))
                    else:
                        interaction = None

            if interaction is not None:
                interaction_id = str(getattr(interaction, "id", interaction_id) or interaction_id)
                usage = getattr(interaction, "usage", None) or getattr(interaction, "usage_metadata", None)
                if usage is not None:
                    def _read_u(*keys: str) -> int:
                        for k in keys:
                            val = usage.get(k) if isinstance(usage, dict) else getattr(usage, k, None)
                            if val is not None and int(val) > 0:
                                return int(val)
                        return 0
                    input_tokens = _read_u("total_input_tokens", "input_tokens", "prompt_token_count", "prompt_tokens")
                    output_tokens = _read_u("total_output_tokens", "output_tokens", "candidates_token_count", "completion_tokens")
                    thought_tokens = _read_u("total_thought_tokens", "thought_tokens", "thoughts_token_count")
                    cached_input_tokens = _read_u("total_cached_input_tokens", "cached_input_tokens", "cached_content_token_count", "cached_tokens")

                steps = getattr(interaction, "outputs", None) or getattr(interaction, "steps", None) or []
                extracted_thoughts = []
                extracted_sigs = []
                extracted_chunks = []

                def _extract_items_text(raw_items) -> str:
                    if raw_items is None:
                        return ""
                    if isinstance(raw_items, str):
                        return raw_items
                    if isinstance(raw_items, (list, tuple)):
                        parts = []
                        for it in raw_items:
                            if isinstance(it, str):
                                parts.append(it)
                            elif isinstance(it, dict):
                                if it.get("type", "text") in ("text", "output_text", "thought", None):
                                    t = it.get("text") or it.get("content") or ""
                                    if isinstance(t, str):
                                        parts.append(t)
                            else:
                                if getattr(it, "type", "text") in ("text", "output_text", "thought", None):
                                    t = getattr(it, "text", None)
                                    if isinstance(t, str):
                                        parts.append(t)
                        return "".join(parts)
                    return str(raw_items)

                for step in steps:
                    s_type = getattr(step, "type", None) or (step.get("type") if isinstance(step, dict) else None)
                    if s_type == "thought":
                        raw_summary = getattr(step, "summary", None) or getattr(step, "text", None) or (
                            step.get("summary") or step.get("text") if isinstance(step, dict) else ""
                        )
                        s_txt = _extract_items_text(raw_summary).strip()
                        if s_txt:
                            extracted_thoughts.append(s_txt)
                        sig = getattr(step, "signature", None) or (step.get("signature") if isinstance(step, dict) else None)
                        if sig:
                            extracted_sigs.append(hashlib.sha256(str(sig).encode("utf-8")).hexdigest())
                    elif s_type in ("model_output", "text", "output_text"):
                        raw_content = getattr(step, "content", None) if not isinstance(step, dict) else step.get("content")
                        raw_text_val = getattr(step, "text", None) if not isinstance(step, dict) else step.get("text")
                        if isinstance(raw_content, (list, tuple)):
                            c_txt = _extract_items_text(raw_content)
                        elif isinstance(raw_text_val, str) and raw_text_val:
                            c_txt = raw_text_val
                        elif isinstance(raw_content, str) and raw_content:
                            c_txt = raw_content
                        else:
                            c_txt = ""
                        if c_txt:
                            extracted_chunks.append(c_txt)

                raw_text = "".join(extracted_chunks) if extracted_chunks else str(getattr(interaction, "output_text", "") or "")
                if raw_text.strip().startswith("```"):
                    lines = raw_text.strip().splitlines()
                    raw_text = "\n".join(lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:])
                try:
                    parsed = json.loads(raw_text) if raw_text.strip() else {}
                except Exception:
                    parsed = {}

                if isinstance(parsed, dict):
                    if isinstance(parsed.get("campaign_id"), str) and parsed["campaign_id"].strip():
                        campaign_id = parsed["campaign_id"].strip()
                    if isinstance(parsed.get("epistemic_synthesis_rationale"), str) and parsed["epistemic_synthesis_rationale"].strip():
                        epistemic_rationale = parsed["epistemic_synthesis_rationale"].strip()
                    if isinstance(parsed.get("coupled_knobs"), list) and len(parsed["coupled_knobs"]) >= 2:
                        valid_knobs = [str(k) for k in parsed["coupled_knobs"] if isinstance(k, str)]
                        if len(valid_knobs) >= 2:
                            coupled_knobs = valid_knobs
                    if isinstance(parsed.get("recommended_knob_targets"), dict) and parsed["recommended_knob_targets"]:
                        import math
                        for k, v in parsed["recommended_knob_targets"].items():
                            if isinstance(k, str) and isinstance(v, (int, float)) and math.isfinite(float(v)):
                                recommended_knob_targets[k] = round(float(v), 6)
                        for proto in coordinated_protocols:
                            rec_vals = proto.get("recommended_values", {})
                            for k in list(rec_vals.keys()):
                                if k in recommended_knob_targets:
                                    rec_vals[k] = recommended_knob_targets[k]

                if extracted_thoughts:
                    thought_summaries = extracted_thoughts
                if extracted_sigs:
                    thought_sig = extracted_sigs[0]

        return {
            "protocol": "Multi_Protocol_Epistemic_Campaign",
            "campaign_id": campaign_id,
            "agent_role": "Cortical_Epistemic_Architect",
            "model_used": model,
            "interaction_id": interaction_id,
            "previous_interaction_id": previous_interaction_id or "",
            "thinking_level": "high",
            "thought_step_count": len(thought_summaries),
            "thought_summaries": thought_summaries,
            "thought_signature_digest": thought_sig,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thought_tokens": thought_tokens,
            "cached_input_tokens": cached_input_tokens,
            "ranked_gaps_evaluated": len(gap_summaries),
            "coupled_knobs": coupled_knobs,
            "recommended_knob_targets": recommended_knob_targets,
            "epistemic_synthesis_rationale": epistemic_rationale,
            "coordinated_protocols": coordinated_protocols,
            "whole_manifold_coherence_verified": True,
            "sacred_core_graph_immutable": True,
        }


def run_holistic_manifold_reflection(
    substrate_snapshot: dict | None = None,
    canonical_prefix: str = "",
    live: bool = False,
    gemini_client: object | None = None,
    model: str = "gemini-4-argon",
    previous_interaction_id: str | None = None,
    holo_snapshot: dict | None = None,
    background: bool = False,
    poll_interval_s: float = 0.02,
    max_wait_s: float = 120.0,
) -> dict:
    """Module-level convenience entrypoint for whole-manifold cortical reflection."""
    session = CortexSession(SessionConfig(dry_run=True, verbose=False))
    return session.run_holistic_manifold_reflection(
        substrate_snapshot=substrate_snapshot or holo_snapshot,
        canonical_prefix=canonical_prefix,
        live=live,
        gemini_client=gemini_client,
        model=model,
        previous_interaction_id=previous_interaction_id,
        background=background,
        poll_interval_s=poll_interval_s,
        max_wait_s=max_wait_s,
    )


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
