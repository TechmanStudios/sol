# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""Debug script to inspect SOL manifold variables during dynamic scaling."""

import sys
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
    driver = webdriver.Firefox(options=options)

    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return !!(window.SOLDashboard && window.SOLDashboard.state && window.SOLDashboard.state.physics)")
        )
        driver.execute_script("if (!window.__SOL_INIT_DONE__) window.SOLDashboard.init();")

        # Intercept console logs
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
            for log in logs:
                if "MASS" in log or "LATTICE" in log:
                    print("  [JS LOG]", log)

        # Inject and print
        driver.execute_script("""
            const phy = window.SOLDashboard.state.physics;
            phy.inject("Exciton-1", 300.0);
            phy.inject("Exciton-64", 300.0);
        """)

        dt = 0.12
        pressure_c = 45.0
        damping = 0.0

        print("=== INITIAL INJECTION ===")
        # Print top 5 nodes by density
        nodes_info = driver.execute_script("""
            return window.SOLDashboard.state.physics.nodes.map(n => ({
                id: n.id,
                label: n.label,
                rho: n.rho,
                p: n.p,
                isStellar: !!n.isStellar,
                isConstellation: !!n.isConstellation
            })).sort((a,b) => b.rho - a.rho).slice(0, 5);
        """)
        for n in nodes_info:
            print(f"Node {n['label']} ({n['id']}): rho={n['rho']:.4f}, p={n['p']:.4f}, isStellar={n['isStellar']}")

        def print_stats(step_num):
            nodes = driver.execute_script("return window.SOLDashboard.state.physics.nodes.length;")
            edges = driver.execute_script("return window.SOLDashboard.state.physics.edges.length;")
            mass_stats = driver.execute_script("""
                let sum = 0, max = 0, maxId = '';
                let stellarList = [];
                window.SOLDashboard.state.physics.nodes.forEach(n => {
                    sum += n.rho;
                    if (n.rho > max) { max = n.rho; maxId = n.label; }
                    if (n.isStellar) stellarList.push(n.label + ' (rho=' + n.rho.toFixed(2) + ')');
                });
                return { sum, max, maxId, stellarList };
            """)
            print(f"Step {step_num:02d} | Nodes: {nodes} | Edges: {edges} | Total Mass: {mass_stats['sum']:.4f} | Max Density: {mass_stats['max']:.4f} ({mass_stats['maxId']}) | Stellar: {mass_stats['stellarList']}")

        # Step Phase 1 (60 steps)
        print("\nRunning Phase 1 (60 steps)...")
        for step in range(1, 61):
            driver.execute_script(f"window.SOLDashboard.state.physics.step({dt}, {pressure_c}, {damping});")
            if step <= 5:
                print_stats(step)
                flush_logs()

        print_stats(60)
        flush_logs()

        # Start Phase 2 (damping = 18.0)
        print("\n=== STARTING PHASE 2 (Damping = 18.0) ===")
        damping = 18.0
        for step in range(61, 81):
            driver.execute_script(f"window.SOLDashboard.state.physics.step({dt}, {pressure_c}, {damping});")
            if step in [61, 62, 65, 70, 75, 80]:
                print_stats(step)
                flush_logs()

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
