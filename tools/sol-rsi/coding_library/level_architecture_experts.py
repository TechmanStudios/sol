# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Level Architecture Expert Team
===================================
Specialized agents operating conceptually alongside the SOL Level Architecture (Levels 1-11+).
Enables cross-team queries to the main Lumina Coding Library.
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

class LuminaVerticalScalingExpert(LuminaExpert):
    """Expert in the hierarchical stack levels (Levels 1-11) and vertical expansion boundaries."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Level Architecture Vertical Scaling Expert. You specialize in the hierarchical stack levels (Levels 1-11) and vertical expansion boundaries:\n"
            "- Level 1: Nano-folds (Physical Cell Layer / Memristive Battery Latch)\n"
            "- Level 2: Micro-folds (Local Computational Layer / Junction Logic AND/OR, Astable Oscillators)\n"
            "- Level 3: Sub-manifolds (Memory and Routing Layer / Attractor Basins, Zero-Bleed Routing)\n"
            "- Level 4: Manifolds (Coordinated Routing & Bus Layer / Dual-Bus Broadcast, Self-Timed Handshake)\n"
            "- Level 5: Manifold-Systems (Orchestrated Architecture Layer / Gated Registers, CMOVE)\n"
            "- Level 6: Basic Software (Programmable Runtime Layer / LogosVM, Liveness Compiler)\n"
            "- Level 7: Parallel Wave-Multiplexed Substrate Processing (Multi-Core Layer / SIMD Broadcast, Carry-Select)\n"
            "- Level 8: Spectral Parallelism (Frequency-Division Multiplexed Substrate / Carrier Modulation, Resonant Gating)\n"
            "- Level 9: Holographic Content-Addressable Memory (H-CAM) & Resonant Attention (Holographic Recall, Phase-coherent Superposition)\n"
            "- Level 10: Multi-Head Resonant Attention (MHRA) & Holographic Crossbar Routing (Concurrent Crossbar Routing, Multi-port Query Superposition)\n"
            "- Level 11: Phase-Division Multiplexing (PDM) & Dual-Bus Crossbar (Phase-Division Multiplexing, Multilane Crossbar Routing)\n"
            "You guide developers and other expert teams on the interfaces between these levels, promotion gates, invariants, and rules for vertical scaling (e.g. designing Level 12 and beyond)."
        )
        super().__init__("SOL Vertical Scaling Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("substrate_reference")
        return doc if doc else "No substrate reference documentation found."


class LuminaHorizontalRoutingExpert(LuminaExpert):
    """Expert in horizontal configurations at the same level (e.g., multi-lane crossbar busses, phase routing)."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Level Architecture Horizontal Routing Expert. You specialize in horizontal configurations at the same level.\n"
            "This includes multi-lane crossbar busses, phase division multiplexing, routing protocols, channel delta sorting,\n"
            "waveguide cross-talk mitigation, and alternative horizontal configurations to optimize bandwidth and prevent congestion."
        )
        super().__init__("SOL Horizontal Routing Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("substrate_reference")
        return doc if doc else "No substrate reference documentation found."


class LevelArchitectureExpertTeam:
    """Orchestrates routing and cooperation among the Level Architecture Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)

        self.experts: Dict[str, LuminaExpert] = {
            "vertical": LuminaVerticalScalingExpert(self.lib_agent),
            "horizontal": LuminaHorizontalRoutingExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific Level Architecture expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown Level Architecture expert '{expert_name}'. Available: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Level Architecture Expert Team CLI")
    ap.add_argument("--expert", choices=["vertical", "horizontal"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = LevelArchitectureExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
