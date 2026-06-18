import json
from pathlib import Path

# Define the 11 engineering domains from ARCHITECTURE_MAP.md
ENGINEERING_DOMAINS = [
    {
        "id": "domain_runtime_engine",
        "name": "Runtime Engine Domain",
        "description": "Responsible for instruction execution, SIMD lane masking, vector registers, scheduling, and core loops.",
        "files": [
            {"name": "sol_sovereign_runtime.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_sovereign_runtime.py"},
            {"name": "sol_engine.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_engine.py"},
            {"name": "sol_runtime_scheduler.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_runtime_scheduler.py"},
            {"name": "sol_simd_core_integration.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_simd_core_integration.py"},
            {"name": "sol_simd_modes.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_simd_modes.py"}
        ]
    },
    {
        "id": "domain_rangers",
        "name": "Rangers Domain",
        "description": "Patrols the runtime state and evaluates local invariants to compile signed telemetry reports.",
        "files": [
            {"name": "finalization_ranger.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-rsi/coding_library/sovereign_domain/rangers/finalization_ranger.py"},
            {"name": "ranger_registry.json", "path": "g:/docs/TechmanStudios/sol/tools/sol-rsi/coding_library/sovereign_domain/ranger_registry.json"}
        ]
    },
    {
        "id": "domain_court",
        "name": "Court Domain",
        "description": "Supervises state promotion, evaluates ranger evidence, and issues binding level-up verdicts.",
        "files": [
            {"name": "sol_court_supervised_promotion.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_court_supervised_promotion.py"},
            {"name": "promotion_court.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-rsi/coding_library/sovereign_domain/promotion_court.py"},
            {"name": "promotion_gates.json", "path": "g:/docs/TechmanStudios/sol/tools/sol-rsi/coding_library/sovereign_domain/promotion_gates.json"}
        ]
    },
    {
        "id": "domain_ledger",
        "name": "Ledger Domain",
        "description": "Maintains append-only, tamper-evident hash chains documenting all coordinate updates and promotion events.",
        "files": [
            {"name": "sol_runtime_ledger.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_runtime_ledger.py"},
            {"name": "sol_long_horizon_stability_ledger.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_long_horizon_stability_ledger.py"}
        ]
    },
    {
        "id": "domain_burnin",
        "name": "Burn-In Domain",
        "description": "Handles long-horizon runtime validation, continuous stress tests, and stability calculations.",
        "files": [
            {"name": "sol_sovereign_burnin_runtime.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_sovereign_burnin_runtime.py"},
            {"name": "sol_burnin_promotion_readiness.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_burnin_promotion_readiness.py"},
            {"name": "sol_burnin_regression_detector.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_burnin_regression_detector.py"},
            {"name": "sol_burnin_stability_metrics.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_burnin_stability_metrics.py"}
        ]
    },
    {
        "id": "domain_release_candidate",
        "name": "Release Candidate Domain",
        "description": "Freezes APIs, validates stability metrics, and packages manifests prior to system finalization.",
        "files": [
            {"name": "sol_release_candidate_manifest.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_release_candidate_manifest.py"},
            {"name": "sol_governance_freeze.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_governance_freeze.py"},
            {"name": "sol_api_stability_contract.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_api_stability_contract.py"}
        ]
    },
    {
        "id": "domain_finalization",
        "name": "Finalization Domain",
        "description": "Secures final gateways, aggregates dockets, and performs system lockdown validations.",
        "files": [
            {"name": "sol_production_gateway.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_production_gateway.py"},
            {"name": "sol_final_system_manifest.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_final_system_manifest.py"},
            {"name": "sol_final_gate_registry.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_final_gate_registry.py"},
            {"name": "sol_production_readiness_guard.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_production_readiness_guard.py"},
            {"name": "sol_system_lockdown.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_system_lockdown.py"},
            {"name": "sol_runtime_handoff_manifest.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_runtime_handoff_manifest.py"},
            {"name": "sol_finalization_docket.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_finalization_docket.py"}
        ]
    },
    {
        "id": "domain_waveguide",
        "name": "Waveguide Domain",
        "description": "Coordinates wave propagation channels, synthesis, and routing logic across execution domains.",
        "files": [
            {"name": "sol_core_waveguide_binding.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_core_waveguide_binding.py"},
            {"name": "sol_hierarchical_waveguide_fabric.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_hierarchical_waveguide_fabric.py"},
            {"name": "sol_dynamic_waveguide_rebalancer.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_dynamic_waveguide_rebalancer.py"},
            {"name": "sol_waveguide_fabric_synthesis.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_waveguide_fabric_synthesis.py"}
        ]
    },
    {
        "id": "domain_cadence",
        "name": "Cadence Domain",
        "description": "Synchronizes coordinate clocks, aligns epochs, and handles consensus across sharded manifolds.",
        "files": [
            {"name": "sol_temporal_cadence.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_temporal_cadence.py"},
            {"name": "sol_autonomous_cadence_sync.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_autonomous_cadence_sync.py"},
            {"name": "sol_cadence_autonomy_guard.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_cadence_autonomy_guard.py"},
            {"name": "sol_transaction_cadence_epoch.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_transaction_cadence_epoch.py"}
        ]
    },
    {
        "id": "domain_topology",
        "name": "Topology Domain",
        "description": "Manages manifold geometry, placements, state containers (carriers), and live relocations.",
        "files": [
            {"name": "sol_dimensional_topology.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_dimensional_topology.py"},
            {"name": "sol_distributed_state_relocation.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_distributed_state_relocation.py"},
            {"name": "sol_live_relocation.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_live_relocation.py"},
            {"name": "sol_manifold_placement.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_manifold_placement.py"}
        ]
    },
    {
        "id": "domain_pipeline_fault",
        "name": "Pipeline & Fault Matrix Domain",
        "description": "Handles geodesic pipeline segment balancing, stability audits, and safety recovery verification.",
        "files": [
            {"name": "sol_geodesic_pipeline_balancer.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_geodesic_pipeline_balancer.py"},
            {"name": "sol_pipeline_wavefront_fault_matrix.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_pipeline_wavefront_fault_matrix.py"},
            {"name": "sol_pipeline_wavefront_rollback_proof.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_pipeline_wavefront_rollback_proof.py"},
            {"name": "sol_pipeline_wavefront_safety_oracle.py", "path": "g:/docs/TechmanStudios/sol/tools/sol-core/sol_pipeline_wavefront_safety_oracle.py"}
        ]
    }
]

# Define manual domain connections (Domain -> Domain)
DOMAIN_CONNECTIONS = [
    {"from": "domain_topology", "to": "domain_waveguide", "label": "coordinates layout"},
    {"from": "domain_pipeline_fault", "to": "domain_runtime_engine", "label": "segment balancing"},
    {"from": "domain_runtime_engine", "to": "domain_cadence", "label": "clock sync"},
    {"from": "domain_cadence", "to": "domain_ledger", "label": "epoch locks"},
    {"from": "domain_rangers", "to": "domain_court", "label": "telemetry reports"},
    {"from": "domain_court", "to": "domain_ledger", "label": "docket verdicts"},
    {"from": "domain_ledger", "to": "domain_burnin", "label": "stability audit"},
    {"from": "domain_burnin", "to": "domain_release_candidate", "label": "readiness checks"},
    {"from": "domain_release_candidate", "to": "domain_finalization", "label": "manifest aggregation"}
]

# Define manual agent to domain connections
AGENT_TO_DOMAIN_CONNECTIONS = [
    {"from": "sol-orchestrator", "to": "domain_runtime_engine", "label": "triggers execution"},
    {"from": "sol-orchestrator", "to": "domain_pipeline_fault", "label": "runs smoke/pipeline"},
    {"from": "sol-orchestrator", "to": "domain_ledger", "label": "verifies SHA256 integrity"},
    {"from": "sol-rsi", "to": "domain_rangers", "label": "invokes ranger patrol"},
    {"from": "sol-rsi", "to": "domain_court", "label": "submits promotion docket"},
    {"from": "sol-rsi", "to": "domain_burnin", "label": "monitors long-horizon stability"},
    {"from": "sol-cortex", "to": "domain_runtime_engine", "label": "submits protocols"},
    {"from": "sol-evolve", "to": "domain_burnin", "label": "A/B tests mutations"},
    {"from": "sol-evolve", "to": "domain_release_candidate", "label": "submits parameter verdicts"},
    {"from": "sol-auto-mapper", "to": "domain_topology", "label": "sweeps coordinates"},
    {"from": "sol-auto-mapper", "to": "domain_waveguide", "label": "maps channels"},
    {"from": "continuity", "to": "domain_ledger", "label": "checks history checkouts"},
    {"from": "sol-knowledge-compiler", "to": "domain_ledger", "label": "docket signatures"},
    {"from": "sol-lab-master", "to": "domain_pipeline_fault", "label": "runs protocols"},
    {"from": "sol-data-analyst", "to": "domain_burnin", "label": "extracts stability drift"}
]

# Preset workflows for animation sequences
WORKFLOWS = [
    {
        "id": "workflow_research",
        "name": "Autonomous Research Loop",
        "description": "Triggered by a researcher or scheduler. Scans gaps, compiles protocols, runs on the engine, analyzes CSVs, and promotes findings.",
        "steps": [
            {"node": "user", "action": "Trigger research request"},
            {"node": "SolTech-StructureManager", "action": "Review workspace and delegate"},
            {"node": "sol-lab-master", "action": "Establish experiment parameters"},
            {"node": "sol-cortex", "action": "Scan knowledge & build protocol JSON"},
            {"node": "domain_runtime_engine", "action": "Execute protocol steps"},
            {"node": "sol-experiment-runner", "action": "Verify execution metrics"},
            {"node": "sol-data-analyst", "action": "Analyze CSV summaries & checks"},
            {"node": "sol-knowledge-compiler", "action": "Compile proof packet"},
            {"node": "domain_ledger", "action": "Log new findings & checkouts"}
        ]
    },
    {
        "id": "workflow_rsi",
        "name": "RSI Telemetry & Promotion Verdict",
        "description": "Patrols system states, triggers finalization rangers, submits docket to court, issues level-up verdicts, and logs to Ledger.",
        "steps": [
            {"node": "user", "action": "Schedule or label triggers RSI"},
            {"node": "sol-rsi", "action": "Initiate RSI sweep"},
            {"node": "domain_rangers", "action": "Patrol state invariants & compile reports"},
            {"node": "domain_court", "action": "Evaluate telemetry evidence"},
            {"node": "domain_ledger", "action": "Log court verdict to immutable hash chain"},
            {"node": "SolTech-StructureManager", "action": "Receive status update & promote"}
        ]
    },
    {
        "id": "workflow_evolve",
        "name": "Parameter Mutation & Burn-In",
        "description": "Evolves physics parameter bounds, runs A/B test simulations, computes drift/jitter in Burn-In, and freezes governance.",
        "steps": [
            {"node": "sol-evolve", "action": "Propose parameter mutation"},
            {"node": "domain_burnin", "action": "Execute long-horizon burn-in simulation"},
            {"node": "domain_runtime_engine", "action": "Run instruction loops"},
            {"node": "sol-data-analyst", "action": "Extract stability score"},
            {"node": "domain_release_candidate", "action": "Validate API contract & governance freeze"},
            {"node": "domain_finalization", "action": "Compile sealed system manifest"}
        ]
    },
    {
        "id": "workflow_topology",
        "name": "Topology Surgery & Relocation",
        "description": "Relocates active carriers across coordinate systems, mapping paths and rebalancing waveguide communication networks.",
        "steps": [
            {"node": "sol-auto-mapper", "action": "Initiate manifold sweep"},
            {"node": "domain_topology", "action": "Compute coordinate layout relocation"},
            {"node": "domain_waveguide", "action": "Rebalance Waveguide fabric ports"},
            {"node": "domain_cadence", "action": "Align epoch transaction clock boundaries"},
            {"node": "continuity", "action": "Commit relocation to repo-backed database"}
        ]
    }
]

def load_template():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SOL Sovereign Engine — Agentic Atlas</title>
    
    <!-- Google Fonts & FontAwesome -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Vis.js Standalone -->
    <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>

    <style>
        :root {
            --bg-color: #030308;
            --bg-darker: #010103;
            --panel-bg: rgba(10, 10, 22, 0.75);
            --border-color: rgba(0, 229, 255, 0.15);
            --text-color: #e2e8f0;
            --text-muted: #94a3b8;
            
            /* Neon Accent Palette */
            --accent-cyan: #00e5ff;
            --accent-blue: #3d5afe;
            --accent-purple: #d500f9;
            --accent-green: #00e676;
            --accent-orange: #ff9100;
            --accent-red: #ff1744;
            
            --panel-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
            --glass-blur: blur(12px);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(13, 13, 30, 0.8) 0%, rgba(3, 3, 8, 1) 90%),
                radial-gradient(circle at 90% 80%, rgba(26, 10, 40, 0.4) 0%, rgba(3, 3, 8, 1) 80%);
            color: var(--text-color);
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        /* Top Bar / Sovereign HUD Header */
        header {
            height: 70px;
            border-bottom: 1px solid var(--border-color);
            background: rgba(4, 4, 10, 0.9);
            backdrop-filter: var(--glass-blur);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            z-index: 100;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        }

        .header-logo-section {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .header-logo-icon {
            font-size: 24px;
            color: var(--accent-cyan);
            text-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
            animation: pulse-glow 3s infinite alternate;
        }

        .header-title-block h1 {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 1.5px;
            background: linear-gradient(135deg, #fff 30%, var(--accent-cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
        }

        .header-title-block p {
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .header-hud-stats {
            display: flex;
            align-items: center;
            gap: 32px;
        }

        .hud-stat-item {
            text-align: right;
        }

        .hud-stat-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
        }

        .hud-stat-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 15px;
            font-weight: 600;
            color: var(--accent-cyan);
        }

        .hud-stat-value.pulse-green {
            color: var(--accent-green);
        }

        /* Dashboard Workspace Layout */
        .workspace {
            flex: 1;
            display: flex;
            position: relative;
            height: calc(100vh - 70px);
        }

        /* Sidebars */
        .sidebar {
            width: 380px;
            background: var(--panel-bg);
            backdrop-filter: var(--glass-blur);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            z-index: 50;
            box-shadow: var(--panel-shadow);
            transition: transform 0.3s ease;
        }

        .sidebar-right {
            border-right: none;
            border-left: 1px solid var(--border-color);
        }

        .sidebar-padding {
            padding: 24px;
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .section-title {
            font-size: 13px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Search Input */
        .search-container {
            position: relative;
        }

        .search-input {
            width: 100%;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(0, 229, 255, 0.2);
            padding: 12px 16px 12px 42px;
            border-radius: 8px;
            color: white;
            font-size: 14px;
            font-family: inherit;
            transition: all 0.3s ease;
        }

        .search-input:focus {
            outline: none;
            border-color: var(--accent-cyan);
            box-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
        }

        .search-icon {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            pointer-events: none;
        }

        /* Layers Toggle Card */
        .layer-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            padding: 16px;
        }

        .toggle-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 0;
        }

        .toggle-label-sec {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            font-weight: 500;
        }

        .dot-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }

        /* Switch UI */
        .switch {
            position: relative;
            display: inline-block;
            width: 40px;
            height: 22px;
        }

        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            inset: 0;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 34px;
            transition: .4s;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 14px;
            width: 14px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            border-radius: 50%;
            transition: .4s;
        }

        input:checked + .slider {
            background-color: rgba(0, 229, 255, 0.2);
            border-color: var(--accent-cyan);
        }

        input:checked + .slider:before {
            transform: translateX(18px);
            background-color: var(--accent-cyan);
            box-shadow: 0 0 8px var(--accent-cyan);
        }

        /* Main Network Canvas area */
        .canvas-area {
            flex: 1;
            position: relative;
            background: #010103;
            overflow: hidden;
        }

        #network-graph {
            width: 100%;
            height: 100%;
            position: absolute;
            inset: 0;
        }

        /* Glassmorphism Inspector */
        .inspector-panel {
            background: rgba(5, 5, 15, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 16px;
            overflow-y: auto;
            position: relative;
        }

        .inspector-placeholder {
            margin: auto;
            text-align: center;
            color: var(--text-muted);
            font-size: 14px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }

        .inspector-placeholder i {
            font-size: 36px;
            opacity: 0.3;
        }

        .inspector-header {
            display: flex;
            flex-direction: column;
            gap: 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            padding-bottom: 14px;
        }

        .inspector-tag {
            align-self: flex-start;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-family: 'JetBrains Mono', monospace;
        }

        .inspector-name {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: white;
        }

        .inspector-description {
            font-size: 14px;
            color: var(--text-muted);
            line-height: 1.5;
        }

        .meta-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .meta-item {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .meta-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
        }

        .meta-value {
            font-size: 13px;
            color: var(--text-color);
            background: rgba(255, 255, 255, 0.02);
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.03);
            max-height: 120px;
            overflow-y: auto;
        }

        .meta-value-link {
            color: var(--accent-cyan);
            text-decoration: none;
            display: inline-block;
            margin-right: 8px;
            transition: text-shadow 0.2s ease;
        }

        .meta-value-link:hover {
            text-shadow: 0 0 6px var(--accent-cyan);
            text-decoration: underline;
        }

        /* Accordion for Markdown Sections */
        .section-accordion {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .accordion-item {
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.2);
        }

        .accordion-trigger {
            width: 100%;
            background: rgba(255, 255, 255, 0.02);
            border: none;
            color: var(--text-color);
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            font-family: inherit;
            font-size: 13px;
            font-weight: 600;
            text-align: left;
            transition: background 0.2s ease;
        }

        .accordion-trigger:hover {
            background: rgba(255, 255, 255, 0.05);
        }

        .accordion-content {
            display: none;
            padding: 14px 16px;
            font-size: 13px;
            line-height: 1.6;
            color: var(--text-muted);
            background: rgba(0, 0, 0, 0.1);
            border-top: 1px solid rgba(255, 255, 255, 0.03);
            white-space: pre-wrap;
            font-family: 'JetBrains Mono', monospace;
        }

        .accordion-item.active .accordion-content {
            display: block;
        }

        .accordion-item.active .accordion-trigger i {
            transform: rotate(180deg);
        }

        /* Preset Workflow Section */
        .workflow-section {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .workflow-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .workflow-card:hover {
            border-color: rgba(0, 229, 255, 0.3);
            background: rgba(0, 229, 255, 0.02);
            box-shadow: 0 4px 15px rgba(0, 229, 255, 0.05);
        }

        .workflow-card.active {
            border-color: var(--accent-cyan);
            background: rgba(0, 229, 255, 0.05);
            box-shadow: 0 4px 20px rgba(0, 229, 255, 0.15);
        }

        .workflow-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
        }

        .workflow-title {
            font-size: 14px;
            font-weight: 600;
            color: white;
        }

        .workflow-desc {
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.4;
            margin-bottom: 12px;
        }

        .workflow-play-btn {
            background: var(--accent-cyan);
            color: var(--bg-color);
            border: none;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            transition: all 0.2s ease;
        }

        .workflow-play-btn:hover {
            background: white;
            box-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
        }

        /* Workflow Steps Panel */
        .workflow-steps-panel {
            background: rgba(0, 0, 0, 0.3);
            border: 1px dashed rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 12px;
            display: none;
        }

        .workflow-card.active + .workflow-steps-panel {
            display: block;
            margin-top: -8px;
            margin-bottom: 8px;
        }

        .step-item {
            display: flex;
            gap: 12px;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            align-items: flex-start;
        }

        .step-item:last-child {
            border-bottom: none;
        }

        .step-num {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-color);
            font-size: 10px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'JetBrains Mono', monospace;
            flex: 0 0 auto;
            margin-top: 1px;
            transition: all 0.3s ease;
        }

        .step-item.highlighted .step-num {
            background: var(--accent-cyan);
            color: var(--bg-color);
            box-shadow: 0 0 8px var(--accent-cyan);
        }

        .step-details {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .step-node-name {
            font-size: 11px;
            font-weight: 700;
            color: var(--accent-cyan);
            text-transform: uppercase;
        }

        .step-action-desc {
            font-size: 12px;
            color: var(--text-color);
        }

        .step-item.highlighted .step-action-desc {
            color: white;
            font-weight: 500;
        }

        /* Tooltip style */
        .viz-tooltip {
            position: absolute;
            background: rgba(5, 5, 15, 0.95);
            border: 1px solid var(--accent-cyan);
            border-radius: 8px;
            padding: 10px 14px;
            box-shadow: var(--panel-shadow);
            z-index: 1000;
            pointer-events: none;
            display: none;
            max-width: 280px;
            font-size: 12px;
            line-height: 1.4;
        }

        /* Physics Stabilization HUD overlay */
        .stabilization-hud {
            position: absolute;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(4, 4, 10, 0.85);
            backdrop-filter: var(--glass-blur);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 8px 18px;
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 40;
            pointer-events: none;
            box-shadow: var(--panel-shadow);
            transition: opacity 0.5s ease;
        }

        .stabilization-hud.fade-out {
            opacity: 0;
        }

        .hud-spinner {
            width: 14px;
            height: 14px;
            border: 2px solid rgba(0, 229, 255, 0.1);
            border-top: 2px solid var(--accent-cyan);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        .hud-text {
            font-size: 11px;
            letter-spacing: 1px;
            text-transform: uppercase;
            font-weight: 600;
        }

        /* Physics / Graph Controls HUD overlay */
        .graph-controls {
            position: absolute;
            bottom: 24px;
            right: 24px;
            background: rgba(4, 4, 10, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 6px;
            display: flex;
            gap: 6px;
            z-index: 40;
        }

        .control-btn {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
            color: var(--text-color);
            width: 32px;
            height: 32px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .control-btn:hover {
            background: var(--accent-cyan);
            color: var(--bg-color);
            border-color: var(--accent-cyan);
            box-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
        }

        /* Animations */
        @keyframes pulse-glow {
            from {
                text-shadow: 0 0 5px rgba(0, 229, 255, 0.3);
            }
            to {
                text-shadow: 0 0 15px rgba(0, 229, 255, 0.8);
            }
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Custom Scrollbars */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(0,0,0,0.1);
        }

        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }

    </style>
</head>
<body>

    <!-- HUD Header -->
    <header>
        <div class="header-logo-section">
            <i class="fa-solid fa-atom header-logo-icon"></i>
            <div class="header-title-block">
                <h1>SOL Engine</h1>
                <p>Agentic Architecture & Engineering Atlas</p>
            </div>
        </div>

        <div class="header-hud-stats">
            <div class="hud-stat-item">
                <div class="hud-stat-label">Active Agents</div>
                <div id="hud-agent-count" class="hud-stat-value">15</div>
            </div>
            <div class="hud-stat-item">
                <div class="hud-stat-label">Eng. Domains</div>
                <div id="hud-domain-count" class="hud-stat-value">11</div>
            </div>
            <div class="hud-stat-item">
                <div class="hud-stat-label">Mapped Nodes</div>
                <div id="hud-node-count" class="hud-stat-value">31</div>
            </div>
            <div class="hud-stat-item">
                <div class="hud-stat-label">System Epoch</div>
                <div class="hud-stat-value pulse-green">Level 50 (Finalized)</div>
            </div>
        </div>
    </header>

    <!-- Main Workspace -->
    <div class="workspace">
        
        <!-- Left Sidebar: Controls & Inspector -->
        <div class="sidebar">
            <div class="sidebar-padding">
                
                <!-- Search & Filters -->
                <div class="search-container">
                    <i class="fa-solid fa-magnifying-glass search-icon"></i>
                    <input type="text" id="search-box" class="search-input" placeholder="Search agents, domains, tools, files...">
                </div>

                <!-- Layer Toggles -->
                <div class="layer-card">
                    <div class="section-title">
                        <i class="fa-solid fa-layer-group"></i> Layer Filters
                    </div>
                    <div class="toggle-row">
                        <div class="toggle-label-sec">
                            <span class="dot-indicator" style="background: var(--accent-purple);"></span>
                            <span>Agentic Layer</span>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="layer-agents" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="toggle-row">
                        <div class="toggle-label-sec">
                            <span class="dot-indicator" style="background: var(--accent-green);"></span>
                            <span>Engineering Domains</span>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="layer-domains" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="toggle-row">
                        <div class="toggle-label-sec">
                            <span class="dot-indicator" style="background: var(--accent-orange);"></span>
                            <span>Behavioral Contracts</span>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="layer-contracts" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="toggle-row">
                        <div class="toggle-label-sec">
                            <span class="dot-indicator" style="background: var(--accent-red);"></span>
                            <span>Storage & Artifacts</span>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="layer-outputs" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>

                <!-- Detail Inspector -->
                <div class="section-title" style="margin-bottom: 0;">
                    <i class="fa-solid fa-circle-info"></i> Detail Inspector
                </div>
                <div class="inspector-panel" id="inspector">
                    <div class="inspector-placeholder" id="inspector-placeholder">
                        <i class="fa-solid fa-circle-nodes"></i>
                        <p>Select any node in the graph to inspect its details, inputs, outputs, and source code files.</p>
                    </div>
                    <div id="inspector-content" style="display: none;">
                        <!-- Dynamically filled by JS -->
                    </div>
                </div>

            </div>
        </div>

        <!-- Center: Interactive Graph -->
        <div class="canvas-area">
            <div id="network-graph"></div>

            <!-- Stabilization HUD -->
            <div class="stabilization-hud" id="stabilization-hud">
                <div class="hud-spinner"></div>
                <div class="hud-text" id="stabilization-text">Stabilizing layout...</div>
            </div>

            <!-- Graph Camera Controls -->
            <div class="graph-controls">
                <div class="control-btn" id="btn-zoom-in" title="Zoom In"><i class="fa-solid fa-plus"></i></div>
                <div class="control-btn" id="btn-zoom-out" title="Zoom Out"><i class="fa-solid fa-minus"></i></div>
                <div class="control-btn" id="btn-fit" title="Fit Screen"><i class="fa-solid fa-expand"></i></div>
                <div class="control-btn" id="btn-physics" title="Toggle Physics"><i class="fa-solid fa-bolt"></i></div>
            </div>
        </div>

        <!-- Right Sidebar: Workflows & Specs -->
        <div class="sidebar sidebar-right">
            <div class="sidebar-padding">
                
                <!-- Preset Workflows -->
                <div class="section-title">
                    <i class="fa-solid fa-route"></i> Execution Workflows
                </div>
                
                <div class="workflow-section" id="workflow-list">
                    <!-- Dynamically filled by JS -->
                </div>

                <!-- Graph Legend -->
                <div class="layer-card">
                    <div class="section-title">
                        <i class="fa-solid fa-key"></i> Graph Legend
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 8px; font-size: 12px; color: var(--text-muted);">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="width: 12px; height: 12px; background: var(--accent-cyan); border-radius: 50%; display: inline-block;"></span>
                            <span style="color: white; font-weight: 500;">User Entry / Trigger</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="width: 12px; height: 12px; background: var(--accent-blue); border-radius: 3px; display: inline-block;"></span>
                            <span style="color: white; font-weight: 500;">Orchestration Hubs</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="width: 12px; height: 12px; background: var(--accent-purple); border-radius: 3px; display: inline-block;"></span>
                            <span style="color: white; font-weight: 500;">Autonomous Research Agents</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="width: 12px; height: 12px; background: var(--accent-green); clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%); display: inline-block;"></span>
                            <span style="color: white; font-weight: 500;">Codebase Engineering Domains</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="width: 12px; height: 12px; background: var(--accent-orange); border-radius: 6px; display: inline-block;"></span>
                            <span style="color: white; font-weight: 500;">Behavioral Contracts & Kit</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="width: 12px; height: 12px; background: var(--accent-red); border-radius: 4px; display: inline-block;"></span>
                            <span style="color: white; font-weight: 500;">Knowledge & Output Data</span>
                        </div>
                    </div>
                </div>

            </div>
        </div>

    </div>

    <!-- Live Tooltip -->
    <div id="graph-tooltip" class="viz-tooltip"></div>

    <script>
        // Embed the parsed agents database and engineering details directly
        const AGENTS_DATABASE = __AGENTS_JSON__;
        const ENGINEERING_DOMAINS = __DOMAINS_JSON__;
        const DOMAIN_CONNECTIONS = __DOMAIN_CONN_JSON__;
        const AGENT_TO_DOMAIN_CONNECTIONS = __AGENT_TO_DOMAIN_CONN_JSON__;
        const WORKFLOWS = __WORKFLOWS_JSON__;

        // Visualizer State
        let network = null;
        let nodesDataset = null;
        let edgesDataset = null;
        let activeWorkflowInterval = null;
        let physicsEnabled = true;

        // DOM elements
        const dom = {
            searchBox: document.getElementById('search-box'),
            inspectorPlaceholder: document.getElementById('inspector-placeholder'),
            inspectorContent: document.getElementById('inspector-content'),
            stabilizationHud: document.getElementById('stabilization-hud'),
            stabilizationText: document.getElementById('stabilization-text'),
            hudNodes: document.getElementById('hud-node-count'),
            workflowList: document.getElementById('workflow-list'),
            tooltip: document.getElementById('graph-tooltip'),
            btnZoomIn: document.getElementById('btn-zoom-in'),
            btnZoomOut: document.getElementById('btn-zoom-out'),
            btnFit: document.getElementById('btn-fit'),
            btnPhysics: document.getElementById('btn-physics'),
            layerAgents: document.getElementById('layer-agents'),
            layerDomains: document.getElementById('layer-domains'),
            layerContracts: document.getElementById('layer-contracts'),
            layerOutputs: document.getElementById('layer-outputs')
        };

        // Initialize App
        window.addEventListener('DOMContentLoaded', () => {
            setupWorkflowsUI();
            initGraph();
            setupInteractivity();
        });

        // Set up the Workflow cards UI in the right sidebar
        function setupWorkflowsUI() {
            dom.workflowList.innerHTML = '';
            WORKFLOWS.forEach(wf => {
                const card = document.createElement('div');
                card.className = 'workflow-card';
                card.id = wf.id;
                
                card.innerHTML = `
                    <div class="workflow-title-row">
                        <span class="workflow-title">${wf.name}</span>
                        <i class="fa-solid fa-chevron-down" style="font-size: 11px; opacity: 0.5;"></i>
                    </div>
                    <div class="workflow-desc">${wf.description}</div>
                    <button class="workflow-play-btn" onclick="triggerWorkflow('${wf.id}', event)">
                        <i class="fa-solid fa-play"></i> Run Workflow
                    </button>
                `;
                
                const stepsPanel = document.createElement('div');
                stepsPanel.className = 'workflow-steps-panel';
                stepsPanel.id = `${wf.id}_steps`;
                
                wf.steps.forEach((step, idx) => {
                    const stepItem = document.createElement('div');
                    stepItem.className = 'step-item';
                    stepItem.id = `${wf.id}_step_${idx}`;
                    stepItem.innerHTML = `
                        <div class="step-num">${idx + 1}</div>
                        <div class="step-details">
                            <span class="step-node-name">${step.node}</span>
                            <span class="step-action-desc">${step.action}</span>
                        </div>
                    `;
                    stepsPanel.appendChild(stepItem);
                });
                
                dom.workflowList.appendChild(card);
                dom.workflowList.appendChild(stepsPanel);
            });
        }

        // Initialize Vis.js network graph
        function initGraph() {
            const rawNodes = [];
            const rawEdges = [];

            // 1. User Entry
            rawNodes.push({
                id: 'user',
                label: 'User / Trigger',
                title: 'Local VS Code, Issue label, or cron schedule triggers',
                group: 'user',
                shape: 'dot',
                size: 25,
                color: {
                    background: '#030308',
                    border: 'var(--accent-cyan)',
                    highlight: { background: 'var(--accent-cyan)', border: 'var(--accent-cyan)' }
                },
                shadow: { enabled: true, color: 'var(--accent-cyan)', size: 10 }
            });

            // 2. Agents Layer (15 nodes)
            AGENTS_DATABASE.forEach(agent => {
                // Determine shape & size & border color based on agent type
                let isOrchestrator = ['SolTech-StructureManager', 'sol-lab-master', 'sol-orchestrator'].includes(agent.name);
                let borderCol = isOrchestrator ? 'var(--accent-blue)' : 'var(--accent-purple)';
                let glowCol = isOrchestrator ? 'rgba(61, 90, 254, 0.4)' : 'rgba(213, 0, 249, 0.4)';
                
                rawNodes.push({
                    id: agent.name,
                    label: agent.name,
                    title: agent.description,
                    group: 'agent',
                    shape: 'box',
                    size: 20,
                    font: { color: 'white', size: 13, face: 'Outfit' },
                    color: {
                        background: '#0d0d1e',
                        border: borderCol,
                        highlight: { background: '#1c1b3a', border: borderCol }
                    },
                    borderWidth: 1.5,
                    shadow: { enabled: true, color: glowCol, size: 8 }
                });

                // Handoff edges
                agent.handoffs.forEach(h => {
                    const targetName = typeof h === 'string' ? h : h.agent;
                    const edgeLabel = typeof h === 'string' ? 'handoff' : h.label;
                    
                    rawEdges.push({
                        from: agent.name,
                        to: targetName,
                        label: edgeLabel,
                        font: { size: 9, color: 'var(--text-muted)', face: 'Outfit', align: 'horizontal' },
                        color: { color: 'rgba(213, 0, 249, 0.35)', highlight: 'var(--accent-purple)' },
                        arrows: 'to',
                        width: 1.5,
                        dashes: false,
                        type: 'handoff'
                    });
                });
            });

            // Edge from User to StructureManager
            rawEdges.push({
                from: 'user',
                to: 'SolTech-StructureManager',
                label: 'request/trigger',
                font: { size: 9, color: 'var(--text-muted)', face: 'Outfit' },
                color: { color: 'rgba(0, 229, 255, 0.4)', highlight: 'var(--accent-cyan)' },
                arrows: 'to',
                width: 2,
                type: 'trigger'
            });

            // 3. Engineering Domains Layer (11 nodes)
            ENGINEERING_DOMAINS.forEach(domain => {
                rawNodes.push({
                    id: domain.id,
                    label: domain.name.replace(' Domain', ''),
                    title: domain.description,
                    group: 'domain',
                    shape: 'hexagon',
                    font: { color: 'white', size: 12, face: 'Outfit' },
                    color: {
                        background: '#071610',
                        border: 'var(--accent-green)',
                        highlight: { background: '#0e2b20', border: 'var(--accent-green)' }
                    },
                    borderWidth: 1.5,
                    shadow: { enabled: true, color: 'rgba(0, 230, 118, 0.3)', size: 8 }
                });
            });

            // Domain to Domain pipelines
            DOMAIN_CONNECTIONS.forEach(conn => {
                rawEdges.push({
                    from: conn.from,
                    to: conn.to,
                    label: conn.label,
                    font: { size: 8, color: 'var(--text-muted)', face: 'Outfit', align: 'horizontal' },
                    color: { color: 'rgba(0, 230, 118, 0.25)', highlight: 'var(--accent-green)' },
                    arrows: 'to',
                    width: 1,
                    dashes: [4, 4],
                    type: 'domain'
                });
            });

            // Agent to Domain bindings
            AGENT_TO_DOMAIN_CONNECTIONS.forEach(conn => {
                rawEdges.push({
                    from: conn.from,
                    to: conn.to,
                    label: conn.label,
                    font: { size: 8, color: 'var(--text-muted)', face: 'Outfit', align: 'horizontal' },
                    color: { color: 'rgba(0, 229, 255, 0.2)', highlight: 'var(--accent-cyan)' },
                    arrows: 'to',
                    width: 1.2,
                    dashes: [2, 2],
                    type: 'agent_domain'
                });
            });

            // 4. Behavioral Contracts Layer (4 nodes)
            const contracts = [
                { id: 'instructions', label: 'Instructions\\n(.github/instructions/*.md)', desc: 'Coding, baseline, style and workflow rules' },
                { id: 'prompts', label: 'Prompts\\n(.github/prompts/*.md)', desc: 'Run bundle templates, incidents, plans' },
                { id: 'skills', label: 'Skills\\n(.github/skills/*)', desc: 'Reusable agent capabilities and packages' },
                { id: 'workflows', label: 'GitHub Workflows\\nsol-pipeline.yml, cortex.yml, rsi.yml', desc: 'GitHub actions orchestration scripts' }
            ];

            contracts.forEach(c => {
                rawNodes.push({
                    id: c.id,
                    label: c.label,
                    title: c.desc,
                    group: 'contract',
                    shape: 'ellipse',
                    font: { color: 'white', size: 10, face: 'Outfit' },
                    color: {
                        background: '#1c0e01',
                        border: 'var(--accent-orange)',
                        highlight: { background: '#301802', border: 'var(--accent-orange)' }
                    },
                    borderWidth: 1,
                    shadow: { enabled: true, color: 'rgba(255, 145, 0, 0.25)', size: 6 }
                });

                // Link instructions/prompts to StructureManager
                rawEdges.push({
                    from: c.id,
                    to: 'SolTech-StructureManager',
                    label: 'governs',
                    font: { size: 7, color: 'var(--text-muted)', face: 'Outfit' },
                    color: { color: 'rgba(255, 145, 0, 0.25)', highlight: 'var(--accent-orange)' },
                    arrows: 'to',
                    width: 1,
                    dashes: true,
                    type: 'contract'
                });
            });

            // Specific workflow/trigger mapping to runtime tools
            rawEdges.push({
                from: 'workflows',
                to: 'domain_runtime_engine',
                label: 'runs pipeline',
                font: { size: 7, color: 'var(--text-muted)', face: 'Outfit' },
                color: { color: 'rgba(255, 145, 0, 0.25)', highlight: 'var(--accent-orange)' },
                arrows: 'to',
                width: 1,
                type: 'contract'
            });

            // 5. Storage / Outputs Layer (3 nodes)
            const outputs = [
                { id: 'data_folder', label: 'data/*\\n(sessions, runs, traces)', desc: 'Execution trace metrics and reports' },
                { id: 'sol_knowledge', label: 'solKnowledge/*\\n(consolidated, proof_packets)', desc: 'Clean, verified knowledge database' },
                { id: 'kb_youtube', label: 'knowledge/youtube\\n(source corpus)', desc: 'Ground truth Youtube transcription index' }
            ];

            outputs.forEach(o => {
                rawNodes.push({
                    id: o.id,
                    label: o.label,
                    title: o.desc,
                    group: 'output',
                    shape: 'database',
                    font: { color: 'white', size: 10, face: 'Outfit' },
                    color: {
                        background: '#1d050a',
                        border: 'var(--accent-red)',
                        highlight: { background: '#350a13', border: 'var(--accent-red)' }
                    },
                    borderWidth: 1,
                    shadow: { enabled: true, color: 'rgba(255, 23, 68, 0.25)', size: 6 }
                });
            });

            // Data flow connections
            rawEdges.push({ from: 'domain_runtime_engine', to: 'data_folder', label: 'writes traces', font: { size: 7, color: 'var(--text-muted)' }, color: { color: 'rgba(255, 23, 68, 0.2)' }, arrows: 'to' });
            rawEdges.push({ from: 'data_folder', to: 'sol_knowledge', label: 'promotes findings', font: { size: 7, color: 'var(--text-muted)' }, color: { color: 'rgba(255, 23, 68, 0.2)' }, arrows: 'to' });
            rawEdges.push({ from: 'kb_youtube', to: 'sol_knowledge', label: 'grounds', font: { size: 7, color: 'var(--text-muted)' }, color: { color: 'rgba(255, 23, 68, 0.2)' }, arrows: 'to' });

            // Create vis datasets
            nodesDataset = new vis.DataSet(rawNodes);
            edgesDataset = new vis.DataSet(rawEdges);

            // Graph Options
            const container = document.getElementById('network-graph');
            const data = { nodes: nodesDataset, edges: edgesDataset };
            const options = {
                nodes: {
                    font: {
                        face: 'Outfit',
                        color: '#ffffff'
                    },
                    margin: { top: 12, bottom: 12, left: 16, right: 16 }
                },
                edges: {
                    font: {
                        face: 'Outfit',
                        strokeWidth: 0,
                        color: 'rgba(255,255,255,0.7)'
                    },
                    smooth: {
                        type: 'cubicBezier',
                        forceDirection: 'none',
                        roundness: 0.15
                    }
                },
                groups: {
                    user: { shape: 'dot' },
                    agent: { shape: 'box' },
                    domain: { shape: 'hexagon' },
                    contract: { shape: 'ellipse' },
                    output: { shape: 'database' }
                },
                physics: {
                    enabled: true,
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {
                        gravitationalConstant: -260,
                        centralGravity: 0.005,
                        springLength: 220,
                        springConstant: 0.08,
                        damping: 0.4,
                        avoidOverlap: 1.0
                    },
                    stabilization: {
                        enabled: true,
                        iterations: 1500,
                        updateInterval: 50
                    }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 300,
                    navigationButtons: false,
                    keyboard: false
                }
            };

            network = new vis.Network(container, data, options);
            dom.hudNodes.innerText = rawNodes.length;

            // Events
            network.on('stabilizationProgress', function(params) {
                const percentage = Math.round((params.iterations / params.total) * 100);
                dom.stabilizationText.innerText = `Stabilizing Layout: ${percentage}%`;
            });

            network.on('stabilizationIterationsDone', function() {
                dom.stabilizationHud.classList.add('fade-out');
            });

            network.on('click', function(params) {
                if (params.nodes.length > 0) {
                    const nodeId = params.nodes[0];
                    inspectNode(nodeId);
                    highlightNeighbors(nodeId);
                } else {
                    resetInspection();
                    resetHighlighting();
                }
            });

            network.on('hoverNode', function(params) {
                // Show floating tooltip
                const node = nodesDataset.get(params.node);
                dom.tooltip.style.display = 'block';
                dom.tooltip.innerHTML = `<strong>${node.label.replace('\\n', ' ')}</strong><br/><span style="color:var(--text-muted);">${node.title || ''}</span>`;
            });

            network.on('blurNode', function() {
                dom.tooltip.style.display = 'none';
            });
            
            // Track mouse for tooltip
            container.addEventListener('mousemove', function(e) {
                const rect = container.getBoundingClientRect();
                dom.tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
                dom.tooltip.style.top = (e.clientY - rect.top + 15) + 'px';
            });
        }

        // Search, Filters & Buttons setup
        function setupInteractivity() {
            // Search Filtering
            dom.searchBox.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase().strip ? e.target.value.toLowerCase().trim() : e.target.value.toLowerCase();
                if (!query) {
                    resetHighlighting();
                    return;
                }
                
                const matchedNodeIds = [];
                nodesDataset.forEach(node => {
                    const label = (node.label || '').toLowerCase();
                    const title = (node.title || '').toLowerCase();
                    
                    if (label.includes(query) || title.includes(query)) {
                        matchedNodeIds.push(node.id);
                    }
                });
                
                if (matchedNodeIds.length > 0) {
                    // Highlight these nodes
                    highlightNodeSet(matchedNodeIds);
                    if (matchedNodeIds.length === 1) {
                        inspectNode(matchedNodeIds[0]);
                        network.focus(matchedNodeIds[0], { scale: 1.2, animation: true });
                    }
                } else {
                    resetHighlighting();
                }
            });

            // Layer Visibility controls
            const toggleLayer = (groupId, checkbox) => {
                nodesDataset.forEach(node => {
                    if (node.group === groupId || (groupId === 'agent' && node.id === 'user')) {
                        nodesDataset.update({ id: node.id, hidden: !checkbox.checked });
                    }
                });
            };

            dom.layerAgents.addEventListener('change', (e) => toggleLayer('agent', e.target));
            dom.layerDomains.addEventListener('change', (e) => toggleLayer('domain', e.target));
            
            // Bind Contract & Output toggles
            dom.layerContracts.addEventListener('change', (e) => {
                nodesDataset.forEach(node => {
                    if (node.group === 'contract') {
                        nodesDataset.update({ id: node.id, hidden: !e.target.checked });
                    }
                });
            });
            dom.layerOutputs.addEventListener('change', (e) => {
                nodesDataset.forEach(node => {
                    if (node.group === 'output') {
                        nodesDataset.update({ id: node.id, hidden: !e.target.checked });
                    }
                });
            });

            // Camera button controls
            dom.btnZoomIn.addEventListener('click', () => {
                network.moveTo({ scale: network.getScale() * 1.3, animation: true });
            });
            dom.btnZoomOut.addEventListener('click', () => {
                network.moveTo({ scale: network.getScale() * 0.7, animation: true });
            });
            dom.btnFit.addEventListener('click', () => {
                network.fit({ animation: true });
            });
            dom.btnPhysics.addEventListener('click', () => {
                physicsEnabled = !physicsEnabled;
                network.setOptions({ physics: { enabled: physicsEnabled } });
                dom.btnPhysics.style.background = physicsEnabled ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.04)';
                dom.btnPhysics.style.color = physicsEnabled ? 'var(--bg-color)' : 'var(--text-color)';
            });
        }

        // Highlight neighbor nodes and edges on select
        function highlightNeighbors(nodeId) {
            const connectedNodes = network.getConnectedNodes(nodeId);
            const connectedEdges = network.getConnectedEdges(nodeId);

            // Dim everything
            nodesDataset.forEach(node => {
                nodesDataset.update({
                    id: node.id,
                    opacity: (node.id === nodeId || connectedNodes.includes(node.id)) ? 1 : 0.15
                });
            });

            edgesDataset.forEach(edge => {
                edgesDataset.update({
                    id: edge.id,
                    color: connectedEdges.includes(edge.id) ? { color: edge.color.highlight || 'var(--accent-cyan)' } : { color: 'rgba(255,255,255,0.03)' },
                    width: connectedEdges.includes(edge.id) ? 2.5 : 0.8
                });
            });
        }

        // Highlight a custom subset of nodes
        function highlightNodeSet(nodeIds) {
            nodesDataset.forEach(node => {
                nodesDataset.update({
                    id: node.id,
                    opacity: nodeIds.includes(node.id) ? 1 : 0.15
                });
            });
            edgesDataset.forEach(edge => {
                const connected = nodeIds.includes(edge.from) && nodeIds.includes(edge.to);
                edgesDataset.update({
                    id: edge.id,
                    color: connected ? { color: 'var(--accent-cyan)' } : { color: 'rgba(255,255,255,0.03)' },
                    width: connected ? 2 : 0.8
                });
            });
        }

        // Reset highlights
        function resetHighlighting() {
            nodesDataset.forEach(node => {
                nodesDataset.update({ id: node.id, opacity: 1 });
            });
            edgesDataset.forEach(edge => {
                let defaultCol = 'rgba(255,255,255,0.15)';
                if (edge.type === 'handoff') defaultCol = 'rgba(213, 0, 249, 0.35)';
                if (edge.type === 'domain') defaultCol = 'rgba(0, 230, 118, 0.25)';
                if (edge.type === 'agent_domain') defaultCol = 'rgba(0, 229, 255, 0.2)';
                if (edge.type === 'contract') defaultCol = 'rgba(255, 145, 0, 0.25)';
                
                edgesDataset.update({
                    id: edge.id,
                    color: { color: defaultCol },
                    width: edge.type === 'trigger' ? 2 : 1
                });
            });
        }

        // Reset detail inspection panel
        function resetInspection() {
            dom.inspectorContent.style.display = 'none';
            dom.inspectorPlaceholder.style.display = 'flex';
        }

        // Inspect a Node and populate the details panel
        function inspectNode(nodeId) {
            dom.inspectorPlaceholder.style.display = 'none';
            dom.inspectorContent.style.display = 'block';
            
            // Check if it's an agent
            const agent = AGENTS_DATABASE.find(a => a.name === nodeId);
            if (agent) {
                renderAgentDetails(agent);
                return;
            }

            // Check if it's a domain
            const domain = ENGINEERING_DOMAINS.find(d => d.id === nodeId);
            if (domain) {
                renderDomainDetails(domain);
                return;
            }

            // Fallback generic info
            const node = nodesDataset.get(nodeId);
            renderGenericDetails(node);
        }

        // Render Agent Details
        function renderAgentDetails(agent) {
            let toolsHtml = agent.tools && agent.tools.length > 0 
                ? agent.tools.map(t => `<code style="display:inline-block; background:rgba(255,255,255,0.05); padding:2px 6px; border-radius:4px; margin:2px; font-size:11px;">${t}</code>`).join(' ')
                : '<span style="color:var(--text-muted);">None declared</span>';

            let handoffsHtml = agent.handoffs && agent.handoffs.length > 0
                ? agent.handoffs.map(h => {
                    const name = typeof h === 'string' ? h : h.agent;
                    const desc = typeof h === 'string' ? '' : ` — <span style="font-size:11px; color:var(--text-muted);">${h.prompt}</span>`;
                    return `<div style="margin:4px 0;"><a href="#" onclick="selectNode('${name}'); return false;" style="color:var(--accent-purple); font-weight:600; text-decoration:none;">${name}</a>${desc}</div>`;
                }).join('')
                : '<span style="color:var(--text-muted);">None</span>';

            // Clickable file path
            const cleanPath = agent.filepath.replace(/\\\\/g, '/');
            const fileLinkHtml = `<a href="file:///${cleanPath}" class="meta-value-link" target="_blank">${agent.filename}</a>`;

            // Accordion sections
            let accordionHtml = '';
            for (const [secTitle, secContent] of Object.entries(agent.sections)) {
                if (secTitle === 'General' || !secContent || secContent.length === 0) continue;
                
                accordionHtml += `
                    <div class="accordion-item" id="accordion_${secTitle.replace(/\\s+/g, '_')}">
                        <button class="accordion-trigger" onclick="toggleAccordion('accordion_${secTitle.replace(/\\s+/g, '_')}')">
                            <span>${secTitle}</span>
                            <i class="fa-solid fa-chevron-down"></i>
                        </button>
                        <div class="accordion-content">${escapeHtml(secContent)}</div>
                    </div>
                `;
            }

            dom.inspectorContent.innerHTML = `
                <div class="inspector-header">
                    <span class="inspector-tag" style="background:rgba(213,0,249,0.15); color:var(--accent-purple); border:1px solid rgba(213,0,249,0.3)">Agent Profile</span>
                    <h2 class="inspector-name">${agent.name}</h2>
                </div>
                
                <p class="inspector-description">${agent.description || 'No description provided.'}</p>
                
                <div class="meta-list">
                    <div class="meta-item">
                        <span class="meta-label">Associated File</span>
                        <div class="meta-value">${fileLinkHtml}</div>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Handoff Ports</span>
                        <div class="meta-value" style="max-height: 180px;">${handoffsHtml}</div>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Tools Equiped</span>
                        <div class="meta-value" style="max-height: 120px;">${toolsHtml}</div>
                    </div>
                </div>

                <div class="section-title" style="margin-top:10px; margin-bottom:0;">
                    <i class="fa-solid fa-file-invoice"></i> System Directives
                </div>
                <div class="section-accordion">
                    ${accordionHtml}
                </div>
            `;
        }

        // Render Engineering Domain Details
        function renderDomainDetails(domain) {
            let filesHtml = domain.files && domain.files.length > 0
                ? domain.files.map(f => {
                    const cleanPath = f.path.replace(/\\\\/g, '/');
                    return `<div style="margin:6px 0;"><a href="file:///${cleanPath}" class="meta-value-link" target="_blank"><i class="fa-regular fa-file-code" style="margin-right:6px;"></i>${f.name}</a></div>`;
                }).join('')
                : '<span style="color:var(--text-muted);">None registered</span>';

            dom.inspectorContent.innerHTML = `
                <div class="inspector-header">
                    <span class="inspector-tag" style="background:rgba(0,230,118,0.15); color:var(--accent-green); border:1px solid rgba(0,230,118,0.3)">Engineering Domain</span>
                    <h2 class="inspector-name">${domain.name}</h2>
                </div>
                
                <p class="inspector-description">${domain.description}</p>
                
                <div class="meta-list">
                    <div class="meta-item">
                        <span class="meta-label">Key Core Modules</span>
                        <div class="meta-value" style="max-height: 250px;">${filesHtml}</div>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Domain ID</span>
                        <div class="meta-value"><code style="font-family:'JetBrains Mono'; color:var(--accent-green);">${domain.id}</code></div>
                    </div>
                </div>
            `;
        }

        // Render generic details (User, Contracts, etc.)
        function renderGenericDetails(node) {
            let tagName = 'System Node';
            let tagColor = 'var(--text-muted)';
            let tagBg = 'rgba(255,255,255,0.05)';
            
            if (node.id === 'user') {
                tagName = 'User Interface';
                tagColor = 'var(--accent-cyan)';
                tagBg = 'rgba(0, 229, 255, 0.1)';
            } else if (node.group === 'contract') {
                tagName = 'Behavior Contract';
                tagColor = 'var(--accent-orange)';
                tagBg = 'rgba(255, 145, 0, 0.1)';
            } else if (node.group === 'output') {
                tagName = 'Database / Storage';
                tagColor = 'var(--accent-red)';
                tagBg = 'rgba(255, 23, 68, 0.1)';
            }

            dom.inspectorContent.innerHTML = `
                <div class="inspector-header">
                    <span class="inspector-tag" style="background:${tagBg}; color:${tagColor}; border:1px solid ${tagColor}40">${tagName}</span>
                    <h2 class="inspector-name">${node.label.replace('\\n', ' ')}</h2>
                </div>
                
                <p class="inspector-description">${node.title || 'No description available.'}</p>
            `;
        }

        // Helper to programmatically select a node
        function selectNode(nodeId) {
            network.selectNodes([nodeId]);
            inspectNode(nodeId);
            highlightNeighbors(nodeId);
            network.focus(nodeId, { scale: 1.1, animation: true });
        }

        // Accordion toggle helper
        function toggleAccordion(itemId) {
            const item = document.getElementById(itemId);
            if (item) {
                item.classList.toggle('active');
            }
        }

        // Trigger Workflow animation
        function triggerWorkflow(workflowId, event) {
            if (event) {
                event.stopPropagation();
            }

            // Clear any active workflow
            if (activeWorkflowInterval) {
                clearInterval(activeWorkflowInterval);
                activeWorkflowInterval = null;
            }

            // Remove active status from all workflow cards
            document.querySelectorAll('.workflow-card').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.step-item').forEach(s => s.classList.remove('highlighted'));

            const wf = WORKFLOWS.find(w => w.id === workflowId);
            if (!wf) return;

            // Mark card active
            const card = document.getElementById(workflowId);
            card.classList.add('active');

            let currentStepIdx = 0;

            const runStep = () => {
                // Remove highlighting from previous step
                document.querySelectorAll('.step-item').forEach(s => s.classList.remove('highlighted'));

                if (currentStepIdx >= wf.steps.length) {
                    // Reset at the end of the workflow
                    resetHighlighting();
                    clearInterval(activeWorkflowInterval);
                    activeWorkflowInterval = null;
                    return;
                }

                // Highlight step item in right sidebar
                const stepElement = document.getElementById(`${workflowId}_step_${currentStepIdx}`);
                if (stepElement) {
                    stepElement.classList.add('highlighted');
                    stepElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }

                const step = wf.steps[currentStepIdx];
                
                // Inspect node
                inspectNode(step.node);

                // Flash node on canvas by making it opaque and styling edges
                nodesDataset.forEach(node => {
                    nodesDataset.update({
                        id: node.id,
                        opacity: node.id === step.node ? 1.0 : 0.2
                    });
                });

                edgesDataset.forEach(edge => {
                    const isActive = edge.from === step.node || edge.to === step.node;
                    edgesDataset.update({
                        id: edge.id,
                        color: isActive ? { color: 'var(--accent-cyan)' } : { color: 'rgba(255,255,255,0.03)' },
                        width: isActive ? 3 : 0.8
                    });
                });

                // Focus/zoom camera on the active node
                network.focus(step.node, { scale: 1.15, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });

                currentStepIdx++;
            };

            // Run first step immediately, then cycle every 2.8 seconds
            runStep();
            activeWorkflowInterval = setInterval(runStep, 2800);
        }

        // HTML escaping helper
        function escapeHtml(text) {
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

    </script>
</body>
</html>
"""

def main():
    # Paths
    agents_json_path = Path("g:/docs/TechmanStudios/sol/scratch/sol_agents_data.json")
    output_html_path = Path("g:/docs/TechmanStudios/sol/sol_agent_architecture_graph.html")
    
    # Load parsed agents
    with open(agents_json_path, "r", encoding="utf-8") as f:
        agents_data = json.load(f)
        
    template_str = load_template()
    
    # Replace JSON placeholders
    rendered_html = template_str.replace("__AGENTS_JSON__", json.dumps(agents_data))
    rendered_html = rendered_html.replace("__DOMAINS_JSON__", json.dumps(ENGINEERING_DOMAINS))
    rendered_html = rendered_html.replace("__DOMAIN_CONN_JSON__", json.dumps(DOMAIN_CONNECTIONS))
    rendered_html = rendered_html.replace("__AGENT_TO_DOMAIN_CONN_JSON__", json.dumps(AGENT_TO_DOMAIN_CONNECTIONS))
    rendered_html = rendered_html.replace("__WORKFLOWS_JSON__", json.dumps(WORKFLOWS))
    
    # Write to target dashboard
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
        
    print(f"Successfully generated visual graph dashboard at {output_html_path}")

if __name__ == "__main__":
    main()
