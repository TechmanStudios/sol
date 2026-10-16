# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Sovereign Domain Registry Manager
=================================
Loads, parses, and provides access to agent, ranger, team, and promotion gate registries.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

class SovereignDomain:
    """
    Registry management class for the SOL Sovereign Domain.
    Reads and queries domain metadata, agents, rangers, and gating metrics.
    """
    def __init__(self, library_dir: Optional[Path] = None):
        if library_dir is None:
            self.lib_dir = Path(__file__).resolve().parent.parent
        else:
            self.lib_dir = Path(library_dir)
            
        self.domain_dir = self.lib_dir / "sovereign_domain"
        
        # Load registry data
        self.agent_registry = self._load_json("agent_registry.json")
        self.ranger_registry = self._load_json("ranger_registry.json")
        self.team_registry = self._load_json("team_registry.json")
        self.promotion_gates = self._load_json("promotion_gates.json")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = self.domain_dir / filename
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """Query metadata for a specific agent or council."""
        return self.agent_registry.get(agent_name, {})

    def get_ranger_info(self, ranger_name: str) -> Dict[str, Any]:
        """Query metadata for a specific ranger class."""
        return self.ranger_registry.get(ranger_name, {})

    def get_team_info(self, team_name: str) -> Dict[str, Any]:
        """Query metadata for a combined agent/ranger operational team."""
        return self.team_registry.get(team_name, {})

    def get_gate_info(self, gate_name: str) -> Dict[str, Any]:
        """Query requirements for a specific architecture promotion gate."""
        return self.promotion_gates.get(gate_name, {})

    def list_rangers(self) -> list[str]:
        """Return all registered mobile Ranger IDs in the Sovereign Domain."""
        return list(self.ranger_registry.keys())

    def list_agent_councils(self) -> list[str]:
        """Return all registered deliberative Agent Councils and Guilds."""
        return list(self.agent_registry.keys())

    def list_teams(self) -> list[str]:
        """Return all registered combined Agent/Ranger operational teams."""
        return list(self.team_registry.keys())

    def list_promotion_gates(self) -> list[str]:
        """Return all registered Promotion Court gate names."""
        return list(self.promotion_gates.keys())

    def route(
        self,
        expert_name: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Route a Sovereign Domain query to the appropriate Council, Ranger Team, or Promotion Court.
        Implements the router contract from LuminaRangerCorps.md §11.
        """
        ctx = context or {}
        target = expert_name.lower().strip()
        level = ctx.get("level", 12)
        if target == "court":
            gate_key = f"level_{level}_32bit_gate" if level == 12 else f"level_{level}_gate"
            gate_info = self.promotion_gates.get(gate_key) or next(
                (v for k, v in self.promotion_gates.items() if f"level_{level}" in k),
                {},
            )
            return json.dumps(
                {
                    "domain": "sol_sovereign",
                    "branch": "promotion_court",
                    "level": level,
                    "query": query,
                    "gate_requirements": gate_info,
                    "total_registered_gates": len(self.promotion_gates),
                },
                sort_keys=True,
            )
        if target == "ranger_team":
            team_key = next(
                (k for k in self.team_registry if f"level_{level}" in k),
                next(iter(self.team_registry.keys()), "level_12_32bit_fabric_team"),
            )
            return json.dumps(
                {
                    "domain": "sol_sovereign",
                    "branch": "ranger_corps",
                    "team": team_key,
                    "team_manifest": self.team_registry.get(team_key, {}),
                    "registered_rangers": self.list_rangers(),
                    "query": query,
                },
                sort_keys=True,
            )
        if target == "agent_team":
            return json.dumps(
                {
                    "domain": "sol_sovereign",
                    "branch": "parliament_of_resonators",
                    "councils": self.agent_registry,
                    "query": query,
                },
                sort_keys=True,
            )
        return json.dumps(
            {
                "domain": "sol_sovereign",
                "branch": "sovereign_overview",
                "councils": self.list_agent_councils(),
                "rangers": self.list_rangers(),
                "teams": self.list_teams(),
                "promotion_gates_count": len(self.promotion_gates),
                "query": query,
            },
            sort_keys=True,
        )

