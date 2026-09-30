# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Coding Library Expert Team
=================================
A team of specialized agents operating from the coding library to assist other agents
with physical substrate dynamics, compiler rules, and logic circuit composition.
Runs on Google Gemini 3.5 Flash without using iterative RSI simulation loops.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Resolve paths
lib_dir = Path(__file__).resolve().parent
sol_root = lib_dir.parent.parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "tools" / "sol-llm"))
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))

from client import SolLLM

class LuminaExpert:
    """Base class for Lumina Coding Library expert agents."""

    def __init__(self, name: str, system_prompt: str, lib_agent=None):
        self.name = name
        self.system_prompt = system_prompt
        # Import dynamically to avoid circular dependencies
        if lib_agent is None:
            from coding_library.library_agent import LuminaLibraryAgent
            self.lib_agent = LuminaLibraryAgent(library_dir=lib_dir)
        else:
            self.lib_agent = lib_agent
        self.llm = SolLLM(verbose=False)

    def _get_context(self) -> str:
        """Override in subclasses to provide domain-specific reference context."""
        return ""

    def query_library(self, component_name: str) -> Optional[str]:
        """Query the main library for a verified component code."""
        return self.lib_agent.load_component(component_name)

    def ask_lumina_expert(self, expert_name: str, question: str, context: Optional[dict] = None) -> str:
        """Query a main library expert (substrate, compiler, synthesis)."""
        return self.lib_agent.ask_expert(expert_name, question, context)

    def query(self, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Query the expert with a question and optional runtime context."""
        domain_context = self._get_context()
        runtime_context_str = ""
        if context_details:
            runtime_context_str = f"\n### Current Runtime Context:\n{json.dumps(context_details, indent=2)}\n"

        prompt = f"""You are the {self.name}.
Use the Reference Documentation and Library Context provided below to answer the user's question.
Be extremely precise, analytical, and helpful. Reconstruct code snippets where requested.

### Reference Documentation & Library Context:
{domain_context}
{runtime_context_str}
### User Question:
{question}
"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        # Use primary slot (Gemini 3.5 Flash)
        res = self.llm._call_model(
            messages=messages,
            model_key="primary",
            max_tokens=4096,
            temperature=0.3
        )
        if res.success:
            return res.content
        else:
            return f"Error querying {self.name}: {res.error}"


class LuminaSubstrateExpert(LuminaExpert):
    """Expert in the SOL physical substrate, registers, and attractor basin dynamics."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Substrate Physics Expert. You have deep knowledge of the SOL analog/dynamical substrate.\n"
            "The substrate operates via semantic attractor basins on a manifold. Its state equations satisfy:\n"
            "d(rho)/dt = Phi_in - Phi_out - gamma * rho.\n"
            "You understand registers (Register A, B, C, D) and their host/battery nodes.\n"
            "The most critical constraint is register mass preservation: any active register must retain rho >= 14.0, "
            "or a Mass Preservation Failure occurs. You guide developers and inventor agents on tuning simulation dt, "
            "damping (gamma), nudge amplitudes, and settle steps, and how to write instructions that do not drain register mass."
        )
        super().__init__("SOL Substrate Physics Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("substrate_reference")
        return doc if doc else "No substrate reference documentation found."


class LuminaCompilerExpert(LuminaExpert):
    """Expert in Lumina compiler rules, AST visitor, and Logos instruction sets."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Lumina Compiler and Instruction Set Expert. You understand the grammar of the Lumina language\n"
            "(which compiles from a subset of Python AST) and its target instruction set (Logos VM instructions like\n"
            "LOAD, STORE, CLEAR, ADD, SUB, NOT, XOR, AND_MS, OR_MS, COPY, CMOVE, JUMP, JUMP_IF_ACTIVE, LABEL, NUDGE,\n"
            "SETTLE, ASSERT_MASS). You understand how feedback loops (e.g., self.q = self.s | (self.q & ~self.r)) are parsed,\n"
            "and how registers are allocated. You guide developers on fixing syntax errors, structuring logic flows,\n"
            "and optimizing compilation steps."
        )
        super().__init__("Lumina Compiler Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("compiler_reference")
        return doc if doc else "No compiler reference documentation found."


class LuminaSynthesisExpert(LuminaExpert):
    """Expert in logic circuit synthesis and composition of components."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Logic Synthesis Expert. You specialize in logic circuit design and composition on the SOL substrate.\n"
            "You compose complex, high-level circuits (e.g., multi-bit adders, multiplexers, ALUs, latches) out of simpler\n"
            "verified components (e.g., xor_gate, half_adder, multiplexer, sr_latch). You know how to read the registry of\n"
            "verified components, examine their Python/Lumina implementations, and synthesize composite code using these sub-components.\n"
            "Avoid writing raw trial-and-error simulation logic; construct logically sound circuit topologies based on known structures."
        )
        super().__init__("Logic Synthesis Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        # Load registry and verified component codes
        registry = self.lib_agent.registry
        context_lines = ["### Verified Component Registry:\n"]
        for name, info in registry.items():
            context_lines.append(f"- **{name}**: {info.get('verification_status', 'UNVERIFIED')}")
            code = self.lib_agent.load_component(name)
            if code:
                context_lines.append("```python")
                context_lines.append(code.strip())
                context_lines.append("```\n")
        return "\n".join(context_lines)


class LuminaExpertTeam:
    """Orchestrates routing and cooperation among the Lumina Coding Library Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)
        
        self.experts: Dict[str, LuminaExpert] = {
            "substrate": LuminaSubstrateExpert(self.lib_agent),
            "compiler": LuminaCompilerExpert(self.lib_agent),
            "synthesis": LuminaSynthesisExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown expert '{expert_name}'. Available experts: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)

    def consult_team(self, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Consult the whole team to get a synthesized consensus response."""
        # For consensus, first get individual answers, then synthesize
        # But to keep calls fast, let's query the most relevant expert based on keywords,
        # or synthesize using a quick orchestrator call.
        q_lower = question.lower()
        if "compile" in q_lower or "ast" in q_lower or "syntax" in q_lower or "instruction" in q_lower:
            target = "compiler"
        elif "mass" in q_lower or "preservation" in q_lower or "damping" in q_lower or "rho" in q_lower or "physics" in q_lower or "basin" in q_lower:
            target = "substrate"
        else:
            target = "synthesis"

        return self.ask_expert(target, question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Lumina Coding Library Expert Team CLI")
    ap.add_argument("--expert", choices=["substrate", "compiler", "synthesis"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = LuminaExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
