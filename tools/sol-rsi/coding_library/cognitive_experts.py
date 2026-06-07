# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Holographic Memory & Recall Expert Team
==============================================
Specialized agents operating to manage phase-aligned Resonant Attention maps,
H-CAM content-addressable memory recall, and multi-port query superposition.
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

class LuminaResonantAttentionExpert(LuminaExpert):
    """Expert in phase-coherent Multi-Head Resonant Attention (MHRA) and weight alignment."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Resonant Attention Expert. You specialize in modeling phase-coherent attention alignments for the\n"
            "Multi-Head Resonant Attention (MHRA) layer. You recommend attention phase maps (weights w0, w1) and configure query/key/value\n"
            "wave matrices to prevent attention-sink collapse and ensure that semantic mass constructively concentrates at target conceptual nodes."
        )
        super().__init__("SOL Resonant Attention Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("holographic_bus_reference")
        return doc if doc else "No holographic bus reference documentation found."


class LuminaHcamRecallExpert(LuminaExpert):
    """Expert in Holographic Content-Addressable Memory (H-CAM) recall and phase superposition."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL H-CAM Recall Expert. You specialize in modeling Holographic Content-Addressable Memory (H-CAM) associative lookups.\n"
            "You formulate multi-port phase superposition keys, detailing how multiple database queries are broadcast simultaneously and resolved\n"
            "without crosstalk by matching phase coherence signatures at the target memory gates."
        )
        super().__init__("SOL H-CAM Recall Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("holographic_bus_reference")
        return doc if doc else "No holographic bus reference documentation found."


class CognitiveExpertTeam:
    """Orchestrates routing and cooperation among the Holographic Memory & Recall Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)

        self.experts: Dict[str, LuminaExpert] = {
            "resonant_attention": LuminaResonantAttentionExpert(self.lib_agent),
            "hcam_recall": LuminaHcamRecallExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific Cognitive expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown Cognitive expert '{expert_name}'. Available: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Cognitive Expert Team CLI")
    ap.add_argument("--expert", choices=["resonant_attention", "hcam_recall"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = CognitiveExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
