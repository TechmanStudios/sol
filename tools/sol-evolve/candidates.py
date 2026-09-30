"""
SOL Evolve — Code Change Candidate System
============================================
Structured templates for proposing modifications to the SOL engine.

SACRED MATH RULE: The core physics equations (pressure, flux, damping,
psi diffusion, conductance, CapLaw) are NEVER modified by candidates.
Candidates can only modify:
  - Configuration parameters (battery_cfg, phase_cfg, etc.)
  - Pre/post step hooks (additional computations)
  - Graph topology (add/remove/reweight edges)

Each candidate declares:
  - What it changes
  - Why (hypothesis)
  - What metrics it expects to improve
  - What regressions it considers acceptable

Usage:
    from candidates import list_candidates, load_candidate, apply_candidate
    for c in list_candidates():
        print(c["name"], c["description"])
    candidate = load_candidate("tune_conductance_gamma")
    modified_engine = apply_candidate(engine, candidate)
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_HERE = Path(__file__).parent


# ---------------------------------------------------------------------------
# Candidate schema
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    """A proposed code change to the SOL engine."""
    name: str
    description: str
    hypothesis: str                          # Why this change might help
    change_type: str                         # "param_tune", "hook", "topology"
    target: str                              # What's being changed
    parameters: dict = field(default_factory=dict)  # Change parameters
    expected_improvements: list[str] = field(default_factory=list)
    acceptable_regressions: list[str] = field(default_factory=list)
    sacred_math_impact: str = "none"         # "none", "indirect", "FORBIDDEN"
    apply_fn: Callable | None = None         # Function to apply the change

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "description": self.description,
            "hypothesis": self.hypothesis,
            "change_type": self.change_type,
            "target": self.target,
            "parameters": self.parameters,
            "expected_improvements": self.expected_improvements,
            "acceptable_regressions": self.acceptable_regressions,
            "sacred_math_impact": self.sacred_math_impact,
        }
        return d


# ---------------------------------------------------------------------------
# Candidate registry
# ---------------------------------------------------------------------------

CANDIDATES: dict[str, Candidate] = {}


def register(candidate: Candidate):
    """Register a candidate in the global registry."""
    CANDIDATES[candidate.name] = candidate
    return candidate


def _apply_param_tune(engine, candidate: Candidate):
    """Apply a parameter tuning candidate."""
    target = candidate.target
    params = candidate.parameters

    for key, value in params.items():
        parts = key.split(".")
        obj = engine.physics

        # Navigate to the right config dict
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                obj = obj[part]
            else:
                raise ValueError(f"Cannot navigate to {key}: {part} not found")

        # Set the value
        final_key = parts[-1]
        if isinstance(obj, dict):
            obj[final_key] = value
        elif hasattr(obj, final_key):
            setattr(obj, final_key, value)
        else:
            raise ValueError(f"Cannot set {key}: {final_key} not found on {type(obj)}")


# ---------------------------------------------------------------------------
# Built-in candidate templates
# ---------------------------------------------------------------------------

# --- 1. Conductance gamma tuning ---
register(Candidate(
    name="tune_conductance_gamma_up",
    description="Increase conductance psi-sensitivity from 0.75 to 1.0",
    hypothesis="Higher gamma should make psi routing more selective, potentially sharpening basin formation.",
    change_type="param_tune",
    target="conductance",
    parameters={"conductance_gamma": 1.0},
    expected_improvements=["Sharper entropy gradients between basins", "Faster basin lock-in"],
    acceptable_regressions=["Slightly lower total flux (more selective routing)"],
    sacred_math_impact="none",
    apply_fn=_apply_param_tune,
))

register(Candidate(
    name="tune_conductance_gamma_down",
    description="Decrease conductance psi-sensitivity from 0.75 to 0.5",
    hypothesis="Lower gamma should make flow more uniform, potentially improving mass distribution.",
    change_type="param_tune",
    target="conductance",
    parameters={"conductance_gamma": 0.5},
    expected_improvements=["More even mass distribution", "Higher active node count"],
    acceptable_regressions=["Slower basin formation"],
    sacred_math_impact="none",
    apply_fn=_apply_param_tune,
))

# --- 2. Battery configuration tuning ---
register(Candidate(
    name="tune_battery_flip_threshold",
    description="Lower battery flip threshold from 0.85 to 0.70",
    hypothesis="Lower threshold should make lighthouses flip earlier, creating more dynamic cycling.",
    change_type="param_tune",
    target="battery_cfg",
    parameters={"battery_cfg.flipThreshold": 0.70},
    expected_improvements=["More frequent lighthouse cycling", "Higher total flux"],
    acceptable_regressions=["Potentially less stable basin states"],
    sacred_math_impact="none",
    apply_fn=_apply_param_tune,
))

register(Candidate(
    name="tune_battery_resonance_boost",
    description="Increase resonance boost from 1.8 to 2.5",
    hypothesis="Higher resonance boost amplifies aligned flow, potentially creating stronger attractor basins.",
    change_type="param_tune",
    target="battery_cfg",
    parameters={"battery_cfg.resonanceBoost": 2.5},
    expected_improvements=["Stronger basin differentiation", "Higher peak rho at attractors"],
    acceptable_regressions=["More mass concentration (lower entropy)"],
    sacred_math_impact="none",
    apply_fn=_apply_param_tune,
))

# --- 3. Psi diffusion tuning ---
register(Candidate(
    name="tune_psi_diffusion_up",
    description="Increase psi diffusion from 0.6 to 0.9",
    hypothesis="Faster psi diffusion should create smoother belief landscapes, enabling longer-range routing.",
    change_type="param_tune",
    target="psi",
    parameters={"psi_diffusion": 0.9},
    expected_improvements=["More spatially coherent psi field", "Broader activation patterns"],
    acceptable_regressions=["May reduce psi contrast between regions"],
    sacred_math_impact="none",
    apply_fn=_apply_param_tune,
))

register(Candidate(
    name="tune_psi_relax_base",
    description="Increase psi relax rate from 0.12 to 0.20",
    hypothesis="Faster relaxation toward bias should help nodes return to baseline psi quicker.",
    change_type="param_tune",
    target="psi",
    parameters={"psi_relax_base": 0.20},
    expected_improvements=["Faster recovery after perturbation", "More distinct group boundaries"],
    acceptable_regressions=["Less dynamic psi response to injections"],
    sacred_math_impact="none",
    apply_fn=_apply_param_tune,
))

# --- 4. Phase gating tuning ---
register(Candidate(
    name="tune_phase_omega",
    description="Increase lighthouse frequency from 0.15 to 0.25",
    hypothesis="Faster oscillation should create more frequent surface/deep exchange, potentially improving mixing.",
    change_type="param_tune",
    target="phase_cfg",
    parameters={"phase_cfg.omega": 0.25},
    expected_improvements=["More even mass distribution", "Faster convergence"],
    acceptable_regressions=["May reduce phase-gated separation effects"],
    sacred_math_impact="none",
    apply_fn=_apply_param_tune,
))

# --- 5. MHD tuning ---
register(Candidate(
    name="tune_mhd_build_rate",
    description="Increase magnetic field build rate from 0.10 to 0.20",
    hypothesis="Faster B-field buildup should create stronger flow channels, amplifying dominant pathways.",
    change_type="param_tune",
    target="mhd_cfg",
    parameters={"mhd_cfg.bBuild": 0.20},
    expected_improvements=["Stronger flow channeling", "More distinct dominant edges"],
    acceptable_regressions=["May lock in early pathways too quickly"],
    sacred_math_impact="none",
    apply_fn=_apply_param_tune,
))

# --- 6. Jeans collapse tuning ---
register(Candidate(
    name="tune_jeans_critical",
    description="Lower Jeans critical threshold from 18.0 to 12.0",
    hypothesis="Lower Jcrit should trigger stellar collapse earlier, creating more semantic stars.",
    change_type="param_tune",
    target="jeans_cfg",
    parameters={"jeans_cfg.Jcrit": 12.0},
    expected_improvements=["More constellations formed", "Earlier semantic mass reinforcement"],
    acceptable_regressions=["More nodes becoming stellar may over-accrete"],
    sacred_math_impact="none",
    apply_fn=_apply_param_tune,
))


# ---------------------------------------------------------------------------
# Programmatic candidate generation
# ---------------------------------------------------------------------------

def generate_sweep_candidates(target_param: str, values: list,
                               config_path: str | None = None,
                               hypothesis: str = "") -> list[Candidate]:
    """Generate a set of candidates sweeping a single parameter.

    Args:
        target_param: Parameter to sweep (e.g., "conductance_gamma")
        values: List of values to try
        config_path: Dotted path to config dict (e.g., "battery_cfg.flipThreshold")
        hypothesis: Why this sweep matters

    Returns:
        List of Candidate objects, one per value.
    """
    path = config_path or target_param
    candidates = []

    for val in values:
        c = Candidate(
            name=f"sweep_{target_param}_{val}",
            description=f"Set {target_param} = {val}",
            hypothesis=hypothesis or f"Testing {target_param} = {val} for sensitivity.",
            change_type="param_tune",
            target=target_param,
            parameters={path: val},
            expected_improvements=[f"Understand effect of {target_param}={val}"],
            acceptable_regressions=["Within 10% of golden on all metrics"],
            sacred_math_impact="none",
            apply_fn=_apply_param_tune,
        )
        candidates.append(c)

    return candidates


# ---------------------------------------------------------------------------
# Apply & list
# ---------------------------------------------------------------------------

def apply_candidate(engine, candidate: Candidate):
    """Apply a candidate modification to an engine (mutates in place).

    Returns the modified engine for chaining.
    """
    if candidate.sacred_math_impact == "FORBIDDEN":
        raise ValueError(
            f"Candidate '{candidate.name}' has sacred_math_impact=FORBIDDEN. "
            "Cannot apply without human approval.")

    if candidate.apply_fn:
        candidate.apply_fn(engine, candidate)
    elif candidate.change_type == "param_tune":
        _apply_param_tune(engine, candidate)
    else:
        raise ValueError(f"No apply function for candidate type: {candidate.change_type}")

    return engine


def list_candidates() -> list[dict]:
    """List all registered candidates."""
    return [c.to_dict() for c in CANDIDATES.values()]


def load_candidate(name: str) -> Candidate:
    """Load a registered candidate by name."""
    if name not in CANDIDATES:
        raise KeyError(f"Candidate '{name}' not found. Available: {list(CANDIDATES.keys())}")
    return CANDIDATES[name]
