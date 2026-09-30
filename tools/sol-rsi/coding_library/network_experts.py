# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Waveguide Routing & Network Expert Team
==============================================
Specialized agents operating to manage multi-lane spatial division multiplexing,
lane arbitration via Basin_Sel, and non-linear soliton wave propagation.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Resolve paths
lib_dir = Path(__file__).resolve().parent
sol_root = lib_dir.parent.parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "tools" / "sol-llm"))
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))

from coding_library.experts import LuminaExpert

class LuminaCollisionArbitratorExpert(LuminaExpert):
    """Expert in multi-lane spatial-division multiplexing (SDM), lane routing, and scheduling."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Waveguide Collision Arbitrator Expert. You specialize in designing multi-lane spatial-division multiplexing (SDM)\n"
            "routing protocols and packet scheduling algorithms for the parallel Holographic waveguide lanes (P_Bus0 to P_Bus7).\n"
            "You recommend lane-switching arbitration strategies via selector basins (Basin_Sel), gate synchronization timings to prevent\n"
            "phase-coherent overlaps, and spatial division of 32-bit and 64-bit word streams to avoid crosstalk."
        )
        super().__init__("SOL Waveguide Collision Arbitrator Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("holographic_bus_reference")
        return doc if doc else "No holographic bus reference documentation found."


class LuminaSolitonWaveformExpert(LuminaExpert):
    """Expert in modeling non-linear Schrödinger solitary waves and dispersion control."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Soliton Waveform Expert. You specialize in modeling non-linear solitary waves (solitons) governed by the\n"
            "Non-Linear Schrödinger Equation (NLSE) to propagate high-density data wave-packets along waveguide channels without shape distortion.\n"
            "You guide developers and compiler agents on selecting amplitude envelope coefficients, dispersion-compensation ratios, and non-linear\n"
            "phase parameters to sustain long-distance signals without dissipation or decay."
        )
        super().__init__("SOL Soliton Waveform Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("holographic_bus_reference")
        return doc if doc else "No holographic bus reference documentation found."


class NetworkExpertTeam:
    """Orchestrates routing and cooperation among the Waveguide Routing & Network Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)

        self.experts: Dict[str, LuminaExpert] = {
            "collision_arbitrator": LuminaCollisionArbitratorExpert(self.lib_agent),
            "soliton_waveform": LuminaSolitonWaveformExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific Waveguide Routing & Network expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown Network expert '{expert_name}'. Available: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Network Expert Team CLI")
    ap.add_argument("--expert", choices=["collision_arbitrator", "soliton_waveform"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = NetworkExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
