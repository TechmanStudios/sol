"""
SOL Cortex — Protocol Generator
=================================
Converts a Hypothesis into a fully-valid protocol JSON that auto_run.py
can execute. Applies guard rails and validates constraints.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hypothesis_templates import Hypothesis

_GUARDRAILS_PATH = Path(__file__).parent / "guardrails.json"


def _load_guard_rails() -> dict:
    """Load guard rails from guardrails.json, with hardcoded fallbacks."""
    defaults = {
        "max_steps_per_run": 2000,
        "max_conditions_per_protocol": 20,
        "max_reps_per_condition": 10,
        "max_total_steps_per_session": 100_000,
        "max_protocols_per_session": 10,
    }
    if _GUARDRAILS_PATH.exists():
        raw = json.loads(_GUARDRAILS_PATH.read_text(encoding="utf-8"))
        limits = raw.get("execution_limits", {})
        defaults.update(limits)
    return defaults


GUARD_RAILS = _load_guard_rails()


class ProtocolValidationError(Exception):
    """Raised when a protocol violates guard rails."""
    pass


def hypothesis_to_protocol(hypothesis: Hypothesis,
                            invariants_override: dict | None = None) -> dict:
    """Convert a Hypothesis to a protocol JSON dict.

    Args:
        hypothesis: The hypothesis to convert.
        invariants_override: Optional overrides for invariant parameters.

    Returns:
        A valid protocol dict ready for auto_run.execute_protocol().
    """
    inv = {
        "dt": 0.12,
        "c_press": 0.1,
        "damping": 0.2,
        "rng_seed": 42,
    }
    if invariants_override:
        inv.update(invariants_override)

    protocol: dict[str, Any] = {
        "seriesName": hypothesis.id.lower().replace(" ", "_"),
        "question": hypothesis.question,
        "invariants": {},
        "injections": [hypothesis.injection] if hypothesis.injection else [{"label": "grail", "amount": 50}],
        "steps": hypothesis.steps,
        "reps": hypothesis.reps,
        "baseline": "fresh",
        "metrics_every": _auto_metrics_every(hypothesis.steps),
        "outputs": {
            "summary_csv": True,
            "trace_csv": True,
            "run_bundle_md": True,
        },
        "falsifiers": hypothesis.falsifiers,
        "notes": hypothesis.notes,
    }

    # Split invariants vs knobs
    # The knob is the parameter being swept; everything else is invariant
    if hypothesis.knob and hypothesis.knob_values:
        # The knob goes into knobs; everything else stays invariant
        knob_name = hypothesis.knob
        protocol["knobs"] = {knob_name: hypothesis.knob_values}

        # Remove the knob from invariants (if present)
        for k, v in inv.items():
            if k != knob_name:
                protocol["invariants"][k] = v
    else:
        protocol["invariants"] = dict(inv)

    # Handle injection_comparison template specially
    if hypothesis.template == "injection_comparison":
        # Multiple injection targets need separate conditions
        # For now, encode as manual multi-run (agent can loop)
        targets = hypothesis.notes.replace("Comparing targets: ", "").strip("[]").split(", ")
        targets = [t.strip().strip("'\"") for t in targets]
        protocol["_multi_injection_targets"] = targets
        protocol["notes"] += f"\nManual: run separately for each target in {targets}"

    return protocol


def validate_protocol(protocol: dict) -> list[str]:
    """Validate a protocol against guard rails. Returns list of violations."""
    violations = []

    # Step limit
    if protocol.get("steps", 0) > GUARD_RAILS["max_steps_per_run"]:
        violations.append(
            f"steps={protocol['steps']} exceeds max_steps_per_run={GUARD_RAILS['max_steps_per_run']}")

    # Condition count
    knobs = protocol.get("knobs", {})
    n_conditions = 1
    for values in knobs.values():
        n_conditions *= len(values)
    if n_conditions > GUARD_RAILS["max_conditions_per_protocol"]:
        violations.append(
            f"conditions={n_conditions} exceeds max_conditions_per_protocol={GUARD_RAILS['max_conditions_per_protocol']}")

    # Rep limit
    reps = protocol.get("reps", 1)
    if reps > GUARD_RAILS["max_reps_per_condition"]:
        violations.append(
            f"reps={reps} exceeds max_reps_per_condition={GUARD_RAILS['max_reps_per_condition']}")

    # Total steps
    total = protocol.get("steps", 0) * n_conditions * reps
    if total > GUARD_RAILS["max_total_steps_per_session"]:
        violations.append(
            f"total_steps={total} exceeds max_total_steps_per_session={GUARD_RAILS['max_total_steps_per_session']}")

    # Baseline declared
    if protocol.get("baseline") not in ("fresh", "restore"):
        violations.append("baseline mode not declared (must be 'fresh' or 'restore')")

    # Falsifiers required
    if not protocol.get("falsifiers"):
        violations.append("No falsifiers specified (at least one required)")

    # Question required
    if not protocol.get("question"):
        violations.append("No question specified")

    return violations


def generate_protocol(hypothesis: Hypothesis,
                       invariants_override: dict | None = None,
                       strict: bool = True) -> dict:
    """Generate and validate a protocol from a hypothesis.
    
    Args:
        hypothesis: The hypothesis to convert.
        invariants_override: Optional parameter overrides.
        strict: If True, raise ProtocolValidationError on violations.
    
    Returns:
        Validated protocol dict.
    """
    protocol = hypothesis_to_protocol(hypothesis, invariants_override)
    violations = validate_protocol(protocol)

    if violations and strict:
        raise ProtocolValidationError(
            f"Protocol violates guard rails:\n" + "\n".join(f"  - {v}" for v in violations))

    if violations:
        protocol["_guard_rail_warnings"] = violations

    return protocol


def _auto_metrics_every(steps: int) -> int:
    """Automatically choose metrics_every based on step count."""
    if steps <= 100:
        return 1
    if steps <= 300:
        return 5
    if steps <= 1000:
        return 10
    return 20


def save_protocol(protocol: dict, out_dir: Path) -> Path:
    """Save protocol JSON to disk."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = protocol.get("seriesName", "unnamed")
    path = out_dir / f"{name}_protocol.json"
    path.write_text(json.dumps(protocol, indent=2, default=str), encoding="utf-8")
    return path
