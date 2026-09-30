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
