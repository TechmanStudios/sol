"""
SOL Cortex — Hypothesis Templates
===================================
Structured hypothesis templates that map gap types to experiment designs.
Each template produces a partial protocol dict that protocol_gen.py
completes and validates.

Templates encode the proven experiment patterns from the SOL research
history (CapLaw sweeps, dt compression, basin programming, etc.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Hypothesis:
    """A structured hypothesis ready for protocol generation."""
    id: str                     # e.g. "H-001"
    template: str               # Template name that generated this
    question: str               # One-sentence falsifiable question
    knob: str | None = None     # Primary independent variable
    knob_values: list = field(default_factory=list)
    injection: dict = field(default_factory=lambda: {"label": "grail", "amount": 50})
    steps: int = 200
    reps: int = 3
    falsifiers: list[str] = field(default_factory=list)
    notes: str = ""
    source_gap: dict = field(default_factory=dict)  # Gap that motivated this


# ---- Template Registry -------------------------------------------------

TEMPLATES: dict[str, dict] = {}


def register(name: str):
    """Decorator to register a hypothesis template function."""
    def wrapper(fn):
        TEMPLATES[name] = {"fn": fn, "name": name, "doc": fn.__doc__ or ""}
        return fn
    return wrapper


@register("parameter_sweep")
def parameter_sweep(gap: dict, **kwargs) -> Hypothesis:
    """Sweep a single parameter across a range to find sensitivity.
    
    Best for: unexplored_param gaps, establishing baselines.
    """
    param = gap.get("metadata", {}).get("param", "damping")
    values = gap.get("metadata", {}).get("range", [0.05, 0.1, 0.2, 0.5])

    return Hypothesis(
        id=kwargs.get("id", "H-sweep"),
        template="parameter_sweep",
        question=f"How does {param} affect entropy, flux, and mass over 200 steps?",
        knob=param,
        knob_values=values,
        steps=200,
        reps=3,
        falsifiers=[
            f"All {param} values produce identical results (no sensitivity)",
            f"Higher {param} produces non-monotonic response without explanation",
        ],
        source_gap=gap,
    )


@register("replication")
def replication(gap: dict, **kwargs) -> Hypothesis:
    """Replicate an existing dashboard result with headless sol-core.
    
    Best for: replication gaps, strengthening existing claims.
    """
    packet_name = gap.get("metadata", {}).get("packet", "unknown")
    claim = gap.get("metadata", {}).get("original_claim", "")

    return Hypothesis(
        id=kwargs.get("id", "H-replicate"),
        template="replication",
        question=f"Can headless sol-core reproduce: {claim}?",
        steps=300,
        reps=5,
        falsifiers=[
            "Headless results qualitatively differ from dashboard results",
            "Metrics trend in opposite direction from original claim",
        ],
        notes=f"Replicating {packet_name}",
        source_gap=gap,
    )


@register("threshold_scan")
def threshold_scan(gap: dict, **kwargs) -> Hypothesis:
    """Find the critical threshold where a behavior transitions.
    
    Best for: boundary detection, ridge scanning.
    """
    param = gap.get("metadata", {}).get("param", "damping")
    values = gap.get("metadata", {}).get("range", [])
    if not values or len(values) < 3:
        values = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]

    return Hypothesis(
        id=kwargs.get("id", "H-threshold"),
        template="threshold_scan",
        question=f"At what value of {param} does the system behavior qualitatively change?",
        knob=param,
        knob_values=values,
        steps=300,
        reps=5,
        falsifiers=[
            "No transition detected across entire range",
            "Transition is not reproducible across reps",
        ],
        source_gap=gap,
    )


@register("injection_comparison")
def injection_comparison(gap: dict, **kwargs) -> Hypothesis:
    """Compare different injection targets to understand graph topology effects.
    
    Best for: basin programming, latch identity verification.
    """
    targets = kwargs.get("targets", ["grail", "consciousness", "gravity", "entropy"])

    return Hypothesis(
        id=kwargs.get("id", "H-inject-cmp"),
        template="injection_comparison",
        question="Do different injection targets produce distinct basin formations?",
        steps=200,
        reps=3,
        falsifiers=[
            "All injection targets produce identical metric trajectories",
            "RhoMaxId is always the same regardless of injection target",
        ],
        notes=f"Comparing targets: {targets}",
        source_gap=gap,
    )


@register("baseline_golden")
def baseline_golden(gap: dict, **kwargs) -> Hypothesis:
    """Establish golden baseline outputs for regression testing.
    
    Best for: headless_baseline gaps.
    """
    return Hypothesis(
        id=kwargs.get("id", "H-golden"),
        template="baseline_golden",
        question="What are the canonical metric outputs for standard injection protocols?",
        steps=500,
        reps=1,
        falsifiers=[
            "Output changes between identical runs with same seed (non-determinism)",
        ],
        notes="Golden baseline for Phase 3 regression suite. Single rep, high step count, full trace.",
        source_gap=gap,
    )


@register("dt_compression")
def dt_compression(gap: dict, **kwargs) -> Hypothesis:
    """Test how dt affects time-to-failure or other temporal metrics.
    
    Best for: replicating CL-3 (metastability) with headless.
    """
    return Hypothesis(
        id=kwargs.get("id", "H-dt-compress"),
        template="dt_compression",
        question="Does dt compress time-to-failure in headless sol-core as it does in the dashboard?",
        knob="dt",
        knob_values=[0.08, 0.10, 0.12, 0.16, 0.20],
        steps=500,
        reps=5,
        falsifiers=[
            "Time-to-failure is constant across dt values",
            "Relationship is non-monotonic (failure time increases then decreases)",
        ],
        source_gap=gap,
    )


@register("psi_sensitivity")
def psi_sensitivity(gap: dict, **kwargs) -> Hypothesis:
    """Test how psi parameters affect routing and basin formation.
    
    Best for: exploring CL-5 (ψ routing) with headless.
    """
    param = gap.get("metadata", {}).get("param", "psi_diffusion")
    values = gap.get("metadata", {}).get("range", [0.2, 0.4, 0.6, 0.8, 1.0])

    return Hypothesis(
        id=kwargs.get("id", "H-psi"),
        template="psi_sensitivity",
        question=f"How does {param} affect entropy distribution and basin selection?",
        knob=param,
        knob_values=values,
        steps=300,
        reps=3,
        falsifiers=[
            f"Entropy is invariant to {param} changes",
            "RhoMaxId distribution is identical across all values",
        ],
        source_gap=gap,
    )


# ---- Template Selection ------------------------------------------------

def select_template(gap: dict) -> str:
    """Given a gap, select the most appropriate hypothesis template."""
    gap_type = gap.get("gap_type", "")
    
    mapping = {
        "unexplored_param": "parameter_sweep",
        "replication": "replication",
        "headless_baseline": "baseline_golden",
        "unpromoted": "threshold_scan",
        "weak_evidence": "replication",
        "unfalsified": "threshold_scan",
        "open_question": "threshold_scan",
    }
    
    # Special cases based on metadata
    meta = gap.get("metadata", {})
    param = meta.get("param", "")
    if param == "dt":
        return "dt_compression"
    if "psi" in param.lower():
        return "psi_sensitivity"
    
    return mapping.get(gap_type, "parameter_sweep")


def generate_hypothesis(
    gap: dict,
    hypothesis_id: str = "H-auto",
    prior_hypotheses: list[dict] | None = None,
) -> Hypothesis:
    """Generate a hypothesis from a gap using the best-matching template.

    If the LLM is available, uses LLM-powered generation for richer,
    more creative hypotheses grounded in existing knowledge.  Falls back
    to static templates when the LLM is unavailable or fails.

    Args:
        gap: Knowledge gap dict.
        hypothesis_id: ID to assign (e.g. "H-001").
        prior_hypotheses: Previously generated hypotheses this session,
            passed to the LLM to enforce diversity.
    """
    # Try LLM-augmented path first
    llm_hyp = _try_llm_hypothesis(gap, hypothesis_id, prior_hypotheses)
    if llm_hyp is not None:
        return llm_hyp

    # Fallback: static template — pick one that hasn't been used yet
    template_name = _select_diverse_template(gap, prior_hypotheses)
    template_fn = TEMPLATES.get(template_name, {}).get("fn")
    if not template_fn:
        template_fn = TEMPLATES["parameter_sweep"]["fn"]

    return template_fn(gap, id=hypothesis_id)


def _select_diverse_template(gap: dict, prior_hypotheses: list[dict] | None = None) -> str:
    """Select a template that hasn't been used yet this session."""
    preferred = select_template(gap)
    if not prior_hypotheses:
        return preferred

    used_templates = {h.get("template", "") for h in prior_hypotheses}
    # If preferred template already used, rotate through alternatives
    if preferred not in used_templates:
        return preferred

    all_templates = list(TEMPLATES.keys())
    for t in all_templates:
        if t not in used_templates:
            return t
    # All templates used — fall back to preferred
    return preferred


def _try_llm_hypothesis(
    gap: dict,
    hypothesis_id: str,
    prior_hypotheses: list[dict] | None = None,
) -> Hypothesis | None:
    """Attempt LLM-powered hypothesis generation. Returns None on failure."""
    try:
        import sys
        _llm_dir = str(Path(__file__).parent.parent / "sol-llm")
        if _llm_dir not in sys.path:
            sys.path.insert(0, _llm_dir)

        from client import SolLLM
        if not SolLLM.is_available():
            return None

        from prompts import PromptLibrary

        # Assemble knowledge context from proof packets
        knowledge_ctx = _gather_knowledge_context(gap)

        # Get available template catalog for the LLM
        template_catalog = list_templates()

        system, user = PromptLibrary.hypothesis(
            gap=gap,
            knowledge_context=knowledge_ctx,
            prior_hypotheses=prior_hypotheses or [],
            available_templates=template_catalog,
        )

        llm = SolLLM(verbose=True)
        response = llm.complete_json(user, system=system, task="hypothesis")

        if not response.success or not response.parsed:
            return None

        data = response.parsed

        # Convert LLM output to Hypothesis dataclass
        return Hypothesis(
            id=hypothesis_id,
            template=f"llm_{select_template(gap)}",
            question=data.get("question", "LLM-generated hypothesis"),
            knob=data.get("knob"),
            knob_values=data.get("knob_values", []),
            injection=data.get("injection", {"label": "grail", "amount": 50}),
            steps=data.get("steps", 200),
            reps=data.get("reps", 3),
            falsifiers=data.get("falsifiers", []),
            notes=f"LLM-generated | Rationale: {data.get('rationale', 'N/A')[:200]}",
            source_gap=gap,
        )

    except Exception:
        # Any failure — silently fall back to template
        return None


def _gather_knowledge_context(gap: dict, max_chars: int = 3000) -> str:
    """Pull relevant knowledge context for LLM hypothesis generation."""
    from pathlib import Path

    sol_root = Path(__file__).parent.parent.parent
    pp_dir = sol_root / "solKnowledge" / "proof_packets"
    domains_dir = pp_dir / "domains"

    context_parts = []
    claim_id = gap.get("claim_id", "")
    desc_lower = gap.get("description", "").lower()

    # Search both domains/ and root proof_packets/
    search_dirs = []
    if domains_dir.is_dir():
        search_dirs.append(domains_dir)
    if pp_dir.is_dir():
        search_dirs.append(pp_dir)

    for search_dir in search_dirs:
        for packet in sorted(search_dir.glob("*.md")):
            try:
                text = packet.read_text(encoding="utf-8")
                # If gap references a specific claim, find that section
                if claim_id and claim_id in text:
                    lines = text.split("\n")
                    for i, line in enumerate(lines):
                        if claim_id in line:
                            start = max(0, i - 2)
                            end = min(len(lines), i + 5)
                            context_parts.append(
                                f"[{packet.name}]\n"
                                + "\n".join(lines[start:end])
                            )
                            break
                # Also match on keywords from gap description
                elif any(kw in text.lower() for kw in desc_lower.split()[:5] if len(kw) > 4):
                    header = "\n".join(text.split("\n")[:15])
                    context_parts.append(f"[{packet.name}]\n{header}")
            except Exception:
                pass

    result = "\n---\n".join(context_parts)
    return result[:max_chars]


def list_templates() -> list[dict]:
    """List all available templates with their docs."""
    return [
        {"name": t["name"], "description": t["doc"].strip().split("\n")[0]}
        for t in TEMPLATES.values()
    ]
