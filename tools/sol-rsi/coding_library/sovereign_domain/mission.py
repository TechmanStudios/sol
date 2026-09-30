# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Ranger Mission Dataclass
========================
Defines target contexts, levels, objectives, allowed/forbidden actions, TTL,
required evidence artifacts, and escalation policies for mobile rangers.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any

@dataclass
class RangerMission:
    mission_id: str
    target: str
    level: int
    objective: str
    allowed_actions: List[str]
    forbidden_actions: List[str]
    ttl_steps: int
    required_artifacts: List[str]
    escalation_policy: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the mission to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RangerMission":
        """Deserialize the mission from a dictionary."""
        return cls(**data)
