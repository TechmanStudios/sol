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
    }
    
    # Special cases based on metadata
    meta = gap.get("metadata", {})
    param = meta.get("param", "")
    if param == "dt":
        return "dt_compression"
    if "psi" in param.lower():
        return "psi_sensitivity"
    
    return mapping.get(gap_type, "parameter_sweep")


def generate_hypothesis(gap: dict, hypothesis_id: str = "H-auto") -> Hypothesis:
    """Generate a hypothesis from a gap using the best-matching template."""
    template_name = select_template(gap)
    template_fn = TEMPLATES.get(template_name, {}).get("fn")
    if not template_fn:
        template_fn = TEMPLATES["parameter_sweep"]["fn"]
    
    return template_fn(gap, id=hypothesis_id)


def list_templates() -> list[dict]:
    """List all available templates with their docs."""
    return [
        {"name": t["name"], "description": t["doc"].strip().split("\n")[0]}
        for t in TEMPLATES.values()
    ]
