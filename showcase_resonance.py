#!/usr/bin/env python3
"""
SOL Unified Showcase & Stress Test
==================================
Runs a combined simulation that excites all system functions:
1) SOL core physics steps and density injections.
2) Pipeline orchestrator stages (smoke, cortex, consolidate, hippocampus, evolve, report).
3) Autonomous agents (Cortex, Hippocampus, RSI).
4) Frontier_OS / Exciton-MoA Operating System (Riemannian manifold, Exciton Giants, Spotlight scans).

Usage:
    python showcase_resonance.py --steps 50 --delay 0.4
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import random
from pathlib import Path

import numpy as np

# Resolve project path mappings
_ROOT = Path(__file__).resolve().parent

# Temporarily insert Exciton-MoA paths to import its modules
sys.path.insert(0, str(_ROOT / "Frontier_OS" / "Exciton-MoA"))
sys.path.insert(0, str(_ROOT / "Frontier_OS" / "Exciton-MoA" / "firmWare"))
sys.path.insert(0, str(_ROOT / "Frontier_OS" / "Exciton-MoA" / "firmWare" / "ExcitonEngine"))
sys.path.insert(0, str(_ROOT / "Frontier_OS" / "Exciton-MoA" / "teleMetry"))

from blank_config import BlankManifoldConfig
from blank_manifold_core import BlankManifoldCore
from excitons import ExcitonEngine
from teleMetry.telemetry import OntologicalOrchestrator

# Immediately pop temporary paths to avoid global name shadowing of telemetry.py
sys.path.pop(0)
sys.path.pop(0)
sys.path.pop(0)
sys.path.pop(0)

# Add sol-core permanently for the engine and telemetry
sys.path.insert(0, str(_ROOT / "tools" / "sol-core"))

from sol_engine import SOLEngine
import telemetry as sol_telemetry


def run_showcase(steps: int = 100, delay: float = 0.5):
    print("==================================================")
    print("     SOL UNIFIED SYSTEM TELEMETRY SHOWCASE        ")
    print("==================================================")
    print(f"Target steps: {steps if steps > 0 else 'Infinite'}")
    print(f"Tick delay  : {delay}s")
    print("Press CTRL+C to stop simulation.\n")

    # 1. Force enable OpenTelemetry and initialize
    os.environ["SOL_TELEMETRY_ENABLED"] = "true"
    sol_telemetry.init_telemetry("sol-showcase")
    
    # 2. Instantiate SOLEngine
    print("Booting SOL Headless Core Engine...")
    engine = SOLEngine.from_default_graph()
    
    # 3. Instantiate Frontier_OS / Exciton-MoA substrate
    print("Booting Frontier_OS / Exciton-MoA Substrate (1024 nodes)...")
    moa_config = BlankManifoldConfig(base_node_count=1024, dimensionality=3)
    moa_manifold = BlankManifoldCore(moa_config)
    moa_manifold.generate_manifold()
    moa_excitons = ExcitonEngine(moa_manifold)
    moa_orchestrator = OntologicalOrchestrator(moa_manifold, tau_threshold=4.5)
    
    valid_labels = ["grail", "metatron", "pyramid", "christ", "light codes"]
    pipeline_stages = ["smoke", "cortex", "consolidate", "hippocampus", "evolve", "report"]
    cortex_gaps = ["symmetry break detection", "quantum boundary discovery", "epistemic flow check"]
    
    step_count = 0
    try:
        while steps == 0 or step_count < steps:
            step_count += 1
            print(f"\n--- [TICK {step_count}] ---")
            
            # Start root orchestrator run span
            run_id = f"SHOWCASE-{time.strftime('%H%M%S')}"
            with sol_telemetry.trace_span("sol.orchestrator.run", {"sol.run_id": run_id}) as run_span:
                
                # A. SOL Engine tick
                print(" -> Running SOL Engine step...")
                engine.step()
                
                # B. Random node injection
                target_node = random.choice(valid_labels)
                injection_amount = float(random.randint(15, 60))
                print(f" -> Injecting {injection_amount} density to '{target_node}'")
                engine.inject(target_node, injection_amount)
                
                # C. Orchestrator stage emulation
                current_stage = pipeline_stages[(step_count - 1) % len(pipeline_stages)]
                print(f" -> Emulating Orchestrator stage: '{current_stage}'")
                with sol_telemetry.trace_span(f"sol.orchestrator.stage", {"sol.stage.name": current_stage}):
                    time.sleep(0.02) # simulated stage load
                    
                    # D. Trigger subagent reasoning traces based on stage
                    if current_stage == "cortex":
                        gap = random.choice(cortex_gaps)
                        print(f"    * Cortex analyzing gap: '{gap}'")
                        with sol_telemetry.trace_span("sol.cortex.resolve_gap", {"sol.cortex.gap_description": gap}, service_name="cortex"):
                            with sol_telemetry.trace_span("sol.cortex.hypothesis_generation", service_name="cortex"):
                                time.sleep(0.01)
                            with sol_telemetry.trace_span("sol.cortex.execution", service_name="cortex"):
                                time.sleep(0.01)
                                
                    elif current_stage == "hippocampus":
                        print("    * Hippocampus dream cycle consolidation...")
                        with sol_telemetry.trace_span("sol.hippocampus.dream_cycle", service_name="hippocampus"):
                            with sol_telemetry.trace_span("sol.hippocampus.consolidate", service_name="hippocampus"):
                                time.sleep(0.02)
                                
                    elif current_stage == "evolve":
                        print("    * RSI evolving agents and mutating genomes...")
                        with sol_telemetry.trace_span("sol.rsi.cycle", service_name="rsi") as rsi_span:
                            fitness = random.uniform(0.75, 0.99)
                            rsi_span.set_attribute("sol.rsi.fitness", fitness)
                            with sol_telemetry.trace_span("sol.rsi.mutate", service_name="rsi"):
                                time.sleep(0.01)
                
                # E. Frontier_OS / Exciton-MoA step
                print(" -> Running Exciton-MoA physical operators...")
                
                # Ignite resonance at a random target coordinate
                target_coords = np.random.normal(loc=0.5, scale=0.15, size=3)
                
                # Trigger some active nodes on Exciton manifold
                active_count = random.randint(3, 15)
                nodes_list = list(moa_manifold.graph.nodes)
                for _ in range(active_count):
                    n_id = random.choice(nodes_list)
                    moa_manifold.graph.nodes[n_id]["resonance_accumulator"] = random.uniform(0.5, 4.0)
                
                moa_excitons.ignite_excitons(target_coords)
                
                # Scan spotlight for Jeans mass collapses and trigger bursts
                print(" -> Orchestrator scanning Exciton manifold...")
                bursts = moa_orchestrator.scan_manifold()
                if bursts:
                    print(f"    * Spotlight alert: {len(bursts)} bursts detected!")

            # Yield to make updates watchable
            time.sleep(delay)
            
    except KeyboardInterrupt:
        print("\nShowcase halted by user command.")
    except Exception as e:
        print(f"\nError running showcase: {e}")
        import traceback
        traceback.print_exc()

    print("\nShowcase execution finished.")


def main():
    parser = argparse.ArgumentParser(description="SOL Showcase Telemetry Loop")
    parser.add_argument("--steps", type=int, default=100, help="Number of ticks to run (0 for infinite)")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds to wait between ticks")
    args = parser.parse_args()
    run_showcase(steps=args.steps, delay=args.delay)


if __name__ == "__main__":
    main()
