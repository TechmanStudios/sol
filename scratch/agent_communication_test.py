# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
"""Simulation script to test agent communication through the SOL manifold."""

import csv
import random
import sys
import time
from pathlib import Path
import numpy as np
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    sol_root = Path(__file__).resolve().parents[1]
    dashboard_path = sol_root / "sol_dashboard_v3_8_agentic.html"
    url = f"file:///{dashboard_path.as_posix()}?automation=1"

    options = Options()
    options.add_argument("-headless")
    
    print("Initializing headless Firefox Developer Edition webdriver...")
    driver = webdriver.Firefox(options=options)

    # Let's seed random to make test sequence reproducible
    random.seed(42)
    test_sequence = [random.choice(['A', 'B', 'C']) for _ in range(12)]
    print(f"Test symbol sequence to transmit: {test_sequence}")

    try:
        def boot_dashboard():
            driver.get(url)
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return !!(window.SOLDashboard && window.SOLDashboard.state && window.SOLDashboard.state.physics)")
            )
            driver.execute_script("if (!window.__SOL_INIT_DONE__) window.SOLDashboard.init();")

        # Sweep configurations: (crosstalk_w, damping, t_silent, inj_rate, sweep_id)
        sweeps = [
            # High-injection sweeps (Dynamic topology changes, heavy splitting)
            (0.0, 8.0, 15, 120.0, "high_inj_ideal_damp8_sil15"),
            (0.2, 8.0, 15, 120.0, "high_inj_med_crosstalk_sil15"),
            (0.2, 8.0, 25, 120.0, "high_inj_med_crosstalk_sil25"),
            # Low-injection sweeps (Static topology, below expansion limit of 25.0)
            (0.0, 8.0, 15, 15.0, "low_inj_ideal_damp8_sil15"),
            (0.2, 8.0, 15, 15.0, "low_inj_med_crosstalk_sil15"),
            (0.2, 8.0, 25, 15.0, "low_inj_med_crosstalk_sil25"),
            (0.5, 8.0, 25, 15.0, "low_inj_high_crosstalk_sil25"),
            (0.2, 2.0, 25, 15.0, "low_inj_med_crosstalk_lowdamp_sil25"),
            (0.2, 15.0, 25, 15.0, "low_inj_med_crosstalk_hidamp_sil25")
        ]

        report = ["# Agent-to-Agent Topological Communication Sweep Report", ""]
        report.append("This report evaluates the Symbol Error Rate (SER) and Throughput of a three-channel mass-wave communication protocol. Senders inject mass, relays propagate density waves, and receivers decode messages via integrated density max-detection.")
        report.append("")
        report.append("| Sweep ID | Crosstalk ($w_{\\text{cross}}$) | Damping ($\\alpha$) | Silence ($T_{\\text{silent}}$) | Inflow ($I_0$) | Sent Sequence | Decoded Sequence | Errors | SER | Throughput (Bits/Tick) | Topology Splitted? |")
        report.append("|---|---|---|---|---|---|---|---|---|---|---|")

        dt = 0.12
        pressure_c = 45.0
        t_pulse = 5      # Steps to pulse inflow

        for w_cross, damping, t_silent, injection_rate, sweep_id in sweeps:
            print(f"\n--- Running Communication Sweep: {sweep_id} ---")
            boot_dashboard()

            # Construct graph
            graph = {
                "rawNodes": [
                    {"id": 1, "label": "Alpha-Message-A", "group": "tech", "x": -200, "y": -150},
                    {"id": 2, "label": "Alpha-Message-B", "group": "tech", "x": -200, "y": 0},
                    {"id": 3, "label": "Alpha-Message-C", "group": "tech", "x": -200, "y": 150},
                    
                    {"id": 4, "label": "Relay-A", "group": "bridge", "x": 0, "y": -150},
                    {"id": 5, "label": "Relay-B", "group": "bridge", "x": 0, "y": 0},
                    {"id": 6, "label": "Relay-C", "group": "bridge", "x": 0, "y": 150},
                    
                    {"id": 7, "label": "Beta-Receive-A", "group": "spirit", "x": 200, "y": -150},
                    {"id": 8, "label": "Beta-Receive-B", "group": "spirit", "x": 200, "y": 0},
                    {"id": 9, "label": "Beta-Receive-C", "group": "spirit", "x": 200, "y": 150}
                ],
                "rawEdges": [
                    # Direct paths
                    {"from": 1, "to": 4, "w0": 1.0},
                    {"from": 4, "to": 7, "w0": 1.0},
                    
                    {"from": 2, "to": 5, "w0": 1.0},
                    {"from": 5, "to": 8, "w0": 1.0},
                    
                    {"from": 3, "to": 6, "w0": 1.0},
                    {"from": 6, "to": 9, "w0": 1.0},
                    
                    # Crosstalk
                    {"from": 4, "to": 5, "w0": w_cross},
                    {"from": 5, "to": 6, "w0": w_cross},
                    {"from": 4, "to": 6, "w0": w_cross}
                ],
                "meta": {
                    "nodeCount": 9,
                    "edgeCount": 9,
                    "isCompiledKB": False
                }
            }

            # Reload graph in Dashboard
            driver.execute_script("window.SOLDashboard.reloadGraph(arguments[0]);", graph)

            # Transmit symbols
            decoded_sequence = []
            
            # Keep track of active node count before and after
            initial_nodes = driver.execute_script("return window.SOLDashboard.state.physics.nodes.length;")
            topology_mutated = False

            for symbol in test_sequence:
                # Target node label
                target_label = f"Alpha-Message-{symbol}"
                
                # We will integrate receiver densities
                integrated_densities = {"A": 0.0, "B": 0.0, "C": 0.0}
                
                # 1. Pulse Phase
                for _ in range(t_pulse):
                    driver.execute_script(f"""
                        const phy = window.SOLDashboard.state.physics;
                        phy.inject("{target_label}", {injection_rate});
                        phy.step({dt}, {pressure_c}, {damping});
                    """)
                    # Record receiver densities
                    densities = driver.execute_script("""
                        const phy = window.SOLDashboard.state.physics;
                        const rA = phy.nodeById.get(7).rho;
                        const rB = phy.nodeById.get(8).rho;
                        const rC = phy.nodeById.get(9).rho;
                        return { A: rA, B: rB, C: rC };
                    """)
                    integrated_densities["A"] += densities["A"]
                    integrated_densities["B"] += densities["B"]
                    integrated_densities["C"] += densities["C"]

                # 2. Silence Phase
                for _ in range(t_silent):
                    driver.execute_script(f"""
                        const phy = window.SOLDashboard.state.physics;
                        phy.step({dt}, {pressure_c}, {damping});
                    """)
                    densities = driver.execute_script("""
                        const phy = window.SOLDashboard.state.physics;
                        const rA = phy.nodeById.get(7).rho;
                        const rB = phy.nodeById.get(8).rho;
                        const rC = phy.nodeById.get(9).rho;
                        return { A: rA, B: rB, C: rC };
                    """)
                    integrated_densities["A"] += densities["A"]
                    integrated_densities["B"] += densities["B"]
                    integrated_densities["C"] += densities["C"]

                # Decode the symbol by taking the max integrated density
                decoded = max(integrated_densities, key=integrated_densities.get)
                decoded_sequence.append(decoded)
                
            final_nodes = driver.execute_script("return window.SOLDashboard.state.physics.nodes.length;")
            if final_nodes != initial_nodes:
                topology_mutated = True

            # Calculate errors and SER
            errors = sum(1 for s, d in zip(test_sequence, decoded_sequence) if s != d)
            ser = errors / len(test_sequence)
            
            # Bits/tick = (1 - SER) * log2(3) / (t_pulse + t_silent)
            bits_per_tick = (1 - ser) * np.log2(3.0) / (t_pulse + t_silent)

            sent_str = "".join(test_sequence)
            dec_str = "".join(decoded_sequence)
            mut_str = f"Yes ({initial_nodes} → {final_nodes} nodes)" if topology_mutated else "No"
            
            print(f"  Sent:    {sent_str}")
            print(f"  Decoded: {dec_str}")
            print(f"  SER:     {ser*100:.1f}% | Bits/tick: {bits_per_tick:.4f} | Splitted: {mut_str}")
            
            report.append(f"| {sweep_id} | {w_cross} | {damping} | {t_silent} | {injection_rate} | `{sent_str}` | `{dec_str}` | {errors} | {ser*100:.1f}% | {bits_per_tick:.4f} | {mut_str} |")

        # Save summary report
        report_path = sol_root / "emergence_agent_communication_summary.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
        print(f"\nExperiment summaries written to {report_path}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
