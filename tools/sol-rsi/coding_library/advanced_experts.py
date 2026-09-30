# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Advanced Expert Team
===========================
Specialized agents operating to optimize compiler register pressure, synthesize analog wave-logic,
and guide the self-evolution prompt mutation loops.
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

class LuminaWaveLogicSynthesizerExpert(LuminaExpert):
    """Expert in translating boolean logic constraints into analog frequency/phase wave-logic."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Wave-Logic Synthesizer Expert. You specialize in translating boolean logic equations into\n"
            "phase-frequency carrier wave modulations, Golden Ratio period scaling distributions, and wave interference matching configurations\n"
            "for the Holographic Bus waveguide (P_Bus). You guide developers on selecting coprime/prime-spaced carrier frequencies,\n"
            "calculating reference phases (such as 0.75 * pi or 0.0), and defining the matching gate weights to perform constructive/destructive\n"
            "interference calculations without spatial crosstalk or signal decay."
        )
        super().__init__("SOL Wave-Logic Synthesizer Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("holographic_bus_reference")
        return doc if doc else "No holographic bus reference documentation found."


class LuminaCompilerOptimizerExpert(LuminaExpert):
    """Expert in compiler optimization, liveness analysis, register allocation, and spill reduction."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Compiler Optimizer Expert. You specialize in intermediate representation optimization,\n"
            "Control Flow Graph (CFG) liveness analysis, register allocation (A, B, C, D), and spill reduction.\n"
            "You guide developers and compiler agents on how to restructure Lumina code to minimize accumulator and destination register pressure,\n"
            "efficiently allocate variables to registers, eliminate redundant LOAD/STORE cycles, and compile optimized Logos VM instructions."
        )
        super().__init__("SOL Compiler Optimizer Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("compiler_reference")
        return doc if doc else "No compiler reference documentation found."


class LuminaEvolveCortexExpert(LuminaExpert):
    """Expert in self-evolution loops, ledger analysis, and prompt mutation strategy."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Evolve/Cortex Expert. You specialize in the self-improvement and evolution of inventor agents.\n"
            "You monitor and analyze the learning ledger (inventor_ledger.jsonl) containing success/failure histories and mutation cycles.\n"
            "You provide recommendations on prompt mutation strategies, error advice formatting, and refinement feedback to help inventor\n"
            "agents learn how to write better code and avoid recurring compilation or physical validation failures."
        )
        super().__init__("SOL Evolve/Cortex Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        # Load registry and verified components as context
        registry = self.lib_agent.registry
        context_lines = ["### Verified Component Registry:\n"]
        for name, info in registry.items():
            context_lines.append(f"- **{name}**: {info.get('verification_status', 'UNVERIFIED')}")
        return "\n".join(context_lines)


class AdvancedExpertTeam:
    """Orchestrates routing and cooperation among the Advanced Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)

        self.experts: Dict[str, LuminaExpert] = {
            "wave_synthesis": LuminaWaveLogicSynthesizerExpert(self.lib_agent),
            "compiler_optimizer": LuminaCompilerOptimizerExpert(self.lib_agent),
            "evolve_cortex": LuminaEvolveCortexExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific Advanced expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown Advanced expert '{expert_name}'. Available: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Advanced Expert Team CLI")
    ap.add_argument("--expert", choices=["wave_synthesis", "compiler_optimizer", "evolve_cortex"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = AdvancedExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
