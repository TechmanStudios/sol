from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskSpec:
    task_id: str
    family: str
    payload: dict[str, Any] = field(default_factory=dict)
    anchor: bool = False


@dataclass
class Policy:
    policy_id: str
    generation: int
    knobs: dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class RunResult:
    policy_id: str
    task_id: str
    metrics: dict[str, float]
    elapsed_sec: float
    run_snapshot: dict[str, Any] | None = None


@dataclass
class ScoreCard:
    policy_id: str
    aggregate: float
    per_task: dict[str, float]


@dataclass
class Proposal:
    proposal_id: str
    parent_policy_id: str
    candidate: Policy
    rationale: str


@dataclass
class GateDecision:
    accepted: bool
    reason: str
    delta_anchor_score: float
    delta_full_score: float
