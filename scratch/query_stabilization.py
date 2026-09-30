# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Consultation script to query Coding Library Experts on Level 11 PDM stabilization
and scaling to 32-bit and 64-bit computing.
"""

import sys
from pathlib import Path

# Resolve paths
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "tools" / "sol-llm"))
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))

from coding_library import LuminaLibraryAgent

def main():
    agent = LuminaLibraryAgent()

    failure_log = """
Starting automatic phase calibration for Level 11 PDM...
  Calibrating frequency channel period 10.0...
    Sine Match (Bit 0):   phase = 1.047198 (0.3333 * pi), max_delta = +29.7846
    Cosine Match (Bit 1): phase = 5.759587 (1.8333 * pi), max_delta = +24.9827
  Calibrating frequency channel period 14.0...
    Sine Match (Bit 2):   phase = 5.235988 (1.6667 * pi), max_delta = +20.7999
    Cosine Match (Bit 3): phase = 5.759587 (1.8333 * pi), max_delta = +20.7875
  Calibrating frequency channel period 18.0...
    Sine Match (Bit 4):   phase = 1.570796 (0.5000 * pi), max_delta = +1.9632
    Cosine Match (Bit 5): phase = 0.000000 (0.0000 * pi), max_delta = -3.4645
  Calibrating frequency channel period 22.0...
    Sine Match (Bit 6):   phase = 0.000000 (0.0000 * pi), max_delta = -3.6334
    Cosine Match (Bit 7): phase = 2.094395 (0.6667 * pi), max_delta = -2.4285
PDM Phase Calibration Complete.
"""

    question_template = f""" We are running Level 11 Phase-Division Multiplexing (PDM) on the SOL substrate to establish 16-bit computing, but periods 18.0 and 22.0 show severe calibration degradation (negative or very low deltas).
Here is the calibration log:
{{failure_log}}

As a specialized expert in the SOL ecosystem:
1. Explain physically why the longer periods (18.0 and 22.0) fail to calibrate (e.g. damping timescale, wave reflection limits, or resonance wall issues).
2. Propose concrete parameter modifications (damping coefficient gamma, periods list, manifold dimensions, or simulation time step dt) to stabilize 16-bit PDM.
3. Outline what architectural or physical features are hidden in the SOL substrate that we must leverage or implement to reach the next milestone of 32-bit and 64-bit computing.
"""

    experts_to_query = [
        ("substrate", "Substrate Physics Expert"),
        ("vertical", "Vertical Scaling Expert"),
        ("horizontal", "Horizontal Routing Expert"),
        ("giants", "Exciton-MOA Giants Expert")
    ]

    print("==========================================================================")
    print("  CONSULTING SOL EXPERTS ON LEVEL 11 PDM STABILIZATION & SCALING")
    print("==========================================================================\n")

    responses = {}
    for key, name in experts_to_query:
        print(f"Querying the {name}...")
        q = question_template.format(failure_log=failure_log)
        ans = agent.ask_expert(key, q)
        responses[key] = ans
        print(f"--- {name} Response ---\n{ans}\n")

    # Save findings as an artifact
    findings_dir = sol_root / "solResearch" / "activeResearch" / "notes"
    findings_dir.mkdir(parents=True, exist_ok=True)
    findings_file = findings_dir / "pdm_stabilization_discoveries.md"

    with open(findings_file, "w", encoding="utf-8") as f:
        f.write("# PDM Stabilization & Scaling Discoveries\n\n")
        f.write("This document compiles expert advice from the Multi-Team SOL Expert Ecosystem on resolving Level 11 16-bit PDM calibration failures and preparing the system for 32-bit and 64-bit milestones.\n\n")
        
        for key, name in experts_to_query:
            f.write(f"## Advice from the {name}\n\n")
            f.write(responses[key])
            f.write("\n\n---\n\n")

    print(f"Saved compiled discoveries to: {findings_file.resolve()}")

if __name__ == "__main__":
    main()
