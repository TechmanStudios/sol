# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Subsystem Verification & Proof Expert Team
=================================================
Specialized agents operating to perform static safety analysis, liveness checks,
mass preservation bounds checking, and formal circuit proof generation.
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

class LuminaMassSentinelExpert(LuminaExpert):
    """Expert in static liveness analysis and register mass preservation safety checks."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Liveness & Mass Sentinel Expert. You specialize in static compiler safety and liveness analysis.\n"
            "You scan compiled Logos VM instruction sequences to identify potential mass leak points (such as loops without SETTLE commands\n"
            "or excessive consecutive ALU gate activations) and statically prove that active registers (A, B, C, D) strictly preserve their\n"
            "required density threshold (rho >= 14.0) under all execution branches."
        )
        super().__init__("SOL Liveness & Mass Sentinel Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("compiler_reference")
        return doc if doc else "No compiler reference documentation found."


class LuminaCircuitProoferExpert(LuminaExpert):
    """Expert in formal logic verification and state-space circuit proofs."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Circuit Proofer Expert. You specialize in formal logic verification and state-space correctness proofs.\n"
            "You formulate boolean equations for composite synthesized components, trace truth tables, verify logical correctness,\n"
            "and write formal verification assertions for ALUs, adders, and latches without relying on trial-and-error simulation."
        )
        super().__init__("SOL Circuit Proofer Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        # Load registry and verified components as context
        registry = self.lib_agent.registry
        context_lines = ["### Verified Component Registry:\n"]
        for name, info in registry.items():
            context_lines.append(f"- **{name}**: {info.get('verification_status', 'UNVERIFIED')}")
        return "\n".join(context_lines)


class VerificationExpertTeam:
    """Orchestrates routing and cooperation among the Subsystem Verification & Proof Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)

        self.experts: Dict[str, LuminaExpert] = {
            "mass_sentinel": LuminaMassSentinelExpert(self.lib_agent),
            "circuit_proofer": LuminaCircuitProoferExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific Verification expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown Verification expert '{expert_name}'. Available: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Verification Expert Team CLI")
    ap.add_argument("--expert", choices=["mass_sentinel", "circuit_proofer"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = VerificationExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
