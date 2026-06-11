# Architecture Map

This document maps the major components of the Sovereign Runtime codebase by engineering domain.

---

## 1. Runtime Engine Domain
Responsible for instruction execution, SIMD lane masking, vector registers, scheduling, and core loops.
* [sol_sovereign_runtime.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_sovereign_runtime.py) - Main runtime state orchestrator and command submission processor.
* [sol_engine.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_engine.py) - Primary execution backend mapping WideWord instructions.
* [sol_runtime_scheduler.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_runtime_scheduler.py) - Manages task queues, execution threads, and synchronization barriers.
* [sol_simd_core_integration.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_simd_core_integration.py) - Integrates parallel SIMD lanes.
* [sol_simd_modes.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_simd_modes.py) - Defines SIMD masking modes and register operations.

---

## 2. Rangers Domain
Patrols the runtime state and evaluates local invariants to compile signed telemetry reports.
* [finalization_ranger.py](file:///g:/docs/TechmanStudios/sol/tools/sol-rsi/coding_library/sovereign_domain/rangers/finalization_ranger.py) - Evaluates Level 50 finalization gates and invariants.
* [ranger_registry.json](file:///g:/docs/TechmanStudios/sol/tools/sol-rsi/coding_library/sovereign_domain/ranger_registry.json) - Contains registrations of active patrol rangers.

---

## 3. Court Domain
Supervises state promotion, evaluates ranger evidence, and issues binding level-up verdicts.
* [sol_court_supervised_promotion.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_court_supervised_promotion.py) - Enforces promotion gate evaluation policies.
* [promotion_court.py](file:///g:/docs/TechmanStudios/sol/tools/sol-rsi/coding_library/sovereign_domain/promotion_court.py) - Models promotion judges, verdicts, and docket signatures.
* [promotion_gates.json](file:///g:/docs/TechmanStudios/sol/tools/sol-rsi/coding_library/sovereign_domain/promotion_gates.json) - Defines required invariants for Level 0 through 50 promotion gates.

---

## 4. Ledger Domain
Maintains append-only, tamper-evident hash chains documenting all coordinate updates and promotion events.
* [sol_runtime_ledger.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_runtime_ledger.py) - Logs execution states, checkpoint logs, and docket promotions.
* [sol_long_horizon_stability_ledger.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_long_horizon_stability_ledger.py) - Logs stability metrics and burn-in metrics.

---

## 5. Burn-In Domain
Handles long-horizon runtime validation, continuous stress tests, and stability calculations.
* [sol_sovereign_burnin_runtime.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_sovereign_burnin_runtime.py) - Executes sequential burn-in cycles and calculates stability readiness scores.
* [sol_burnin_promotion_readiness.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_burnin_promotion_readiness.py) - Compares stability benchmarks against target promotion scores.
* [sol_burnin_regression_detector.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_burnin_regression_detector.py) - Identifies execution performance degradation.
* [sol_burnin_stability_metrics.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_burnin_stability_metrics.py) - Calculates variance, drift, and jitter.

---

## 6. Release Candidate Domain
Freezes APIs, validates stability metrics, and packages manifests prior to system finalization.
* [sol_release_candidate_manifest.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_release_candidate_manifest.py) - Constructs release candidate manifests and exports evidence.
* [sol_governance_freeze.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_governance_freeze.py) - Implements configuration snapshot lockouts and governance freezes.
* [sol_api_stability_contract.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_api_stability_contract.py) - Enforces API signatures and interface invariants.

---

## 7. Finalization Domain
Secures final gateways, aggregates dockets, and performs system lockdown validations.
* [sol_production_gateway.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_production_gateway.py) - Implements the sealed default-deny production gateway check.
* [sol_final_system_manifest.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_final_system_manifest.py) - Compiles all Level 49 manifests, freezes, and verdicts into a final manifest.
* [sol_final_gate_registry.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_final_gate_registry.py) - Registry of final Level 50 promotion gates.
* [sol_production_readiness_guard.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_production_readiness_guard.py) - Reads manifests and enforces `production_blocked` status.
* [sol_system_lockdown.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_system_lockdown.py) - Validates configuration snapshots against drift and unauthorized writes.
* [sol_runtime_handoff_manifest.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_runtime_handoff_manifest.py) - Captures inventory checklists, verify script paths, and fallback procedures.
* [sol_finalization_docket.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_finalization_docket.py) - Final docket container presenting evidence to the promotion court.

---

## 8. Waveguide Domain
Coordinates wave propagation channels, synthesis, and routing logic across execution domains.
* [sol_core_waveguide_binding.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_core_waveguide_binding.py) - Links logical communication ports to waveguide physical channels.
* [sol_hierarchical_waveguide_fabric.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_hierarchical_waveguide_fabric.py) - Connects multi-layer waveguide hierarchies.
* [sol_dynamic_waveguide_rebalancer.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_dynamic_waveguide_rebalancer.py) - Re-allocates routing lanes to balance bandwidth.
* [sol_waveguide_fabric_synthesis.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_waveguide_fabric_synthesis.py) - Synthesizes logical layouts from physical topology constraints.

---

## 9. Cadence Domain
Synchronizes coordinate clocks, aligns epochs, and handles consensus across sharded manifolds.
* [sol_temporal_cadence.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_temporal_cadence.py) - Main coordinate clock alignment module.
* [sol_autonomous_cadence_sync.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_autonomous_cadence_sync.py) - Coordinates drift correction between sharded clocks.
* [sol_cadence_autonomy_guard.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_cadence_autonomy_guard.py) - Prevents sync overrun and clock drift.
* [sol_transaction_cadence_epoch.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_transaction_cadence_epoch.py) - Aligns transaction commitments with clock boundaries.

---

## 10. Topology Domain
Manages manifold geometry, placements, state containers (carriers), and live relocations.
* [sol_dimensional_topology.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_dimensional_topology.py) - Models multi-dimensional coordinates and coordinate mappings.
* [sol_distributed_state_relocation.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_distributed_state_relocation.py) - Manages multi-manifold relocation protocols.
* [sol_live_relocation.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_live_relocation.py) - Performs online relocation of carriers with active routing updates.
* [sol_manifold_placement.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_manifold_placement.py) - Computes optimal placement vectors for state shards.

---

## 11. Pipeline & Fault Matrix Domain
Handles geodesic pipeline segment balancing, stability audits, and safety recovery verification.
* [sol_geodesic_pipeline_balancer.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_geodesic_pipeline_balancer.py) - Balances work distribution across geodesic segments.
* [sol_pipeline_wavefront_fault_matrix.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_pipeline_wavefront_fault_matrix.py) - Injects deterministic faults to audit pipeline recovery.
* [sol_pipeline_wavefront_rollback_proof.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_pipeline_wavefront_rollback_proof.py) - Verifies successful rollback to safe configurations under injected faults.
* [sol_pipeline_wavefront_safety_oracle.py](file:///g:/docs/TechmanStudios/sol/tools/sol-core/sol_pipeline_wavefront_safety_oracle.py) - Oracle detecting boundary violations and triggering rollback.
