from __future__ import annotations

import random

from .models import Policy, Proposal


class Teacher:
    def __init__(self, knob_bounds: dict[str, tuple[float, float]], step_scale: float = 0.15):
        self.knob_bounds = knob_bounds
        self.step_scale = step_scale

    def propose(self, baseline: Policy, generation: int) -> Proposal:
        rng = random.Random(f"{baseline.policy_id}:{generation}")
        candidate_knobs = dict(baseline.knobs)

        knob_name = rng.choice(sorted(self.knob_bounds.keys()))
        lo, hi = self.knob_bounds[knob_name]
        span = hi - lo
        delta = span * self.step_scale
        direction = 1.0 if rng.random() > 0.5 else -1.0
        new_value = candidate_knobs.get(knob_name, (lo + hi) / 2.0) + direction * delta
        new_value = max(lo, min(hi, new_value))
        candidate_knobs[knob_name] = round(new_value, 6)

        candidate = Policy(
            policy_id=f"policy-g{generation:03d}",
            generation=generation,
            knobs=candidate_knobs,
        )
        rationale = f"Mutate {knob_name} by ±{delta:.3f} within bounds [{lo}, {hi}]"

        return Proposal(
            proposal_id=f"proposal-g{generation:03d}",
            parent_policy_id=baseline.policy_id,
            candidate=candidate,
            rationale=rationale,
        )
