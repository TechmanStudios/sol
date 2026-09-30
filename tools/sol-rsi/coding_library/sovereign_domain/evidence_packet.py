# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Sovereign Packet Dataclass
==========================
Defines standard evidence structure for all agent/ranger diagnostic claims,
checked invariants, reproducibility hashes, and promotion recommendations.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Literal

@dataclass
class SovereignPacket:
    packet_id: str
    domain: str
    level: int
    actor: str
    actor_type: Literal["agent", "ranger", "team", "court"]
    mission_id: str
    claim: str
    evidence: Dict[str, Any]
    invariants_checked: List[str]
    artifacts: List[str]
    recommendation: Literal[
        "observe",
        "patch",
        "promote",
        "reject",
        "quarantine",
        "rerun",
        "escalate"
    ]
    confidence: float
    reproducibility_hash: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the packet to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SovereignPacket":
        """Deserialize the packet from a dictionary."""
        return cls(**data)
