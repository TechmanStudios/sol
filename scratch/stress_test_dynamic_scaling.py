# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
"""Stress-test suite to analyze emergent dynamic scaling properties in PME mode."""

import sys
import time
from pathlib import Path
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

    # We will accumulate summary markdown
    report = ["# Emergent Manifold Scaling Report (PME Mode)", ""]

    try:
        # Helper to boot and initialize
        def boot_dashboard():
            driver.get(url)
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return !!(window.SOLDashboard && window.SOLDashboard.state && window.SOLDashboard.state.physics)")
            )
            driver.execute_script("if (!window.__SOL_INIT_DONE__) window.SOLDashboard.init();")
            driver.execute_script("""
                window.__console_logs = [];
                const originalLog = console.log;
                console.log = function(...args) {
                    let msg = args[0];
                    if (typeof msg === 'string' && msg.includes('%c')) {
                        msg = msg.replace(/%c/g, '');
                        args = [msg];
                    }
                    window.__console_logs.push(args.map(x => typeof x === 'object' ? JSON.stringify(x) : String(x)).join(' '));
                    originalLog.apply(console, args);
                };
            """)

        def flush_logs():
            logs = driver.execute_script("""
                const l = window.__console_logs || [];
                window.__console_logs = [];
                return l;
            """)
            out = []
            for log in logs:
                if "LATTICE" in log or "MASS" in log:
                    out.append(log)
            return out

        # =====================================================================
        # EXPERIMENT 1: Mass Conservation Verification
        # =====================================================================
        print("\n=== Running Experiment 1: Mass Conservation Verification ===")
        boot_dashboard()
        
        # Inject mass
        driver.execute_script("""
            const phy = window.SOLDashboard.state.physics;
            phy.inject("Exciton-1", 300.0);
            phy.inject("Exciton-64", 300.0);
        """)

        dt = 0.12
        pressure_c = 45.0
        damping = 0.0
        exp1_masses = []
        exp1_nodes = []

        print("Stepping 30 ticks with damping = 0.0...")
        for step in range(1, 31):
            driver.execute_script(f"window.SOLDashboard.state.physics.step({dt}, {pressure_c}, {damping});")
            m = driver.execute_script("return window.SOLDashboard.state.physics.nodes.reduce((s, n) => s + n.rho, 0);")
            n = driver.execute_script("return window.SOLDashboard.state.physics.nodes.length;")
            exp1_masses.append(m)
            exp1_nodes.append(n)

        # Check precision
        max_mass_dev = max(abs(x - 600.0) for x in exp1_masses)
        print(f"Max mass deviation from 600.0: {max_mass_dev:.8f}")
        
        report.append("## Experiment 1: Mass Conservation")
        report.append(f"- **Initial Mass:** 600.000")
        report.append(f"- **Max Deviation during expansion:** {max_mass_dev:.8e} (Tolerance: 1e-6)")
        if max_mass_dev < 1e-6:
            report.append("- **Status:** ✅ SUCCESS (Perfect mass conservation under flux limiter)")
        else:
            report.append("- **Status:** ❌ FAILED (Mass leak detected)")
        report.append("")

        # =====================================================================
        # EXPERIMENT 2: Topological Hysteresis and Scarring
        # =====================================================================
        print("\n=== Running Experiment 2: Topological Hysteresis & Scarring ===")
        boot_dashboard()

        # Check initial connections
        initial_edges = driver.execute_script("return window.SOLDashboard.state.physics.edges.length;")
        initial_nodes = driver.execute_script("return window.SOLDashboard.state.physics.nodes.length;")

        # Inject mass to trigger expansion
        driver.execute_script("""
            const phy = window.SOLDashboard.state.physics;
            phy.inject("Exciton-1", 300.0);
            phy.inject("Exciton-64", 300.0);
        """)

        print("Stepping 40 ticks with damping = 0.0 (Expansion)...")
        for step in range(40):
            driver.execute_script(f"window.SOLDashboard.state.physics.step({dt}, {pressure_c}, 0.0);")
        
        peak_nodes = driver.execute_script("return window.SOLDashboard.state.physics.nodes.length;")
        peak_edges = driver.execute_script("return window.SOLDashboard.state.physics.edges.length;")
        print(f"Peak size during expansion: Nodes={peak_nodes}, Edges={peak_edges}")

        print("Stepping 120 ticks with damping = 18.0 (Contraction)...")
        for step in range(120):
            driver.execute_script(f"window.SOLDashboard.state.physics.step({dt}, {pressure_c}, 18.0);")
            logs = flush_logs()
            for l in logs:
                if "CONTRACTION" in l:
                    print("  [JS LOG]", l)

        final_nodes = driver.execute_script("return window.SOLDashboard.state.physics.nodes.length;")
        final_edges = driver.execute_script("return window.SOLDashboard.state.physics.edges.length;")
        print(f"Final size after contraction: Nodes={final_nodes}, Edges={final_edges}")

        # Check graph layout symmetry / scars
        has_scars = final_nodes != initial_nodes or final_edges != initial_edges
        
        report.append("## Experiment 2: Topological Hysteresis and Memory Scars")
        report.append(f"- **Initial Size:** {initial_nodes} Nodes, {initial_edges} Edges")
        report.append(f"- **Peak Expanded Size:** {peak_nodes} Nodes, {peak_edges} Edges")
        report.append(f"- **Post-Decay Final Size:** {final_nodes} Nodes, {final_edges} Edges")
        if has_scars:
            report.append("- **Emergent Finding:** 🌀 Hysteresis scar detected! The network did not return to its default grid topology, demonstrating topological memory in Riemann manifolds.")
        else:
            report.append("- **Status:** ✅ Elastic return (Manifold fully contracted back to baseline 8x8 grid)")
        report.append("")

        # =====================================================================
        # EXPERIMENT 3: Continuous Write Storm (Sweep)
        # =====================================================================
        print("\n=== Running Experiment 3: Continuous Write Storm Sweep ===")
        
        inflow_rates = [10.0, 50.0, 150.0]
        report.append("## Experiment 3: Continuous Write Storm Sweep")
        report.append("| Inflow Rate | Peak Size (Nodes) | Steady State Behavior |")
        report.append("|---|---|---|")

        for rate in inflow_rates:
            boot_dashboard()
            print(f"Testing inflow rate of {rate} mass/tick...")
            
            node_counts = []
            masses = []
            
            # Step 100 ticks, injecting continuous mass each step
            for tick in range(1, 101):
                # Inject continuous mass on Exciton-1 and Exciton-64
                driver.execute_script(f"""
                    const phy = window.SOLDashboard.state.physics;
                    phy.inject("Exciton-1", {rate / 2.0});
                    phy.inject("Exciton-64", {rate / 2.0});
                """)
                driver.execute_script(f"window.SOLDashboard.state.physics.step({dt}, {pressure_c}, 8.0);") # high damping
                
                n = driver.execute_script("return window.SOLDashboard.state.physics.nodes.length;")
                m = driver.execute_script("return window.SOLDashboard.state.physics.nodes.reduce((s, n) => s + n.rho, 0);")
                node_counts.append(n)
                masses.append(m)

            # Analyze steady state
            last_30_nodes = node_counts[-30:]
            steady_state_n = last_30_nodes[-1]
            min_n = min(last_30_nodes)
            max_n = max(last_30_nodes)
            
            if min_n == max_n:
                behavior = f"Static Equilibrium at {steady_state_n} nodes"
            else:
                behavior = f"Oscillatory (Limit Cycle) between {min_n} and {max_n} nodes"
                
            print(f"Rate: {rate} | Steady Behavior: {behavior} | Max Node Count: {max(node_counts)}")
            report.append(f"| {rate} | {max(node_counts)} | {behavior} |")

        # Save Report
        report_path = sol_root / "emergence_check_summary.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
        print(f"\nExperiment summary written to {report_path}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
