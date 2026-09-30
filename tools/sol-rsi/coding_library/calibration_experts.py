# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Metrology & Calibration Expert Team
==========================================
Specialized agents operating to tune phase calibration, measure frequency drift,
and configure Perfectly Matched Layer (PML) boundary parameters.
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

class LuminaPhaseCalibrationExpert(LuminaExpert):
    """Expert in measuring and correcting phase drift, frequency coupling, and temporal scaling."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Phase Calibration Expert. You specialize in analyzing coupled analog/dynamical simulation traces\n"
            "to detect, measure, and correct phase drift, frequency coupling, and temporal accumulation errors on the Holographic Bus (P_Bus).\n"
            "You recommend dynamic phase angle adjustments (e.g. shifts by fractions of pi or specific offsets like 0.75 * pi) and temporal step\n"
            "size (dt) overrides to maintain wave orthogonality and prevent phase-division multiplexing signal overlap."
        )
        super().__init__("SOL Phase Calibration Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("holographic_bus_reference")
        return doc if doc else "No holographic bus reference documentation found."


class LuminaAcousticImpedanceExpert(LuminaExpert):
    """Expert in modeling Perfectly Matched Layer (PML) boundary conditions and wave reflection damping."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the SOL Acoustic Impedance Expert. You specialize in boundary physics, wave reflection damping, and impedance matching.\n"
            "You diagnose standing wave interference patterns and back-reflection noise on the waveguide. You recommend Perfectly Matched Layer (PML)\n"
            "absorbing boundary widths, boundary damping decay variables (gamma_boundary), and matching gate structures to optimize conductance\n"
            "and prevent mass dissipation or signal attenuation."
        )
        super().__init__("SOL Acoustic Impedance Expert", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("substrate_reference")
        return doc if doc else "No substrate reference documentation found."


class CalibrationExpertTeam:
    """Orchestrates routing and cooperation among the Metrology & Calibration Experts."""

    def __init__(self, library_dir: Optional[Path] = None):
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        self.lib_agent = LuminaLibraryAgent(library_dir=library_dir)

        self.experts: Dict[str, LuminaExpert] = {
            "phase_calibration": LuminaPhaseCalibrationExpert(self.lib_agent),
            "acoustic_impedance": LuminaAcousticImpedanceExpert(self.lib_agent)
        }

    def ask_expert(self, expert_name: str, question: str, context_details: Optional[Dict[str, Any]] = None) -> str:
        """Route a query to a specific Metrology & Calibration expert agent."""
        expert_key = expert_name.lower().strip()
        if expert_key not in self.experts:
            return f"Error: Unknown Calibration expert '{expert_name}'. Available: {list(self.experts.keys())}"
        return self.experts[expert_key].query(question, context_details)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Calibration Expert Team CLI")
    ap.add_argument("--expert", choices=["phase_calibration", "acoustic_impedance"], required=True, help="Expert to query")
    ap.add_argument("--query", required=True, help="Question to ask the expert")
    args = ap.parse_args()

    team = CalibrationExpertTeam()
    ans = team.ask_expert(args.expert, args.query)
    print(ans)
