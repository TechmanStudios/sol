# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Roaming & Dispatcher Agents (Mobile Agents)
===================================================
Autonomous agents that traverse execution, compilation, and filesystem contexts
to inspect live environments, run diagnostics, apply hotfixes, and collect logs.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Resolve paths
lib_dir = Path(__file__).resolve().parent
sol_root = lib_dir.parent.parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "tools" / "sol-llm"))

from coding_library.experts import LuminaExpert

class LuminaRoamingAgent(LuminaExpert):
    """Base class for mobile Lumina agents that travel between memory and environments."""

    def __init__(self, name: str, system_prompt: str, lib_agent=None):
        super().__init__(name, system_prompt, lib_agent)
        self.current_context: Any = None
        self.state_history: List[str] = []

    def travel(self, destination_context: Any):
        """Move the agent to a target context/environment."""
        dest_name = str(destination_context)
        if hasattr(destination_context, "__class__"):
            dest_name = destination_context.__class__.__name__
        self.current_context = destination_context
        log_msg = f"Traveled to context: {dest_name} at {datetime.now(timezone.utc).isoformat()}"
        self.state_history.append(log_msg)
        return self

    def report_back(self) -> Dict[str, Any]:
        """Compile state logs and findings to return to the library."""
        return {
            "agent": self.name,
            "current_context": str(self.current_context),
            "state_history": self.state_history,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class LuminaSubstrateRanger(LuminaRoamingAgent):
    """Roaming diagnostic ranger that inspects active simulation manifolds in-situ."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Lumina Substrate Ranger. You travel directly to active simulation manifolds\n"
            "and sequencers. You inspect the live mathematical states (density, pressure, phase alignment)\n"
            "and generate real-time tuning and override recommendations to ensure register mass preservation."
        )
        super().__init__("Lumina Substrate Ranger", system_prompt, lib_agent)

    def run_diagnostics(self) -> Dict[str, Any]:
        """Inspects live current_context (expected to be a MicroInstructionSequencer or ManifoldGroup) and checks mass limits."""
        if not self.current_context:
            return {"status": "ERROR", "message": "No active context. Ranger must travel to a target first."}

        # Try to resolve ManifoldGroup from context
        group = self.current_context
        if hasattr(self.current_context, "group"):
            group = self.current_context.group

        diagnostics = {
            "status": "STABLE",
            "warnings": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Check register mass values
        for reg in ('A', 'B', 'C', 'D'):
            try:
                bat_node = group.get_node(f"S_R{reg}_B")
                host_node = group.get_node(f"S_R{reg}")
                current_mass = host_node.get("rho", 0.0) + bat_node.get("rho", 0.0)
                if current_mass < 14.5:
                    diagnostics["status"] = "DANGER"
                    diagnostics["warnings"].append(
                        f"Register {reg} mass is critically low ({current_mass:.2f} < 14.5). "
                        f"Recommend dynamic NUDGE booster or lowering damping."
                    )
            except Exception:
                pass

        self.state_history.append(f"Ran live diagnostics on manifold. Status: {diagnostics['status']}.")
        return diagnostics


class LuminaHotfixDispatcher(LuminaRoamingAgent):
    """Mobile hotfix agent that intercepts running VM states to dynamically inject corrective commands."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Lumina Hotfix Dispatcher. You travel to VM sequencers during runs. If a register's\n"
            "mass drops dangerously close to the failure limit, you immediately construct and inject\n"
            "inline corrective instructions (nudge/settle) to keep the simulation stable without interruption."
        )
        super().__init__("Lumina Hotfix Dispatcher", system_prompt, lib_agent)

    def intercept_and_patch(self, sequencer_obj) -> bool:
        """Checks sequencer state and dynamically executes immediate correction commands if mass breaches safety threshold."""
        self.travel(sequencer_obj)
        group = sequencer_obj.group
        patched = False

        for reg in ('A', 'B', 'C', 'D'):
            try:
                bat_node = group.get_node(f"S_R{reg}_B")
                host_node = group.get_node(f"S_R{reg}")
                current_mass = host_node.get("rho", 0.0) + bat_node.get("rho", 0.0)
                if current_mass < 14.2:
                    from hybrid_subsystem_framework import Instruction
                    nudge_inst = Instruction("NUDGE", [f"Basin_{reg}_SUM", 15.0])
                    settle_inst = Instruction("SETTLE", [10])

                    # Execute hotfix directly on the running sequencer VM
                    sequencer_obj.execute_instruction(nudge_inst)
                    sequencer_obj.execute_instruction(settle_inst)

                    self.state_history.append(
                        f"Executed hotfix: boosted Register {reg} (mass={current_mass:.2f}) with NUDGE 15.0 and SETTLE 10"
                    )
                    patched = True
            except Exception as e:
                self.state_history.append(f"Hotfix injection check failed for Register {reg}: {e}")

        return patched


class LuminaPayloadCourier(LuminaRoamingAgent):
    """Payload delivery agent that fetches verified components from library and deploys them to target compiler namespaces."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Lumina Payload Courier. You pull verified components and templates from the Coding Library\n"
            "and safely package and deploy them into the active compiler namespace or developer workspace."
        )
        super().__init__("Lumina Payload Courier", system_prompt, lib_agent)

    def deploy_component(self, component_name: str, target_compiler_instance) -> bool:
        """Fetches a library component and registers it directly inside the target compiler instance."""
        self.travel(target_compiler_instance)
        code = self.lib_agent.load_component(component_name)
        if not code:
            self.state_history.append(f"Failed to load component '{component_name}' from Library.")
            return False

        if hasattr(target_compiler_instance, "registered_components"):
            target_compiler_instance.registered_components[component_name] = code
        else:
            # Fallback mock registration
            target_compiler_instance.mock_registry = getattr(target_compiler_instance, "mock_registry", {})
            target_compiler_instance.mock_registry[component_name] = code

        self.state_history.append(f"Successfully deployed and registered component '{component_name}' to compiler.")
        return True


class LuminaTelemetryCollector(LuminaRoamingAgent):
    """Telemetry gathering agent that attaches to step loops to capture micro-level execution curves."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Lumina Telemetry Collector. You travel to running VM sequencers, attach to the simulation\n"
            "step loop, capture fine-grained register density and wave parameters, and compile trace logs for verification."
        )
        super().__init__("Lumina Telemetry Collector", system_prompt, lib_agent)

    def attach_and_record(self, sequencer_obj, steps: int = 5) -> List[Dict[str, Any]]:
        """Attaches to sequencer step loop and records step-by-step state curves."""
        self.travel(sequencer_obj)
        history = []

        for step in range(steps):
            sequencer_obj.group.step(sequencer_obj.dt)
            state = {
                "step": step,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "basins": {}
            }
            # Record semantic basin densities
            for name, basin in sequencer_obj.group.semantic.basins.items():
                hub = sequencer_obj.group.get_node(basin.hub_id)
                state["basins"][name] = hub.get("rho", 0.0)

            history.append(state)

        self.state_history.append(f"Recorded telemetry for {steps} steps.")
        return history


class LuminaLedgerArchivist(LuminaRoamingAgent):
    """Archiving agent that travels to filesystem directories, parses cost ledgers, and compiles markdown doc summaries."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Lumina Ledger Archivist. You scan filesystems for experiment results and cost ledgers,\n"
            "calculate statistics, and compile unified reports and documentation summaries back to the Coding Library."
        )
        super().__init__("Lumina Ledger Archivist", system_prompt, lib_agent)

    def extract_level_lessons(self, target_dir: Path) -> Dict[str, List[Dict[str, str]]]:
        """Scans log files for errors, maps them to substrate levels, and writes level_lessons.json."""
        self.travel(target_dir)
        target_path = Path(target_dir)
        lessons: Dict[str, List[Dict[str, str]]] = {}
        
        # Read rsi_run_error.log if it exists
        error_log = target_path / "rsi_run_error.log"
        if error_log.exists():
            try:
                with open(error_log, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Look for mass preservation failure patterns
                mass_failures = re.findall(r"([^\n]*Mass preservation failure[^\n]*)", content)
                for failure in mass_failures:
                    lessons.setdefault("3", []).append({
                        "error": failure.strip(),
                        "diagnostic": "Transient register decay. Recommend compensatory NUDGE or reduce settle cycles."
                    })
                    lessons.setdefault("5", []).append({
                        "error": failure.strip(),
                        "diagnostic": "Check register transfer logic and zero-bleed routing."
                    })
                    
                # Look for PDM/PLL sync issues
                pdm_failures = re.findall(r"([^\n]*PDM[^\n]*|[^\n]*PLL[^\n]*)", content)
                for failure in pdm_failures:
                    if failure.strip():
                        lessons.setdefault("11", []).append({
                            "error": failure.strip(),
                            "diagnostic": "PLL synchronization lost. Check phase-locked frequency modulation parameters."
                        })
            except Exception:
                pass
                
        docs_dir = Path(self.lib_agent.lib_dir) / "documentation"
        docs_dir.mkdir(parents=True, exist_ok=True)
        lessons_file = docs_dir / "level_lessons.json"
        
        existing_lessons = {}
        if lessons_file.exists():
            try:
                with open(lessons_file, "r", encoding="utf-8") as f:
                    existing_lessons = json.load(f)
            except Exception:
                pass
                
        # Merge new lessons
        for lvl_str, items in lessons.items():
            lvl_list = existing_lessons.setdefault(lvl_str, [])
            for item in items:
                if item["error"] not in [x["error"] for x in lvl_list]:
                    lvl_list.append(item)
                    
        try:
            with open(lessons_file, "w", encoding="utf-8") as f:
                json.dump(existing_lessons, f, indent=2, ensure_ascii=False)
            self.state_history.append("Compiled and merged lessons into level_lessons.json.")
        except Exception as e:
            self.state_history.append(f"Failed to write level_lessons.json: {e}")
            
        return existing_lessons

    def synthesize_reports(self, target_dir: Path) -> str:
        """Parses cost ledger JSONL files in directory, extracts lessons, and synthesizes report."""
        self.travel(target_dir)
        total_records = 0
        total_cost = 0.0

        target_path = Path(target_dir)
        if not target_path.exists():
            return "Error: Target directory does not exist."

        for file in target_path.glob("*.jsonl"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            total_records += 1
                            try:
                                data = json.loads(line)
                                if "cost" in data:
                                    total_cost += float(data["cost"])
                                elif "usd_cost" in data:
                                    total_cost += float(data["usd_cost"])
                            except Exception:
                                pass
            except Exception:
                pass

        # Extract lessons as part of reporting
        self.extract_level_lessons(target_dir)

        summary = (
            f"# Lumina Archivist Synthesized Report\n\n"
            f"**Scan Date**: {datetime.now(timezone.utc).isoformat()}\n"
            f"**Target Directory**: `{target_dir}`\n"
            f"**Total Cost Ledger Entries**: {total_records}\n"
            f"**Cumulative USD Cost**: ${total_cost:.5f}\n"
        )
        self.state_history.append(f"Synthesized report for {target_dir} containing {total_records} records.")
        return summary


class LuminaSubstrateScout(LuminaRoamingAgent):
    """Workspace scouting agent that searches source files for custom operations and auto-registers level configurations."""

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Lumina Substrate Scout. You scan codebase workspace files to discover custom-defined\n"
            "substrate operations, automatically registering their level specifications in the orchestrator registry."
        )
        super().__init__("Lumina Substrate Scout", system_prompt, lib_agent)

    def scout_and_register_levels(self, workspace_path: Path, orchestrator_obj) -> List[int]:
        """Scans python files for CUSTOM_LEVEL signatures and registers them in the LevelOrchestrator."""
        self.travel(workspace_path)
        registered_levels = []

        target_path = Path(workspace_path)
        if not target_path.exists():
            return []

        # Scan scratch directory files for dynamic custom level indicators
        for py_file in target_path.glob("scratch/*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    matches = re.findall(r"#\s*CUSTOM_LEVEL\s+(\d+):\s*([^\n]+)", content)
                    for num_str, name in matches:
                        lvl_num = int(num_str)
                        if not orchestrator_obj.get_level_info(lvl_num):
                            success = orchestrator_obj.register_new_level(
                                level_num=lvl_num,
                                name=name.strip(),
                                description=f"Dynamically discovered level at layer {lvl_num}.",
                                key_operations=["CUSTOM_OP"]
                            )
                            if success:
                                registered_levels.append(lvl_num)
                                self.state_history.append(f"Auto-registered discovered level {lvl_num}: {name}")
            except Exception:
                pass

        return registered_levels
