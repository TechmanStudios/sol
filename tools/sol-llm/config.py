"""
SOL LLM — Model Configuration
================================
Loads model slots, budgets, and temperatures from models.json.
Falls back to hardcoded defaults if the JSON file is missing.

To change models, edit models.json or run:
    python tools/sol-llm/update_models.py set primary <model-id>
"""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Load external config (models.json) with hardcoded fallback
# ---------------------------------------------------------------------------
_CONFIG_DIR = Path(__file__).resolve().parent
_MODELS_JSON = _CONFIG_DIR / "models.json"

def _load_json_config() -> dict:
    """Load models.json if it exists, otherwise return empty dict."""
    if _MODELS_JSON.exists():
        with open(_MODELS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_json_config(cfg: dict) -> None:
    """Write config back to models.json."""
    with open(_MODELS_JSON, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")

_CFG = _load_json_config()

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
_providers = _CFG.get("providers", {})

# All providers (for multi-provider support in client.py)
PROVIDERS = _providers or {
    "modal_glm5": {
        "name": "Modal GLM-5",
        "endpoint": "https://api.us-west-2.modal.direct/v1",
        "env_var": "MODAL_API_KEY",
        "sdk": "openai",
    }
}

# ---------------------------------------------------------------------------
# Model registry — loaded from models.json slots
# ---------------------------------------------------------------------------
_json_slots = _CFG.get("slots", {})

if _json_slots:
    MODELS = {}
    for slot_name, slot_data in _json_slots.items():
        MODELS[slot_name] = {
            "id": slot_data["id"],
            "name": slot_data.get("name", slot_data["id"]),
            "role": slot_name,
            "provider": slot_data.get("provider", "modal_glm5"),
            "context_window": slot_data.get("context_window", 128_000),
            "cost_per_1k_input": slot_data.get("cost_per_1k_input", 0.001),
            "cost_per_1k_output": slot_data.get("cost_per_1k_output", 0.003),
            "is_reasoning": slot_data.get("is_reasoning", False),
        }
else:
    # Hardcoded fallback if models.json is missing
    MODELS = {
        "primary": {
            "id": "zai-org/GLM-5-FP8",
            "name": "GLM-5 FP8",
            "role": "primary",
            "provider": "modal_glm5",
            "context_window": 128_000,
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "is_reasoning": False,
        },
        "fallback": {
            "id": "zai-org/GLM-5-FP8",
            "name": "GLM-5 FP8",
            "role": "fallback",
            "provider": "modal_glm5",
            "context_window": 128_000,
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "is_reasoning": False,
        },
        "reasoning": {
            "id": "zai-org/GLM-5-FP8",
            "name": "GLM-5 FP8",
            "role": "reasoning",
            "provider": "modal_glm5",
            "context_window": 128_000,
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "is_reasoning": False,
        },
    }

# ---------------------------------------------------------------------------
# Budget & safety defaults
# ---------------------------------------------------------------------------
DEFAULT_BUDGET = _CFG.get("budget", {
    "max_tokens_per_call": 4096,
    "max_calls_per_cycle": 20,
    "max_cost_per_cycle_usd": 2.00,
    "max_cost_per_day_usd": 10.00,
    "max_retries": 2,
    "retry_delay_sec": 5.0,
    "retry_jitter_sec": 1.0,
    "timeout_sec": 75,
    "request_timeout_sec": 75,
    "lock_timeout_sec": 30,
})

# ---------------------------------------------------------------------------
# Temperature defaults per task type
# ---------------------------------------------------------------------------
TASK_TEMPERATURES = _CFG.get("temperatures", {
    "hypothesis": 0.7,
    "interpretation": 0.3,
    "claim_draft": 0.2,
    "consolidation": 0.4,
    "question_gen": 0.6,
})
