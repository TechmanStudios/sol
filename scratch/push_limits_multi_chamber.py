# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
"""Orchestration script to test multi-chamber counter-breathing in PME mode."""

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

    data_dir = sol_root / "data"
    data_dir.mkdir(exist_ok=True)

    options = Options()
    options.add_argument("-headless")
    
    print("Initializing headless Firefox Developer Edition webdriver...")
    driver = webdriver.Firefox(options=options)

    # Competing chambers script
    drive_js = """
    const phy = window.SOLDashboard.state.physics;
    const rate = arguments[0];
    const omega = arguments[1];
    const t = phy._t || 0;

    // Competing time-varying drive: Chamber 1 (in-phase), Chamber 2 (out-of-phase by PI)
    const drive1 = rate * Math.max(0, Math.sin(omega * t));
    const drive2 = rate * Math.max(0, Math.sin(omega * t + Math.PI));

    // Chamber 1: Inject at Exciton-1, drain at Exciton-8
    phy.inject("Exciton-1", drive1);
    const node8 = phy.nodeById.get(8);
    const drain1 = Math.min(node8 ? node8.rho : 0, drive1);
    if (node8) node8.rho -= drain1;

    // Chamber 2: Inject at Exciton-57, drain at Exciton-64
    phy.inject("Exciton-57", drive2);
    const node64 = phy.nodeById.get(64);
    const drain2 = Math.min(node64 ? node64.rho : 0, drive2);
    if (node64) node64.rho -= drain2;
    """

    # Partition count script
    partition_js = """
    const phy = window.SOLDashboard.state.physics;

    function getOriginalParents(nodeId) {
        if (nodeId <= 64) return [nodeId];
        const node = phy.nodeById.get(nodeId);
        if (!node || !node.parentEndpoints) return [];
        
        let parents = [];
        node.parentEndpoints.forEach(pId => {
            parents = parents.concat(getOriginalParents(pId));
        });
        return parents;
    }

    let n1 = 0;
    let n2 = 0;

    phy.nodes.forEach(n => {
        const orig = getOriginalParents(n.id);
        if (orig.length === 0) return;
        const topCount = orig.filter(id => id <= 32).length;
        const botCount = orig.length - topCount;
        if (topCount >= botCount) {
            n1++;
        } else {
            n2++;
        }
    });

    return { n1, n2, total_mass: phy.nodes.reduce((s, n) => s + n.rho, 0) };
    """

    try:
        def boot_dashboard():
            driver.get(url)
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return !!(window.SOLDashboard && window.SOLDashboard.state && window.SOLDashboard.state.physics)")
            )
            driver.execute_script("if (!window.__SOL_INIT_DONE__) window.SOLDashboard.init();")

        # Sweeps parameter configurations: (amplitude, omega)
        sweeps = [
            (50.0, 0.05, "50_med"),
            (150.0, 0.05, "150_med"),
            (150.0, 0.20, "150_fast"),
            (150.0, 0.01, "150_slow")
        ]
        
        dt = 0.12
        pressure_c = 45.0
        damping = 8.0
        steps = 300

        report = ["# Multi-Chamber Resonant Counter-Breathing Report", ""]
        report.append("| Experiment ID | Amplitude ($I_0$) | Drive Frequency ($\omega_d$) | Chamber 1 Nodes ($N_1$) | Chamber 2 Nodes ($N_2$) | Correlation $r(N_1, N_2)$ | Dynamic Behavior |")
        report.append("|---|---|---|---|---|---|---|")

        for amp, omega, exp_id in sweeps:
            print(f"\n--- Running counter-drive sweep: Amp={amp}, Omega={omega} ({exp_id}) ---")
            boot_dashboard()
            
            csv_path = data_dir / f"counter_breathing_{exp_id}.csv"
            
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["tick", "n1", "n2", "total_mass"])
                
                for tick in range(1, steps + 1):
                    # Apply time-varying drive
                    driver.execute_script(drive_js, amp, omega)
                    # Step physics
                    driver.execute_script(f"window.SOLDashboard.state.physics.step({dt}, {pressure_c}, {damping});")
                    
                    # Gather partitions
                    res = driver.execute_script(partition_js)
                    writer.writerow([tick, res["n1"], res["n2"], res["total_mass"]])
                    
                    if tick % 50 == 0:
                        print(f"  Tick {tick:03d} | N1: {res['n1']} | N2: {res['n2']} | Mass: {res['total_mass']:.2f}")

            # Run statistical analysis on the sweep results
            data = np.genfromtxt(csv_path, delimiter=',', skip_header=1)
            # Focus on the last 150 ticks
            ss_data = data[-150:]
            n1_vals = ss_data[:, 1]
            n2_vals = ss_data[:, 2]
            
            n1_mean, n1_std = np.mean(n1_vals), np.std(n1_vals)
            n2_mean, n2_std = np.mean(n2_vals), np.std(n2_vals)
            
            # Correlation
            if n1_std > 0 and n2_std > 0:
                r = np.corrcoef(n1_vals, n2_vals)[0, 1]
            else:
                r = 0.0
                
            print(f"Sweep Completed: N1={int(np.min(n1_vals))}-{int(np.max(n1_vals))} | N2={int(np.min(n2_vals))}-{int(np.max(n2_vals))} | r={r:.4f}")
            
            behavior = "Stable Counter-Breathing (Anti-correlated)" if r < -0.4 else "In-Phase/In-Phase (Correlated)"
            if r >= -0.4 and r <= 0.4:
                behavior = "Decoupled / Asymmetric"
            
            report.append(f"| {exp_id} | {amp} | {omega} | {int(np.min(n1_vals))}-{int(np.max(n1_vals))} | {int(np.min(n2_vals))}-{int(np.max(n2_vals))} | {r:.4f} | {behavior} |")

        # Save summary report
        report_path = sol_root / "emergence_counter_breathing_summary.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
        print(f"\nExperiment summaries written to {report_path}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
