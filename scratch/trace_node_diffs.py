# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
"""Diagnostic script to print individual node differences in Step 2."""

from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

def main():
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

        # Inject mass
        driver.execute_script("""
            const phy = window.SOLDashboard.state.physics;
            phy.inject("Exciton-1", 300.0);
            phy.inject("Exciton-64", 300.0);
        """)

        # Step 1 (triggers splits)
        driver.execute_script("window.SOLDashboard.state.physics.step(0.12, 45.0, 0.0);")

        # Trace differences node-by-node
        nodes_diffs = driver.execute_script("""
            const phy = window.SOLDashboard.state.physics;
            const dt = 0.12;
            const c_press = 45.0;
            const damping = 0.0;

            // Run step calculations manually to intercept variables
            phy._t = (phy._t || 0) + dt;
            const phase = Math.cos(phy.phaseCfg.omega * phy._t * 10);
            const isSurfaceActive = phase > -0.2;
            const isDeepActive = phase < 0.2;

            phy.updatePsi(dt);
            phy.applySemanticMassDecay(dt);
            phy.computePressure(c_press);
            phy.updateConductance();

            if (phy.updateBatteries) phy.updateBatteries(dt);
            phy.computePressure(c_press);

            const dRho = new Array(phy.nodes.length).fill(0);

            phy.edges.forEach(e => {
                const ia = phy.nodeIndexById.get(e.from);
                const ib = phy.nodeIndexById.get(e.to);
                if (ia === undefined || ib === undefined) return;

                const src = phy.nodes[ia];
                const dst = phy.nodes[ib];

                const srcGroup = src.group || 'bridge';
                const dstGroup = dst.group || 'bridge';

                let srcAwake = true;
                let dstAwake = true;

                if (srcGroup === 'tech' && !isSurfaceActive) srcAwake = false;
                if (srcGroup === 'spirit' && !isDeepActive) srcAwake = false;
                if (dstGroup === 'tech' && !isSurfaceActive) dstAwake = false;
                if (dstGroup === 'spirit' && !isDeepActive) dstAwake = false;

                if (!srcAwake || !dstAwake) return;

                const deltaP = src.p - dst.p;

                let tension = 1.0;
                if (srcGroup === 'tech' || dstGroup === 'tech') tension = phy.phaseCfg.surfaceTension;
                if (srcGroup === 'spirit' || dstGroup === 'spirit') tension = phy.phaseCfg.deepViscosity;

                let diodeGain = 1.0;

                const targetFlux = (e.conductance * tension * diodeGain) * deltaP;
                e.flux = e.flux * (1 - dt) + targetFlux * dt;

                const flowAmt = e.flux * dt * 0.5;

                if (srcAwake) dRho[ia] -= flowAmt;
                if (dstAwake) dRho[ib] += flowAmt;
            });

            // Compare node-by-node
            const details = [];
            phy.nodes.forEach((n, idx) => {
                const before = n.rho;
                n.rho += dRho[idx];
                const after = n.rho;
                const diff = after - before;
                const drhoVal = dRho[idx];
                if (Math.abs(diff - drhoVal) > 1e-9) {
                    details.push({
                        id: n.id,
                        label: n.label,
                        before,
                        drhoVal,
                        after,
                        diff,
                        mismatch: true
                    });
                } else if (Math.abs(drhoVal) > 0.001) {
                    details.push({
                        id: n.id,
                        label: n.label,
                        before,
                        drhoVal,
                        after,
                        diff,
                        mismatch: false
                    });
                }
            });

            return details;
        """)

        print(f"Details (Total traced nodes with non-zero change or mismatch: {len(nodes_diffs)}):")
        mismatches = 0
        for item in nodes_diffs:
            if item["mismatch"]:
                print(f"!!! MISMATCH !!! Node {item['label']} ({item['id']}): before={item['before']:.4f}, drho={item['drhoVal']:.4f}, after={item['after']:.4f}, diff={item['diff']:.4f}")
                mismatches += 1
            else:
                print(f"Node {item['label']} ({item['id']}): before={item['before']:.4f}, drho={item['drhoVal']:.4f}, after={item['after']:.4f}, diff={item['diff']:.4f}")
        print("Total mismatches found:", mismatches)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
