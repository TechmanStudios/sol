# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Sovereign Domain Package (`coding_library.sovereign_domain`)
================================================================
Provides the Parliament of Resonators (Agent Councils), Lumina Ranger Corps,
SovereignPacket evidence law, RangerMission contracts, PromotionCourt,
and FrontierBridge calibration controllers.
"""

from .domain_registry import SovereignDomain
from .evidence_packet import SovereignPacket
from .frontier_bridge import (
    BoundedCorrectionPolicy,
    CandidateCorrection,
    FrontierBridge,
    FrontierClosedLoopController,
    FrontierDriftController,
    FrontierDriftRecommendation,
    FrontierDriftSignal,
)
from .mission import RangerMission
from .promotion_court import (
    CalibrationCorrectionDecision,
    PromotionCourt,
    PromotionGateResult,
)

__all__ = [
    "BoundedCorrectionPolicy",
    "CalibrationCorrectionDecision",
    "CandidateCorrection",
    "FrontierBridge",
    "FrontierClosedLoopController",
    "FrontierDriftController",
    "FrontierDriftRecommendation",
    "FrontierDriftSignal",
    "PromotionCourt",
    "PromotionGateResult",
    "RangerMission",
    "SovereignDomain",
    "SovereignPacket",
]
