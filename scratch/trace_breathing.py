# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
"""Instrumentation script to trace breathing manifold limit cycles in PME mode."""

import csv
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

    # Ensure data folder exists
    data_dir = sol_root / "data"
    data_dir.mkdir(exist_ok=True)

    options = Options()
    options.add_argument("-headless")
    
    print("Initializing headless Firefox Developer Edition webdriver...")
    driver = webdriver.Firefox(options=options)

    try:
        def boot_dashboard():
            driver.get(url)
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return !!(window.SOLDashboard && window.SOLDashboard.state && window.SOLDashboard.state.physics)")
            )
            driver.execute_script("if (!window.__SOL_INIT_DONE__) window.SOLDashboard.init();")

        # Javascript calculation script
        metrics_js = """
        const phy = window.SOLDashboard.state.physics;
        const c_press = 45.0; 
        const eps = phy.nodalCfg ? phy.nodalCfg.eps : 1e-6;

        let total_mass = 0;
        let mass_sq_sum = 0;
        let potential_energy = 0;
        let num_nodes = phy.nodes.length;

        phy.nodes.forEach(n => {
            total_mass += n.rho;
            mass_sq_sum += n.rho * n.rho;
            const m = n.semanticMass || 1.0;
            // Potential energy: c * [(rho + m) * log(1 + rho/m) - rho]
            potential_energy += c_press * ((n.rho + m) * Math.log(1 + n.rho / m) - n.rho);
        });

        const mean_mass = total_mass / num_nodes;
        const mass_variance = (mass_sq_sum / num_nodes) - (mean_mass * mean_mass);

        let kinetic_energy = 0;
        let total_momentum_scalar = 0;
        let total_momentum_algebraic = 0;
        let num_edges = phy.edges.length;

        phy.edges.forEach(e => {
            if (e.background) return;
            const ia = phy.nodeIndexById.get(e.from);
            const ib = phy.nodeIndexById.get(e.to);
            if (ia === undefined || ib === undefined) return;
            const rho_from = phy.nodes[ia].rho;
            const rho_to = phy.nodes[ib].rho;

            const m_from = e.m_from || 0;
            const m_to = e.m_to || 0;

            // Kinetic energy: 0.5 * ( m_from^2 / (rho_from + eps) + m_to^2 / (rho_to + eps) )
            kinetic_energy += 0.5 * ( (m_from * m_from) / (rho_from + eps) + (m_to * m_to) / (rho_to + eps) );
            total_momentum_scalar += Math.abs(m_from) + Math.abs(m_to);
            total_momentum_algebraic += m_from + m_to;
        });

        return {
            total_mass,
            mass_variance,
            kinetic_energy,
            potential_energy,
            total_energy: kinetic_energy + potential_energy,
            total_momentum_scalar,
            total_momentum_algebraic,
            num_nodes,
            num_edges,
            vorticity_global: phy.vortNorm_global || 0
        };
        """

        inflow_rates = [50.0, 150.0]
        dt = 0.12
        pressure_c = 45.0
        damping = 8.0
        steps = 400  # Run longer to capture multiple cycles

        for rate in inflow_rates:
            print(f"\n--- Running Trace for Inflow Rate: {rate} mass/tick ---")
            boot_dashboard()
            
            csv_path = data_dir / f"breathing_trace_{int(rate)}.csv"
            
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "tick", "num_nodes", "num_edges", "total_mass", "mass_variance",
                    "kinetic_energy", "potential_energy", "total_energy",
                    "total_momentum_scalar", "total_momentum_algebraic", "vorticity_global"
                ])
                
                for tick in range(1, steps + 1):
                    # Inject continuous mass on Exciton-1 and Exciton-64
                    driver.execute_script(f"""
                        const phy = window.SOLDashboard.state.physics;
                        phy.inject("Exciton-1", {rate / 2.0});
                        phy.inject("Exciton-64", {rate / 2.0});
                    """)
                    # Step physics
                    driver.execute_script(f"window.SOLDashboard.state.physics.step({dt}, {pressure_c}, {damping});")
                    
                    # Gather metrics
                    metrics = driver.execute_script(metrics_js)
                    
                    writer.writerow([
                        tick, metrics["num_nodes"], metrics["num_edges"],
                        metrics["total_mass"], metrics["mass_variance"],
                        metrics["kinetic_energy"], metrics["potential_energy"],
                        metrics["total_energy"], metrics["total_momentum_scalar"],
                        metrics["total_momentum_algebraic"], metrics["vorticity_global"]
                    ])
                    
                    if tick % 50 == 0:
                        print(f"  Tick {tick:03d} | Nodes: {metrics['num_nodes']} | Mass: {metrics['total_mass']:.2f} | Kinetic Energy: {metrics['kinetic_energy']:.2f}")

            print(f"Finished. Data saved to {csv_path}")

            # Attractor / Phase Space analysis
            data = np.genfromtxt(csv_path, delimiter=',', skip_header=1)
            
            # Analyze the last 150 ticks (steady state limit cycle)
            steady_state_data = data[-150:]
            ticks = steady_state_data[:, 0]
            nodes = steady_state_data[:, 1]
            mass = steady_state_data[:, 3]
            ke = steady_state_data[:, 5]
            pe = steady_state_data[:, 6]
            te = steady_state_data[:, 7]
            
            node_min, node_max = int(np.min(nodes)), int(np.max(nodes))
            mass_min, mass_max = np.min(mass), np.max(mass)
            ke_min, ke_max = np.min(ke), np.max(ke)
            te_min, te_max = np.min(te), np.max(te)
            
            # Simple autocorrelation to find period of node count oscillation
            node_centered = nodes - np.mean(nodes)
            if np.std(node_centered) > 0.5:
                autocorr = np.correlate(node_centered, node_centered, mode='full')
                autocorr = autocorr[autocorr.size // 2:]
                # find peaks
                peaks = []
                for i in range(1, len(autocorr) - 1):
                    if autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1]:
                        peaks.append(i)
                period = peaks[0] if len(peaks) > 0 else "N/A"
            else:
                period = "Static"
                
            print(f"--- Limit Cycle Attractor Report ({rate} mass/tick) ---")
            print(f"  Node Range: {node_min} - {node_max} (Amplitude: {node_max - node_min})")
            print(f"  Mass Range: {mass_min:.2f} - {mass_max:.2f}")
            print(f"  Kinetic Energy Range: {ke_min:.2f} - {ke_max:.2f}")
            print(f"  Total Energy Range: {te_min:.2f} - {te_max:.2f}")
            print(f"  Oscillation Period: {period} ticks")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
