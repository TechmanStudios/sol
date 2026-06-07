# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Coding Library Manager
=============================
Acts as a persistent repository for verified LuminaAgent classes and substrate specifications.
Allows other agents to query and retrieve specialized code and documentation templates.
"""

import sys
import os
import re
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Resolve paths
lib_dir = Path(__file__).resolve().parent
sol_root = lib_dir.parent.parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "tools" / "sol-llm"))
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))

class LuminaLibraryAgent:
    """Manages verified Lumina component code and substrate design documentation."""

    def __init__(self, library_dir: Optional[Path] = None):
        if library_dir is None:
            self.lib_dir = Path(__file__).resolve().parent
        else:
            self.lib_dir = Path(library_dir)
            
        self.components_dir = self.lib_dir / "components"
        self.doc_dir = self.lib_dir / "documentation"
        self.registry_path = self.lib_dir / "registry.json"
        
        # Ensure directories exist
        self.components_dir.mkdir(parents=True, exist_ok=True)
        self.doc_dir.mkdir(parents=True, exist_ok=True)
        
        # Load registry
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict[str, dict]:
        if not self.registry_path.exists():
            return {}
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_registry(self):
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

    def sync_from_ledger(self, ledger_path: Optional[Path] = None) -> List[str]:
        """Scan the inventor ledger and migrate successful code blocks to library components."""
        if ledger_path is None:
            # Resolve relative to SOL root
            sol_root = self.lib_dir.parent.parent.parent
            ledger_path = sol_root / "data" / "rsi" / "inventor_ledger.jsonl"
            
        if not ledger_path.exists():
            return []
            
        synced = []
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    task = entry.get("task")
                    success = entry.get("success")
                    history = entry.get("history", [])
                    
                    if not task or not success or not history:
                        continue
                        
                    # Find the successful cycle's code
                    success_code = ""
                    for cycle in history:
                        if cycle.get("status") == "SUCCESS":
                            success_code = cycle.get("code", "")
                            break
                            
                    if not success_code:
                        continue
                        
                    # Save component file
                    comp_file = self.components_dir / f"{task}.py"
                    with open(comp_file, "w", encoding="utf-8") as out_f:
                        out_f.write(success_code)
                        
                    # Update registry
                    self.registry[task] = {
                        "path": f"components/{task}.py",
                        "verification_status": "VERIFIED",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    synced.append(task)
                except (json.JSONDecodeError, OSError):
                    pass
                    
        if synced:
            self._save_registry()
        return synced

    def list_components(self) -> List[str]:
        """Return list of all registered logic components."""
        return list(self.registry.keys())

    def load_component(self, name: str) -> Optional[str]:
        """Retrieve the verified Lumina source code for a component by name."""
        info = self.registry.get(name)
        if not info:
            return None
            
        comp_path = self.lib_dir / info["path"]
        if not comp_path.exists():
            return None
            
        with open(comp_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_documentation(self, topic: str) -> Optional[str]:
        """Retrieve reference documentation text for a given topic."""
        doc_file = self.doc_dir / f"{topic}.md"
        if not doc_file.exists():
            # Try lowercase
            doc_file = self.doc_dir / f"{topic.lower()}.md"
            if not doc_file.exists():
                return None
                
        with open(doc_file, "r", encoding="utf-8") as f:
            return f.read()

    def ask_expert(self, expert_name: str, query: str, context: Optional[dict] = None) -> str:
        """Route a query to a specialized Coding Library Expert."""
        expert_name_lower = expert_name.lower().strip()
        if expert_name_lower in ["giants", "manifold"]:
            from coding_library.exciton_moa_experts import ExcitonMoaExpertTeam
            team = ExcitonMoaExpertTeam(library_dir=self.lib_dir)
            return team.ask_expert(expert_name_lower, query, context)
        elif expert_name_lower in ["vertical", "horizontal"]:
            from coding_library.level_architecture_experts import LevelArchitectureExpertTeam
            team = LevelArchitectureExpertTeam(library_dir=self.lib_dir)
            return team.ask_expert(expert_name_lower, query, context)
        elif expert_name_lower in ["discovery", "recommendation"]:
            from coding_library.discovery_experts import DiscoveryExpertTeam
            team = DiscoveryExpertTeam(library_dir=self.lib_dir)
            return team.ask_expert(expert_name_lower, query, context)
        elif expert_name_lower in ["planner", "controller"]:
            from coding_library.experiment_experts import ExperimentExpertTeam
            team = ExperimentExpertTeam(library_dir=self.lib_dir)
            return team.ask_expert(expert_name_lower, query, context)
        elif expert_name_lower in ["wave_synthesis", "compiler_optimizer", "evolve_cortex"]:
            from coding_library.advanced_experts import AdvancedExpertTeam
            team = AdvancedExpertTeam(library_dir=self.lib_dir)
            return team.ask_expert(expert_name_lower, query, context)
        elif expert_name_lower in ["phase_calibration", "acoustic_impedance"]:
            from coding_library.calibration_experts import CalibrationExpertTeam
            team = CalibrationExpertTeam(library_dir=self.lib_dir)
            return team.ask_expert(expert_name_lower, query, context)
        elif expert_name_lower in ["collision_arbitrator", "soliton_waveform"]:
            from coding_library.network_experts import NetworkExpertTeam
            team = NetworkExpertTeam(library_dir=self.lib_dir)
            return team.ask_expert(expert_name_lower, query, context)
        elif expert_name_lower in ["mass_sentinel", "circuit_proofer"]:
            from coding_library.verification_experts import VerificationExpertTeam
            team = VerificationExpertTeam(library_dir=self.lib_dir)
            return team.ask_expert(expert_name_lower, query, context)
        elif expert_name_lower in ["resonant_attention", "hcam_recall"]:
            from coding_library.cognitive_experts import CognitiveExpertTeam
            team = CognitiveExpertTeam(library_dir=self.lib_dir)
            return team.ask_expert(expert_name_lower, query, context)
        elif expert_name_lower in ["ranger", "substrate_ranger", "hotfix_dispatcher", "payload_courier", "telemetry_collector", "ledger_archivist", "substrate_scout"]:
            from coding_library.roaming_agents import (
                LuminaSubstrateRanger, LuminaHotfixDispatcher, LuminaPayloadCourier,
                LuminaTelemetryCollector, LuminaLedgerArchivist, LuminaSubstrateScout
            )
            if expert_name_lower in ["ranger", "substrate_ranger"]:
                agent = LuminaSubstrateRanger(self)
            elif expert_name_lower == "hotfix_dispatcher":
                agent = LuminaHotfixDispatcher(self)
            elif expert_name_lower == "payload_courier":
                agent = LuminaPayloadCourier(self)
            elif expert_name_lower == "telemetry_collector":
                agent = LuminaTelemetryCollector(self)
            elif expert_name_lower == "ledger_archivist":
                agent = LuminaLedgerArchivist(self)
            else:
                agent = LuminaSubstrateScout(self)
            return agent.query(query, context)
        else:
            m = re.match(r"^level_?(\d+)$", expert_name_lower)
            if expert_name_lower in ["level_agent", "level"] or m:
                from coding_library.level_agents import LevelOrchestrator
                orch = LevelOrchestrator(library_dir=self.lib_dir)
                if m:
                    level_num = int(m.group(1))
                else:
                    level_num = 1
                    if context and ("level" in context or "level_number" in context):
                        level_num = int(context.get("level") or context.get("level_number"))
                return orch.ask_level_agent(level_num, query, context)
            else:
                from coding_library.experts import LuminaExpertTeam
                team = LuminaExpertTeam(library_dir=self.lib_dir)
                return team.ask_expert(expert_name_lower, query, context)

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lumina Coding Library Manager API CLI")
    ap.add_argument("--query", choices=["list", "sync", "get", "doc", "expert"], required=True, help="Query type")
    ap.add_argument("--name", help="Component name (required for 'get')")
    ap.add_argument("--topic", help="Documentation topic (required for 'doc')")
    ap.add_argument("--expert", help="Expert name (required for 'expert')")
    ap.add_argument("--question", help="Question for the expert (required for 'expert')")
    args = ap.parse_args()
    
    manager = LuminaLibraryAgent()
    
    if args.query == "list":
        comps = manager.list_components()
        print(f"Registered Components ({len(comps)}):")
        for comp in comps:
            print(f"  - {comp}")
    elif args.query == "sync":
        synced = manager.sync_from_ledger()
        print(f"Synchronized {len(synced)} components from ledger: {', '.join(synced)}")
    elif args.query == "get":
        if not args.name:
            print("Error: --name is required for 'get' query")
            sys.exit(1)
        code = manager.load_component(args.name)
        if code:
            print(code)
        else:
            print(f"Component '{args.name}' not found.")
    elif args.query == "doc":
        if not args.topic:
            print("Error: --topic is required for 'doc' query")
            sys.exit(1)
        doc = manager.get_documentation(args.topic)
        if doc:
            print(doc)
        else:
            print(f"Documentation topic '{args.topic}' not found.")
    elif args.query == "expert":
        if not args.expert or not args.question:
            print("Error: --expert and --question are required for 'expert' query")
            sys.exit(1)
        ctx = None
        expert_clean = args.expert.lower().strip()
        m = re.match(r"^level_?(\d+)$", expert_clean)
        if m:
            ctx = {"level": int(m.group(1))}
        elif expert_clean in ["level_agent", "level"] and args.name:
            ctx = {"level": int(args.name)}
        ans = manager.ask_expert(args.expert, args.question, ctx)
        print(ans)
