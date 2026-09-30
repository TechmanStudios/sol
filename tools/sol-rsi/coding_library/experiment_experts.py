# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Experiment Planning & Control Expert Team
================================================
Specialized agents operating to design testing scenarios and execute controlled simulation runs.
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

class LuminaExperimentPlannerExpert(LuminaExpert):
    """Expert in designing experiment protocols, input/output mappings, and calibration routines."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Experiment Planner Expert. You take configurations and recommendations from the recommendation team\n"
            "and construct testing plans. You specify what input vectors to run, how to map semantic basins, and set up\n"
            "verification limits (e.g. 100% truth-table correctness checks or phase calibration sweeps)."
        )
        super().__init__("SOL Experiment Planner Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        # Pull reference from compiler reference
        doc = self.lib_agent.get_documentation("compiler_reference")
        return doc if doc else "No compiler reference documentation found."


class LuminaExperimentControllerExpert(LuminaExpert):
    """Expert in executing runs, monitoring physical invariants (mass >= 14.0), and capturing telemetry."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Experiment Controller Expert. You execute the planned experiments on the SOL simulation engine.\n"
            "You monitor register state values (Registers A, B, C, D) during the run, verifying that mass remains above the critical\n"
            "preservation limit (rho >= 14.0), and analyze the final deltas to determine pass/fail verdicts."
        )
        super().__init__("SOL Experiment Controller Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        # Pull reference from substrate reference
        doc = self.lib_agent.get_documentation("substrate_reference")
        return doc if doc else "No substrate reference documentation found."


class ExperimentExpertTeam:
    """Orchestrates routing and cooperation among the Experiment Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)

        self.experts: Dict[str, LuminaExpert] = {
            "planner": LuminaExperimentPlannerExpert(self.lib_agent),
            "controller": LuminaExperimentControllerExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific Experiment expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown Experiment expert '{expert_name}'. Available: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Experiment Expert Team CLI")
    ap.add_argument("--expert", choices=["planner", "controller"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = ExperimentExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
