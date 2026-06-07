# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Substrate Level Agent Orchestrator
=========================================
Dynamic agent system that instantiates a dedicated LuminaAgent expert for each
physical/computational level of the SOL substrate, and supports programmatic
level invention and registration.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Resolve paths
lib_dir = Path(__file__).resolve().parent
sol_root = lib_dir.parent.parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "tools" / "sol-llm"))
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))

from coding_library.experts import LuminaExpert

class LuminaLevelAgent(LuminaExpert):
    """Dynamically configured expert agent for a specific SOL substrate level."""

    def __init__(self, level_num: int, name: str, description: str, key_operations: List[str], lib_agent=None):
        self.level_number = level_num
        self.level_name = name
        self.level_description = description
        self.key_operations = key_operations
        
        system_prompt = (
            f"You are the Lumina Substrate Level {level_num} Agent, specializing in the '{name}' layer.\n"
            f"Description: {description}\n"
            f"Key Operations at this layer: {', '.join(key_operations)}.\n"
            f"You guide developers, compiler agents, and inventors on fixing violations, optimizing operations, "
            f"and writing Lumina program flows targeting Level {level_num} features."
        )
        super().__init__(f"Lumina Substrate Level {level_num} Agent ({name})", system_prompt, lib_agent)

    def _get_context(self) -> str:
        doc = self.lib_agent.get_documentation("substrate_reference")
        hbus = self.lib_agent.get_documentation("holographic_bus_reference")
        
        ctx = []
        if doc:
            ctx.append("### Substrate Reference:")
            ctx.append(doc)
        if hbus and self.level_number >= 8:
            ctx.append("### Holographic Bus Reference:")
            ctx.append(hbus)
            
        return "\n\n".join(ctx) if ctx else "No reference documentation found."


class LevelOrchestrator:
    """Manages the lifecycle, registry, and query routing for all Substrate Level Agents."""

    def __init__(self, library_dir: Optional[Path] = None):
        if library_dir is None:
            self.lib_dir = Path(__file__).resolve().parent
        else:
            self.lib_dir = Path(library_dir)
            
        self.registry_path = self.lib_dir / "level_registry.json"
        
        # Load registry
        self.levels_db = self._load_registry()
        
        # Cache of initialized agents
        self.agents_cache: Dict[int, LuminaLevelAgent] = {}

    def _load_registry(self) -> List[Dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _save_registry(self):
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self.levels_db, f, indent=2, ensure_ascii=False)

    def register_new_level(self, level_num: int, name: str, description: str, key_operations: List[str]) -> bool:
        """Register a new substrate level and dynamically assign a Lumina level agent to it."""
        # Check if already registered
        for level in self.levels_db:
            if level.get("level_number") == level_num:
                # Update existing
                level["name"] = name
                level["description"] = description
                level["key_operations"] = key_operations
                level["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_registry()
                
                # Invalidate cache entry
                if level_num in self.agents_cache:
                    del self.agents_cache[level_num]
                return True
                
        # Append new
        new_entry = {
            "level_number": level_num,
            "name": name,
            "description": description,
            "key_operations": key_operations,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.levels_db.append(new_entry)
        # Sort levels db by level number
        self.levels_db.sort(key=lambda x: x.get("level_number", 999))
        self._save_registry()
        return True

    def get_level_info(self, level_num: int) -> Optional[Dict[str, Any]]:
        for level in self.levels_db:
            if level.get("level_number") == level_num:
                return level
        return None

    def get_level_agent(self, level_num: int, lib_agent=None) -> Optional[LuminaLevelAgent]:
        if level_num in self.agents_cache:
            return self.agents_cache[level_num]
            
        info = self.get_level_info(level_num)
        if not info:
            return None
            
        agent = LuminaLevelAgent(
            level_num=info["level_number"],
            name=info["name"],
            description=info["description"],
            key_operations=info.get("key_operations", []),
            lib_agent=lib_agent
        )
        self.agents_cache[level_num] = agent
        return agent

    def ask_level_agent(self, level_num: int, query: str, context_details: Optional[dict] = None) -> str:
        """Query a specific level agent by level number."""
        # Import dynamically to avoid circular dependencies
        from coding_library.library_agent import LuminaLibraryAgent
        lib_agent = LuminaLibraryAgent(library_dir=self.lib_dir)
        
        agent = self.get_level_agent(level_num, lib_agent=lib_agent)
        if not agent:
            return f"Error: Substrate Level {level_num} is not registered in the level database."
            
        return agent.query(query, context_details)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Level Agents and Orchestrator API CLI")
    ap.add_argument("--query", choices=["list", "ask", "register"], required=True, help="Query type")
    ap.add_argument("--level", type=int, help="Level number")
    ap.add_argument("--name", help="Level name (required for 'register')")
    ap.add_argument("--description", help="Level description (required for 'register')")
    ap.add_argument("--operations", help="Comma-separated key operations (required for 'register')")
    ap.add_argument("--question", help="Question to ask (required for 'ask')")
    args = ap.parse_args()
    
    orch = LevelOrchestrator()
    
    if args.query == "list":
        print("Registered Substrate Levels:")
        for lvl in orch.levels_db:
            print(f"  Level {lvl['level_number']}: {lvl['name']}")
            print(f"    - Description: {lvl['description']}")
            print(f"    - Operations : {', '.join(lvl.get('key_operations', []))}")
            print()
    elif args.query == "register":
        if args.level is None or not args.name or not args.description or not args.operations:
            print("Error: --level, --name, --description, and --operations are required for register.")
            sys.exit(1)
        ops = [op.strip() for op in args.operations.split(",") if op.strip()]
        success = orch.register_new_level(args.level, args.name, args.description, ops)
        if success:
            print(f"Successfully registered/updated Substrate Level {args.level}: {args.name}")
        else:
            print("Failed to register level.")
    elif args.query == "ask":
        if args.level is None or not args.question:
            print("Error: --level and --question are required for ask.")
            sys.exit(1)
        ans = orch.ask_level_agent(args.level, args.question)
        print(ans)
