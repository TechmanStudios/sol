# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
"""Diagnostic script to track mass conservation in SOL manifold scaling."""

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

        # Wrap runDynamicScaling to print mass before/after and intercept console logs
        driver.execute_script("""
            window.__console_logs = [];
            const originalLog = console.log;
            console.log = function(...args) {
                window.__console_logs.push(args.join(' '));
                originalLog.apply(console, args);
            };

            const synth = window.SOLDashboard.synth;
            if (synth) {
                const originalScaling = synth.runDynamicScaling;
                synth.runDynamicScaling = function(physics) {
                    const massBefore = physics.nodes.reduce((s, n) => s + n.rho, 0);
                    console.log("[DIAG] MASS BEFORE SCALING: " + massBefore.toFixed(6));
                    originalScaling.call(this, physics);
                    const massAfter = physics.nodes.reduce((s, n) => s + n.rho, 0);
                    console.log("[DIAG] MASS AFTER SCALING: " + massAfter.toFixed(6));
                };
            }
        """)

        # Inject mass
        driver.execute_script("""
            const phy = window.SOLDashboard.state.physics;
            phy.inject("Exciton-1", 300.0);
            phy.inject("Exciton-64", 300.0);
        """)

        dt = 0.12
        pressure_c = 45.0
        damping = 0.0

        def flush_logs():
            logs = driver.execute_script("""
                const l = window.__console_logs || [];
                window.__console_logs = [];
                return l;
            """)
            for log in logs:
                if "[DIAG]" in log or "LATTICE" in log or "MASS" in log:
                    print("  ", log)

        for step in range(1, 11):
            mass_before_step = driver.execute_script("""
                return window.SOLDashboard.state.physics.nodes.reduce((s, n) => s + n.rho, 0);
            """)
            print(f"\n--- STEP {step:02d} ---")
            print(f"   Mass BEFORE step(): {mass_before_step:.6f}")
            
            driver.execute_script(f"window.SOLDashboard.state.physics.step({dt}, {pressure_c}, {damping});")
            
            mass_after_step = driver.execute_script("""
                return window.SOLDashboard.state.physics.nodes.reduce((s, n) => s + n.rho, 0);
            """)
            print(f"   Mass AFTER step(): {mass_after_step:.6f}")
            flush_logs()

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
