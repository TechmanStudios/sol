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
# Providers
# ---------------------------------------------------------------------------
_providers = _CFG.get("providers", {})

PROVIDERS = _providers or {
    "github": {
        "name": "GitHub Models",
        "endpoint": "https://models.inference.ai.azure.com",
        "env_var": "GITHUB_TOKEN",
        "sdk": "openai",
    },
    "openai": {
        "name": "OpenAI (Direct)",
        "endpoint": "https://api.openai.com/v1",
        "env_var": "OPENAI_API_KEY",
        "sdk": "openai",
    },
}

# GitHub Models API endpoint (kept for backward compatibility)
_github_provider = PROVIDERS.get("github", {})
GITHUB_MODELS_ENDPOINT = _github_provider.get(
    "endpoint", "https://models.inference.ai.azure.com"
)

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
            "provider": slot_data.get("provider", "github"),
            "github_fallback_id": slot_data.get("github_fallback_id", ""),
            "context_window": slot_data.get("context_window", 128_000),
            "cost_per_1k_input": slot_data.get("cost_per_1k_input", 0.001),
            "cost_per_1k_output": slot_data.get("cost_per_1k_output", 0.003),
            "is_reasoning": slot_data.get("is_reasoning", False),
        }
else:
    # Hardcoded fallback if models.json is missing
    MODELS = {
        "primary": {
            "id": "gpt-5.4-mini",
            "name": "GPT-5.4 Mini",
            "role": "primary",
            "provider": "openai",
            "github_fallback_id": "Meta-Llama-3.1-405B-Instruct",
            "context_window": 128_000,
            "cost_per_1k_input": 0.0005,
            "cost_per_1k_output": 0.0015,
            "is_reasoning": False,
        },
        "lightweight": {
            "id": "gpt-5.4-nano",
            "name": "GPT-5.4 Nano",
            "role": "lightweight",
            "provider": "openai",
            "github_fallback_id": "gpt-5-nano",
            "context_window": 128_000,
            "cost_per_1k_input": 0.0001,
            "cost_per_1k_output": 0.0003,
            "is_reasoning": False,
        },
        "reasoning": {
            "id": "gpt-5.4",
            "name": "GPT-5.4",
            "role": "reasoning",
            "provider": "openai",
            "github_fallback_id": "DeepSeek-R1-0528",
            "context_window": 128_000,
            "cost_per_1k_input": 0.005,
            "cost_per_1k_output": 0.015,
            "is_reasoning": False,
        },
        "fallback": {
            "id": "gpt-5.4-nano",
            "name": "GPT-5.4 Nano (fallback)",
            "role": "fallback",
            "provider": "openai",
            "github_fallback_id": "Mistral-large-2411",
            "context_window": 128_000,
            "cost_per_1k_input": 0.0001,
            "cost_per_1k_output": 0.0003,
            "is_reasoning": False,
        },
    }

# ---------------------------------------------------------------------------
# Task → slot routing
# Maps task names to the model slot best suited for that work level.
# lightweight = nano (cheap, fast); primary = mini; reasoning = full model.
# ---------------------------------------------------------------------------
_json_routing = _CFG.get("task_routing", {})

TASK_ROUTING: dict[str, str] = {
    "hypothesis":    "reasoning",
    "reflection":    "lightweight",
    "question_gen":  "lightweight",
    "claim_draft":   "primary",
    "interpretation":"primary",
    "synthesis":     "primary",
    "consolidation": "primary",
    "general":       "primary",
    **{k: v for k, v in _json_routing.items() if not k.startswith("_")},
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
    "timeout_sec": 120,
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
