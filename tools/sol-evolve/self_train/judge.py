from __future__ import annotations

from .models import RunResult, ScoreCard


class Judge:
    def __init__(self, weights: dict[str, float]):
        self.weights = weights

    def score(self, policy_id: str, results: list[RunResult]) -> ScoreCard:
        per_task: dict[str, float] = {}
        for result in results:
            m = result.metrics
            task_score = (
                self.weights.get("stability", 0.0) * m.get("stability", 0.0)
                + self.weights.get("novelty", 0.0) * m.get("novelty", 0.0)
                + self.weights.get("usefulness", 0.0) * m.get("usefulness", 0.0)
                + self.weights.get("reproducibility", 0.0) * m.get("reproducibility", 0.0)
                - self.weights.get("cost", 0.0) * m.get("cost", 0.0)
            )
            per_task[result.task_id] = task_score

        aggregate = sum(per_task.values()) / max(1, len(per_task))
        return ScoreCard(policy_id=policy_id, aggregate=aggregate, per_task=per_task)
