from __future__ import annotations

from .models import GateDecision, ScoreCard


class Gatekeeper:
    def __init__(self, min_anchor_delta: float = 0.01, max_full_regression: float = 0.0):
        self.min_anchor_delta = min_anchor_delta
        self.max_full_regression = max_full_regression

    def decide(
        self,
        baseline_full: ScoreCard,
        candidate_full: ScoreCard,
        baseline_anchor: ScoreCard,
        candidate_anchor: ScoreCard,
    ) -> GateDecision:
        delta_anchor = candidate_anchor.aggregate - baseline_anchor.aggregate
        delta_full = candidate_full.aggregate - baseline_full.aggregate

        if delta_anchor < self.min_anchor_delta:
            return GateDecision(
                accepted=False,
                reason=f"Anchor delta {delta_anchor:.4f} below minimum {self.min_anchor_delta:.4f}",
                delta_anchor_score=delta_anchor,
                delta_full_score=delta_full,
            )

        if delta_full < self.max_full_regression:
            return GateDecision(
                accepted=False,
                reason=f"Full-task delta {delta_full:.4f} below allowed floor {self.max_full_regression:.4f}",
                delta_anchor_score=delta_anchor,
                delta_full_score=delta_full,
            )

        return GateDecision(
            accepted=True,
            reason="Candidate clears anchor and full-task thresholds",
            delta_anchor_score=delta_anchor,
            delta_full_score=delta_full,
        )
