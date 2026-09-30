# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
"""Diagnostic script to check duplicates and indices in physics state."""

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

        # Inject and step 1 manually to cause splits
        driver.execute_script("""
            const phy = window.SOLDashboard.state.physics;
            phy.inject("Exciton-1", 300.0);
            phy.inject("Exciton-64", 300.0);
            phy.step(0.12, 45.0, 0.0);
        """)

        # Run diagnostics in JS
        diagnostic_info = driver.execute_script("""
            const phy = window.SOLDashboard.state.physics;
            
            // Check duplicates in nodes array
            const nodeIds = phy.nodes.map(n => n.id);
            const uniqueIdsCount = new Set(nodeIds).size;
            const uniqueObjectsCount = new Set(phy.nodes).size;
            
            // Check nodeIndexById
            let indexMapIssues = [];
            phy.nodes.forEach((n, idx) => {
                const mapIdx = phy.nodeIndexById.get(n.id);
                if (mapIdx !== idx) {
                    indexMapIssues.push(`Node ${n.id} is at index ${idx} but mapped to index ${mapIdx}`);
                }
            });

            // Check if there are edges with missing node entries
            let missingNodeEdges = [];
            phy.edges.forEach(e => {
                if (!phy.nodeById.has(e.from)) {
                    missingNodeEdges.push(`Edge connects from missing node: ${e.from}`);
                }
                if (!phy.nodeById.has(e.to)) {
                    missingNodeEdges.push(`Edge connects to missing node: ${e.to}`);
                }
            });

            return {
                nodesCount: phy.nodes.length,
                uniqueIdsCount,
                uniqueObjectsCount,
                indexMapIssues,
                missingNodeEdges,
                nodeIds: nodeIds.slice(0, 10),
                edgesCount: phy.edges.length
            };
        """)

        print("Nodes Count:", diagnostic_info["nodesCount"])
        print("Unique IDs Count:", diagnostic_info["uniqueIdsCount"])
        print("Unique Objects Count:", diagnostic_info["uniqueObjectsCount"])
        print("Index Map Issues:", diagnostic_info["indexMapIssues"])
        print("Missing Node Edges:", diagnostic_info["missingNodeEdges"])
        print("Edges Count:", diagnostic_info["edgesCount"])

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
