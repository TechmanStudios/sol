#!/usr/bin/env python3
"""
SOL LLM — Model Update Helper
================================
CLI tool to manage LLM model configuration without editing Python code.

Usage:
    python tools/sol-llm/update_models.py show
    python tools/sol-llm/update_models.py set primary gpt-5.4-mini
    python tools/sol-llm/update_models.py set lightweight gpt-5.4-nano --provider openai
    python tools/sol-llm/update_models.py set reasoning gpt-5.4 --provider openai
    python tools/sol-llm/update_models.py scan
    python tools/sol-llm/update_models.py test
    python tools/sol-llm/update_models.py catalog
    python tools/sol-llm/update_models.py history
    python tools/sol-llm/update_models.py rollback primary
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DIR = Path(__file__).resolve().parent
_MODELS_JSON = _DIR / "models.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load() -> dict:
    if _MODELS_JSON.exists():
        with open(_MODELS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"ERROR: {_MODELS_JSON} not found. Run from the sol project root.")
    sys.exit(1)

def _save(cfg: dict) -> None:
    cfg["_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(_MODELS_JSON, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  Saved → {_MODELS_JSON}")


def _get_api_key(provider_cfg: dict) -> str | None:
    """Resolve API key for a provider from env vars."""
    env_var = provider_cfg.get("env_var", "GITHUB_TOKEN")
    key = os.environ.get(env_var)
    if not key and env_var == "GITHUB_TOKEN":
        key = os.environ.get("GITHUB_MODELS_TOKEN") or os.environ.get("GH_TOKEN")
    return key


def _make_client(provider_cfg: dict, api_key: str):
    """Create an OpenAI-compatible client for the given provider."""
    from openai import OpenAI
    return OpenAI(
        base_url=provider_cfg["endpoint"],
        api_key=api_key,
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_show(cfg: dict, _args) -> None:
    """Display current model configuration."""
    slots = cfg.get("slots", {})
    providers = cfg.get("providers", {})

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║              SOL LLM — Current Configuration               ║")
    print("╠══════════════════════════════════════════════════════════════╣")

    for slot_name, slot in slots.items():
        provider_key = slot.get("provider", "github")
        provider = providers.get(provider_key, {})
        env_var = provider.get("env_var", "?")
        has_key = "✓" if _get_api_key(provider) else "✗"

        print(f"║  {slot_name.upper():10s}  │  {slot['id']:<28s}       ║")
        print(f"║             │  provider: {provider_key:<10s}  key({env_var}): {has_key}  ║")
        reasoning = "yes" if slot.get("is_reasoning") else "no"
        ctx = f"{slot.get('context_window', 0):,}"
        print(f"║             │  reasoning: {reasoning:<5s}  context: {ctx:<12s}  ║")
        print("║─────────────┼────────────────────────────────────────────║")

    budget = cfg.get("budget", {})
    print(f"║  BUDGET     │  ${budget.get('max_cost_per_day_usd', 0):.2f}/day  "
          f"${budget.get('max_cost_per_cycle_usd', 0):.2f}/cycle  "
          f"{budget.get('max_calls_per_cycle', 0)} calls    ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")


def cmd_set(cfg: dict, args) -> None:
    """Swap a model slot to a new model ID."""
    slot = args.slot
    model_id = args.model_id
    provider = args.provider or cfg["slots"].get(slot, {}).get("provider", "github")
    reasoning = args.reasoning

    if slot not in cfg.get("slots", {}):
        valid = list(cfg.get("slots", {}).keys())
        print(f"ERROR: Unknown slot '{slot}'. Valid slots: {valid}")
        sys.exit(1)

    old_id = cfg["slots"][slot]["id"]

    # Auto-detect reasoning for known model families
    if reasoning is None:
        reasoning_prefixes = (
            "o1", "o3", "o4", "DeepSeek-R1",
            "gpt-5-mini", "gpt-5-nano", "gpt-5 ",
        )
        reasoning_exact = {"gpt-5", "gpt-5-mini", "gpt-5-nano"}
        reasoning = model_id in reasoning_exact or any(model_id.startswith(p) for p in reasoning_prefixes)

    cfg["slots"][slot]["id"] = model_id
    cfg["slots"][slot]["name"] = args.name or model_id
    cfg["slots"][slot]["provider"] = provider
    cfg["slots"][slot]["is_reasoning"] = reasoning

    # Optionally update costs
    if args.cost_in is not None:
        cfg["slots"][slot]["cost_per_1k_input"] = args.cost_in
    if args.cost_out is not None:
        cfg["slots"][slot]["cost_per_1k_output"] = args.cost_out
    if args.context is not None:
        cfg["slots"][slot]["context_window"] = args.context

    # Record in history
    history = cfg.setdefault("history", [])
    history.append({
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "slot": slot,
        "from": old_id,
        "to": model_id,
        "reason": args.reason or "manual swap",
    })

    _save(cfg)
    print(f"\n  ✓ {slot.upper()}: {old_id} → {model_id} (provider: {provider}, reasoning: {reasoning})")
    print(f"    To test: python tools/sol-llm/update_models.py test\n")


def cmd_scan(cfg: dict, _args) -> None:
    """Scan GitHub Models API for all available models."""
    providers = cfg.get("providers", {})
    catalog = cfg.get("model_catalog", {})

    print("\nScanning providers for available models...\n")

    for provider_key, provider_cfg in providers.items():
        if provider_cfg.get("sdk") != "openai":
            print(f"  [{provider_key}] Skipped (non-OpenAI SDK — scan not implemented)")
            continue

        api_key = _get_api_key(provider_cfg)
        if not api_key:
            print(f"  [{provider_key}] Skipped (no API key in ${provider_cfg.get('env_var', '?')})")
            continue

        print(f"  [{provider_key}] Scanning {provider_cfg.get('name', provider_key)}...")

        # Build candidate list: catalog + known models
        known = set(catalog.get(provider_key, []))
        # Add some new candidates to always check
        new_candidates = {
            "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano",
            "gpt-5.3", "gpt-5.3-codex",
            "gpt-5", "gpt-5-chat", "gpt-5-mini", "gpt-5-nano",
            "gpt-5.1", "gpt-5.1-mini", "gpt-5.1-nano",
            "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
            "gpt-4o", "gpt-4o-mini",
            "o1", "o1-mini", "o1-preview", "o3", "o3-mini", "o3-pro", "o4-mini",
            "claude-4", "claude-4.5", "claude-4.6",
            "claude-opus-4-20250514", "claude-sonnet-4-20250514",
            "gemini-2.5-pro", "gemini-3.0-pro", "gemini-3-pro",
            "Grok-3", "Grok-3-Mini", "Grok-4",
            "DeepSeek-R1", "DeepSeek-R1-0528", "DeepSeek-V3", "MAI-DS-R1",
            "Meta-Llama-3.1-405B-Instruct", "Llama-3.3-70B-Instruct",
            "Llama-4-Scout-17B-16E-Instruct", "Llama-4-Maverick-17B-128E-Instruct-FP8",
            "Mistral-large-2411", "Mistral-small-2503", "Codestral-2501",
            "Phi-4", "Phi-4-mini", "Phi-5",
        }
        candidates = sorted(known | new_candidates)

        client = _make_client(provider_cfg, api_key)
        available = []
        unavailable = []

        for model_id in candidates:
            try:
                result = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                )
                available.append(model_id)
                sys.stdout.write(f"    ✓ {model_id}\n")
            except Exception as e:
                err = str(e)
                if "rate limit" in err.lower() or "429" in err:
                    available.append(model_id)
                    sys.stdout.write(f"    ✓ {model_id} (rate-limited but valid)\n")
                elif "unknown_model" in err or "404" in err or "not found" in err.lower():
                    unavailable.append(model_id)
                elif "temperature" in err.lower() or "max_tokens" in err.lower():
                    # Reasoning model that needs special params
                    try:
                        result = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": "ping"}],
                            max_completion_tokens=1,
                        )
                        available.append(model_id)
                        sys.stdout.write(f"    ✓ {model_id} (reasoning)\n")
                    except Exception:
                        available.append(model_id)
                        sys.stdout.write(f"    ✓ {model_id} (special params)\n")
                else:
                    unavailable.append(model_id)
            sys.stdout.flush()

        # Update catalog
        catalog[provider_key] = sorted(available)
        cfg["model_catalog"] = catalog
        _save(cfg)

        print(f"\n    Available: {len(available)}  |  Not found: {len(unavailable)}")
        if unavailable:
            print(f"    Not found: {', '.join(unavailable[:10])}")
        print()


def cmd_test(cfg: dict, _args) -> None:
    """Test connectivity with all configured model slots."""
    slots = cfg.get("slots", {})
    providers = cfg.get("providers", {})

    print("\nTesting model connectivity...\n")

    all_ok = True
    for slot_name, slot in slots.items():
        provider_key = slot.get("provider", "github")
        provider_cfg = providers.get(provider_key, {})
        model_id = slot["id"]
        is_reasoning = slot.get("is_reasoning", False)

        api_key = _get_api_key(provider_cfg)
        if not api_key:
            print(f"  ✗ {slot_name.upper():10s} ({model_id}) — no API key for {provider_key}")
            all_ok = False
            continue

        try:
            client = _make_client(provider_cfg, api_key)
            t0 = time.time()

            kwargs = {
                "model": model_id,
                "messages": [{"role": "user", "content": "What is 2+2? Reply with just the number."}],
            }
            if is_reasoning:
                kwargs["max_completion_tokens"] = 32
            else:
                kwargs["max_tokens"] = 32
                kwargs["temperature"] = 0.0

            result = client.chat.completions.create(**kwargs)
            elapsed = time.time() - t0
            content = (result.choices[0].message.content or "").strip()[:50]
            tokens = getattr(result.usage, "total_tokens", 0)

            print(f"  ✓ {slot_name.upper():10s} ({model_id}) — {elapsed:.1f}s, "
                  f"{tokens} tokens, response: \"{content}\"")

        except Exception as e:
            print(f"  ✗ {slot_name.upper():10s} ({model_id}) — {type(e).__name__}: {e}")
            all_ok = False

    if all_ok:
        print("\n  All models operational.\n")
    else:
        print("\n  Some models failed. Run 'scan' to check available models.\n")


def cmd_catalog(cfg: dict, _args) -> None:
    """Show known available models from last scan."""
    catalog = cfg.get("model_catalog", {})
    if not catalog:
        print("\nNo catalog data. Run: python tools/sol-llm/update_models.py scan\n")
        return

    print("\n╔═══ Known Available Models ═══╗")
    for provider, models in catalog.items():
        print(f"║  {provider}:")
        for m in models:
            print(f"║    • {m}")
    print("╚══════════════════════════════╝\n")


def cmd_history(cfg: dict, _args) -> None:
    """Show model change history."""
    history = cfg.get("history", [])
    if not history:
        print("\nNo history recorded.\n")
        return

    print("\n╔═══ Model Change History ═══╗")
    for entry in history[-20:]:  # Last 20 entries
        print(f"║  {entry['date']}  {entry['slot'].upper():10s}  "
              f"{entry['from']} → {entry['to']}")
        if entry.get("reason"):
            print(f"║             reason: {entry['reason']}")
    print("╚════════════════════════════╝\n")


def cmd_rollback(cfg: dict, args) -> None:
    """Rollback a slot to its previous model."""
    slot = args.slot
    history = cfg.get("history", [])

    # Find last change for this slot
    slot_changes = [h for h in history if h["slot"] == slot]
    if not slot_changes:
        print(f"\nNo history for slot '{slot}'. Nothing to roll back.\n")
        return

    last_change = slot_changes[-1]
    prev_model = last_change["from"]
    current_model = cfg["slots"][slot]["id"]

    if current_model != last_change["to"]:
        print(f"  Warning: current model ({current_model}) doesn't match "
              f"last recorded change ({last_change['to']})")

    cfg["slots"][slot]["id"] = prev_model
    cfg["slots"][slot]["name"] = prev_model

    history.append({
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "slot": slot,
        "from": current_model,
        "to": prev_model,
        "reason": "rollback",
    })

    _save(cfg)
    print(f"\n  ✓ Rolled back {slot.upper()}: {current_model} → {prev_model}\n")


def cmd_add_provider(cfg: dict, args) -> None:
    """Add or update a provider."""
    providers = cfg.setdefault("providers", {})
    providers[args.key] = {
        "name": args.name or args.key,
        "endpoint": args.endpoint,
        "env_var": args.env_var,
        "sdk": args.sdk or "openai",
    }
    _save(cfg)
    print(f"\n  ✓ Provider '{args.key}' added/updated.")
    print(f"    Set ${args.env_var} with your API key.\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="update_models",
        description="SOL LLM — Model Update Helper",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # show
    sub.add_parser("show", help="Display current model configuration")

    # set
    p_set = sub.add_parser("set", help="Swap a model slot")
    p_set.add_argument("slot", choices=["primary", "fallback", "reasoning", "lightweight"],
                       help="Slot to update")
    p_set.add_argument("model_id", help="New model ID (e.g. gpt-5.4-mini)")
    p_set.add_argument("--provider", help="Provider key (default: keep current)")
    p_set.add_argument("--name", help="Human-readable name")
    p_set.add_argument("--reasoning", type=bool, default=None,
                       help="Is this a reasoning model? (auto-detected if omitted)")
    p_set.add_argument("--cost-in", type=float, default=None,
                       help="Cost per 1K input tokens")
    p_set.add_argument("--cost-out", type=float, default=None,
                       help="Cost per 1K output tokens")
    p_set.add_argument("--context", type=int, default=None,
                       help="Context window size")
    p_set.add_argument("--reason", help="Reason for the change (logged to history)")

    # scan
    sub.add_parser("scan", help="Scan API for available models")

    # test
    sub.add_parser("test", help="Test connectivity with current models")

    # catalog
    sub.add_parser("catalog", help="Show known models from last scan")

    # history
    sub.add_parser("history", help="Show model change history")

    # rollback
    p_roll = sub.add_parser("rollback", help="Rollback a slot to previous model")
    p_roll.add_argument("slot", choices=["primary", "fallback", "reasoning", "lightweight"])

    # add-provider
    p_prov = sub.add_parser("add-provider", help="Add or update a provider")
    p_prov.add_argument("key", help="Provider key (e.g. anthropic, google)")
    p_prov.add_argument("--endpoint", required=True, help="API endpoint URL")
    p_prov.add_argument("--env-var", required=True, help="Env var for API key")
    p_prov.add_argument("--name", help="Human-readable provider name")
    p_prov.add_argument("--sdk", default="openai",
                       help="SDK type: openai (default) | anthropic | google")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    cfg = _load()

    dispatch = {
        "show": cmd_show,
        "set": cmd_set,
        "scan": cmd_scan,
        "test": cmd_test,
        "catalog": cmd_catalog,
        "history": cmd_history,
        "rollback": cmd_rollback,
        "add-provider": cmd_add_provider,
    }

    dispatch[args.command](cfg, args)


if __name__ == "__main__":
    main()
