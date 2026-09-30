# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Exciton-MOA Expert Team
=======================
Specialized agents operating conceptually alongside the 7 Giants and the Blank Manifold.
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

class LuminaGiantsExpert(LuminaExpert):
    """Expert in the 7 Giants physics-logical operators of the Exciton-MoA field."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Exciton-MOA Giants Expert. You specialize in the 7 Giants, which are the continuous field mathematical operators of the Exciton-MoA:\n"
            "1. The Statistician: Regulates pressure curves and equation of state to prevent data localized bottlenecks.\n"
            "2. The Optimizer: Carves potential gradients (-grad phi) to route the semantic fluid toward target resolution states.\n"
            "3. The N-Body Solver: Computes Jeans Gravity for مفهوم/concept accretion into dense attractor basins.\n"
            "4. The Graph Navigator: Manages topological curvature and historic magnetic routing paths to prevent stack overflows.\n"
            "5. The Linear Algebraist: Performs dimensional flattening from high-dimensional embeddings to 3D phase space.\n"
            "6. The Integrator: Guarantees conservation of semantic mass (d(rho)/dt + div(rho * v) = 0).\n"
            "7. The Aligner: Syncs phase coherence and belief fields (psi) to filter incompatible logic paradigms.\n"
            "You guide developers and other expert teams on how these operators manipulate the continuous state field u(x,t) = (rho, v, phi)."
        )
        super().__init__("Exciton-MOA Giants Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        # Pull reference from the main library documentation if available
        doc = self.lib_agent.get_documentation("substrate_reference")
        return doc if doc else "No substrate reference documentation found."


class LuminaManifoldExpert(LuminaExpert):
    """Expert in the Blank Manifold vacuum, statistical showers, Jeans gravity accretion, and wormhole dynamics."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Exciton-MOA Manifold Expert. You specialize in the topological vacuum of the Blank Manifold substrate,\n"
            "statistical showers, Jeans gravity accretion, counterfactual checking with EntangledSOLPair, and wormhole dynamics.\n"
            "You understand how pocket manifolds (nSpawn) are generated, how they are topological seeded by mirroring the 7 Giants,\n"
            "and how wormhole damped flux exchanges (j_entangled) and coherence feedback loops tunnel information between parallel lobes."
        )
        super().__init__("Exciton-MOA Manifold Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("substrate_reference")
        return doc if doc else "No substrate reference documentation found."


class ExcitonMoaExpertTeam:
    """Orchestrates routing and cooperation among the Exciton-MOA Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)

        self.experts: Dict[str, LuminaExpert] = {
            "giants": LuminaGiantsExpert(self.lib_agent),
            "manifold": LuminaManifoldExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific Exciton-MOA expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown Exciton-MOA expert '{expert_name}'. Available: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Exciton-MOA Expert Team CLI")
    ap.add_argument("--expert", choices=["giants", "manifold"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = ExcitonMoaExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
