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

def load_config() -> dict:
    """Public helper returning the parsed models.json dictionary alongside normalized MODELS."""
    cfg = _load_json_config()
    if "slots" in cfg and "models" not in cfg:
        cfg["models"] = cfg["slots"]
    return cfg

def _save_json_config(cfg: dict) -> None:
    """Write config back to models.json."""
    with open(_MODELS_JSON, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")

_CFG = _load_json_config()

# ---------------------------------------------------------------------------
# GitHub Models API endpoint
# ---------------------------------------------------------------------------
_providers = _CFG.get("providers", {})
_github_provider = _providers.get("github", {})
GITHUB_MODELS_ENDPOINT = _github_provider.get(
    "endpoint", "https://models.inference.ai.azure.com"
)

# All providers (for multi-provider support in client.py)
PROVIDERS = _providers or {
    "github": {
        "name": "GitHub Models",
        "endpoint": "https://models.inference.ai.azure.com",
        "env_var": "GITHUB_TOKEN",
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
            "provider": slot_data.get("provider", "google"),
            "sdk": slot_data.get("sdk", _providers.get(slot_data.get("provider", "google"), {}).get("sdk", "google-genai")),
            "context_window": slot_data.get("context_window", 1_048_576),
            "max_output_tokens": slot_data.get("max_output_tokens", 32_768),
            "thinking_level": slot_data.get("thinking_level", "high"),
            "cost_per_1k_input": slot_data.get("cost_per_1k_input", 0.002),
            "cost_per_1k_output": slot_data.get("cost_per_1k_output", 0.012),
            "is_reasoning": slot_data.get("is_reasoning", True),
        }
else:
    # Hardcoded fallback if models.json is missing
    MODELS = {
        "primary": {
            "id": "gemini-4-argon",
            "name": "Gemini 4 Argon",
            "role": "primary",
            "provider": "google",
            "sdk": "google-genai",
            "context_window": 1_048_576,
            "max_output_tokens": 32_768,
            "thinking_level": "high",
            "cost_per_1k_input": 0.002,
            "cost_per_1k_output": 0.012,
            "is_reasoning": True,
        },
        "fallback": {
            "id": "gemini-3.8-flash",
            "name": "Gemini 3.8 Flash",
            "role": "fallback",
            "provider": "google",
            "sdk": "google-genai",
            "context_window": 1_048_576,
            "max_output_tokens": 32_768,
            "thinking_level": "medium",
            "cost_per_1k_input": 0.0005,
            "cost_per_1k_output": 0.003,
            "is_reasoning": True,
        },
        "reasoning": {
            "id": "gemini-4-argon",
            "name": "Gemini 4 Argon (Reflective Reasoning)",
            "role": "reasoning",
            "provider": "google",
            "sdk": "google-genai",
            "context_window": 1_048_576,
            "max_output_tokens": 32_768,
            "thinking_level": "high",
            "cost_per_1k_input": 0.002,
            "cost_per_1k_output": 0.012,
            "is_reasoning": True,
        },
    }

# ---------------------------------------------------------------------------
# Budget & safety defaults
# ---------------------------------------------------------------------------
DEFAULT_BUDGET = _CFG.get("budget", {
    "max_tokens_per_call": 32768,
    "max_calls_per_cycle": 20,
    "max_cost_per_cycle_usd": 2.00,
    "max_cost_per_day_usd": 10.00,
    "max_calls_per_minute": 10,
    "max_calls_per_day": 100,
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
