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
        self.observatory_staging_path = self.lib_dir / "observatory_staged_registry.json"
        self.lessons_path = self.lib_dir / "level_lessons.json"
        
        # Ensure directories exist
        self.components_dir.mkdir(parents=True, exist_ok=True)
        self.doc_dir.mkdir(parents=True, exist_ok=True)
        
        # Load registry
        self.registry = self._load_registry()
        self.observatory_staged = self._load_observatory_staged()
        self.level_lessons = self._load_level_lessons()

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

    def _load_observatory_staged(self) -> Dict[str, dict]:
        if not self.observatory_staging_path.exists():
            return {}
        try:
            with open(self.observatory_staging_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_observatory_staged(self) -> None:
        with open(self.observatory_staging_path, "w", encoding="utf-8") as f:
            json.dump(self.observatory_staged, f, indent=2, ensure_ascii=False)

    def _load_level_lessons(self) -> List[dict]:
        if not self.lessons_path.exists():
            return []
        try:
            with open(self.lessons_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_level_lessons(self) -> None:
        with open(self.lessons_path, "w", encoding="utf-8") as f:
            json.dump(self.level_lessons, f, indent=2, ensure_ascii=False)

    def stage_observatory_candidate(
        self,
        *,
        component_name: str,
        code_source: str,
        experiment_id: str,
        sovereign_packet_id: str,
        reproducibility_hash: str,
        court_decision: str,
        target_level: int = 12,
        review_status: str = "awaiting_review",
        persist_to_disk: bool = True,
    ) -> Dict[str, str]:
        """
        Stages a candidate Lumina component under SOL Change Observatory + PromotionCourt
        governance (`Rule 1: Agents propose; courts promote`).
        Candidate components remain `AWAITING_OBSERVATORY_REVIEW` (`review_status='awaiting_review'`)
        until human reviewer sign-off in the SOL Change Observatory.
        """
        record = {
            "component_name": component_name,
            "path": f"components/staged_{component_name}.py",
            "verification_status": "AWAITING_OBSERVATORY_REVIEW",
            "review_status": review_status,
            "observatory_experiment_id": experiment_id,
            "sovereign_packet_id": sovereign_packet_id,
            "reproducibility_hash": reproducibility_hash,
            "court_decision": court_decision,
            "target_level": int(target_level),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.observatory_staged[component_name] = record
        if persist_to_disk:
            staged_file = self.components_dir / f"staged_{component_name}.py"
            with open(staged_file, "w", encoding="utf-8") as out_f:
                out_f.write(code_source)
            self._save_observatory_staged()
        return record

    def list_observatory_staged_candidates(self) -> Dict[str, dict]:
        """Return all candidate components staged with SOL Change Observatory provenance."""
        return dict(self.observatory_staged)

    def record_lesson_law(
        self,
        *,
        lesson_id: str,
        level: int,
        failure_pattern: str,
        constitutional_rule: str,
        ranger_actor: str,
        experiment_id: str,
        reproducibility_hash: str,
        persist_to_disk: bool = True,
    ) -> Dict[str, object]:
        """
        Implements Rule 7 (`Lessons become law` from LuminaRangerCorps.md §10):
        Persists a verified field failure lesson into `level_lessons.json` so deliberative
        councils and Continuum agents load it before future proposals.
        """
        entry = {
            "lesson_id": lesson_id,
            "level": int(level),
            "failure_pattern": failure_pattern,
            "constitutional_rule": constitutional_rule,
            "ranger_actor": ranger_actor,
            "observatory_experiment_id": experiment_id,
            "reproducibility_hash": reproducibility_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        existing_ids = {item.get("lesson_id") for item in self.level_lessons}
        if lesson_id not in existing_ids:
            self.level_lessons.append(entry)
        else:
            self.level_lessons = [
                entry if item.get("lesson_id") == lesson_id else item
                for item in self.level_lessons
            ]
        if persist_to_disk:
            self._save_level_lessons()
        return entry

    def load_level_lessons(self, level: Optional[int] = None) -> List[dict]:
        """Load constitutional lessons from `level_lessons.json`, optionally filtered by level."""
        if level is None:
            return list(self.level_lessons)
        return [item for item in self.level_lessons if int(item.get("level", -1)) == int(level)]

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
        elif expert_name_lower in ["sovereign", "court", "ranger_team", "agent_team"]:
            from coding_library.sovereign_domain import SovereignDomain
            domain = SovereignDomain(library_dir=self.lib_dir)
            return domain.route(expert_name_lower, query, context)
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
