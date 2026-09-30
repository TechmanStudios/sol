# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
"""Diagnostic script to print step-by-step dRho values."""

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

        # Trace Step 2 using custom step execution inside JS
        results = driver.execute_script("""
            const phy = window.SOLDashboard.state.physics;
            const dt = 0.12;
            const c_press = 45.0;
            const damping = 0.0;

            const mass0 = phy.nodes.reduce((s, n) => s + n.rho, 0);

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

            let totalFlux = 0;
            const dRho = new Array(phy.nodes.length).fill(0);
            let edgesProcessed = 0;
            let sumFlowAmt = 0;

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

                edgesProcessed++;
                const deltaP = src.p - dst.p;

                let tension = 1.0;
                if (srcGroup === 'tech' || dstGroup === 'tech') tension = phy.phaseCfg.surfaceTension;
                if (srcGroup === 'spirit' || dstGroup === 'spirit') tension = phy.phaseCfg.deepViscosity;

                let diodeGain = 1.0;

                const targetFlux = (e.conductance * tension * diodeGain) * deltaP;
                e.flux = e.flux * (1 - dt) + targetFlux * dt;
                totalFlux += Math.abs(e.flux);

                const flowAmt = e.flux * dt * 0.5;
                sumFlowAmt += flowAmt;

                if (srcAwake) dRho[ia] -= flowAmt;
                if (dstAwake) dRho[ib] += flowAmt;
            });

            // Sum of dRho array elements
            let dRhoSum = dRho.reduce((s, x) => s + x, 0);

            // Apply mass changes manually
            let nodeRhoBefore = phy.nodes.map(n => n.rho);
            phy.nodes.forEach((n, idx) => {
                n.rho += dRho[idx];
                n.rho *= (1.0 - (damping * dt * 0.1 * 1.0));
                if(n.rho < 0) n.rho = 0;
            });
            let nodeRhoAfter = phy.nodes.map(n => n.rho);

            const mass1 = phy.nodes.reduce((s, n) => s + n.rho, 0);

            return {
                mass0,
                mass1,
                dRhoSum,
                edgesProcessed,
                sumFlowAmt,
                nodesCount: phy.nodes.length,
                edgesCount: phy.edges.length,
                dRhoNonZeroCount: dRho.filter(x => x !== 0).length,
                changeInRhoSum: nodeRhoAfter.reduce((s,x,i) => s + (x - nodeRhoBefore[i]), 0)
            };
        """)

        print("Mass 0 (Start of Step 2):", results["mass0"])
        print("Mass 1 (End of Step 2 physics):", results["mass1"])
        print("Sum of dRho Array:", results["dRhoSum"])
        print("Edges Processed:", results["edgesProcessed"])
        print("Sum of Flow Amount:", results["sumFlowAmt"])
        print("Nodes Count:", results["nodesCount"])
        print("Edges Count:", results["edgesCount"])
        print("dRho Non-zero Count:", results["dRhoNonZeroCount"])
        print("Change in Rho Sum:", results["changeInRhoSum"])

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
