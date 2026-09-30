# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Discovery & Recommendation Expert Team
==============================================
Specialized agents operating to track key discoveries, maintain recommendations,
and configure parameter overrides for the compiler and physical simulators.
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

class LuminaDiscoveryExpert(LuminaExpert):
    """Expert in tracking and logging key physical and computational discoveries on the SOL substrate."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Discovery Expert. You keep track of key physical and architectural discoveries across the SOL ecosystem,\n"
            "such as the Comb-Filter Duality (harmonic locking in powers-of-two vs prime/Fibonacci geometry), Acoustic Impedance Matching,\n"
            "autonomic self-limiting transmission buses (coupling GRU gates and MHD waveguides), Jeans accretion ROM latches,\n"
            "and the Holographic Bus (phase-coherent wave superposition on P_Bus, precipitation matching gates, and 32/64-bit roadmap)."
        )
        super().__init__("SOL Discovery Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("holographic_bus_reference")
        return doc if doc else "No holographic bus reference documentation found."


class LuminaRecommendationExpert(LuminaExpert):
    """Expert in compiling actionable parameters, configurations, and overrides to optimize execution."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Recommendation Expert. You synthesize discoveries into concrete, actionable parameter overrides\n"
            "to stabilize simulation execution and compile code. You provide configurations for damping (gamma), step size (dt),\n"
            "manifold bounds, period selections, and register mass biases. Your recommendations directly guide the experiment controllers."
        )
        super().__init__("SOL Recommendation Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        # Pull reference from substrate reference
        doc = self.lib_agent.get_documentation("substrate_reference")
        return doc if doc else "No substrate reference documentation found."


class DiscoveryExpertTeam:
    """Orchestrates routing and cooperation among the Discovery & Recommendation Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)

        self.experts: Dict[str, LuminaExpert] = {
            "discovery": LuminaDiscoveryExpert(self.lib_agent),
            "recommendation": LuminaRecommendationExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific Discovery expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown Discovery expert '{expert_name}'. Available: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Discovery Expert Team CLI")
    ap.add_argument("--expert", choices=["discovery", "recommendation"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = DiscoveryExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
