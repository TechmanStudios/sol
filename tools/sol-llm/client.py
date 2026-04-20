"""
SOL LLM — Client
==================
Unified LLM client for the SOL RSI pipeline.

Supports multiple providers with task-based model routing:
  - Lightweight (nano): reflection, question_gen  → cheapest, fastest
  - Primary    (mini):  synthesis, consolidation  → balanced cost/quality
  - Reasoning  (full):  hypothesis, deep analysis → highest quality

Provider priority:
  1. OpenAI direct API  (OPENAI_API_KEY)   — preferred when key is present
  2. GitHub Models      (GITHUB_TOKEN)     — free tier fallback

Usage:
    from sol_llm import SolLLM

    llm = SolLLM()
    response = llm.complete("Analyze this experiment result...", task="interpretation")
    print(response.content)
    print(f"Cost: ${response.cost_usd:.4f}")

    # Structured JSON output
    response = llm.complete_json(
        "Generate a hypothesis...",
        schema={"question": "str", "knob": "str", "values": "list"},
        task="hypothesis",
    )
    print(response.parsed)  # dict
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .config import (
        GITHUB_MODELS_ENDPOINT,
        PROVIDERS,
        MODELS,
        DEFAULT_BUDGET,
        TASK_TEMPERATURES,
        TASK_ROUTING,
    )
except ImportError:
    from config import (
        GITHUB_MODELS_ENDPOINT,
        PROVIDERS,
        MODELS,
        DEFAULT_BUDGET,
        TASK_TEMPERATURES,
        TASK_ROUTING,
    )


# ---------------------------------------------------------------------------
# .env auto-loading
# ---------------------------------------------------------------------------

def _load_dotenv():
    """Load .env from SOL root if API keys are not already set."""
    needs_load = not (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GITHUB_MODELS_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("OPENAI_API_KEY")
    )
    if not needs_load:
        return
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if key and val and key not in os.environ:
                os.environ[key] = val

_load_dotenv()


# ---------------------------------------------------------------------------
# Response wrapper
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Wrapper around an LLM API response with cost tracking."""
    content: str = ""
    parsed: dict | list | None = None   # For JSON mode
    model: str = ""
    role: str = ""                      # slot name used (e.g. "primary", "lightweight")
    provider: str = ""                  # provider used (e.g. "openai", "github")
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_sec: float = 0.0
    task: str = ""
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Cost Ledger (persistent tracking)
# ---------------------------------------------------------------------------

_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_COST_LEDGER = _SOL_ROOT / "data" / "rsi" / "llm_cost_ledger.jsonl"


def _log_cost(response: LLMResponse):
    """Append a cost entry to the persistent ledger."""
    _COST_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": response.model,
        "role": response.role,
        "provider": response.provider,
        "task": response.task,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "cost_usd": response.cost_usd,
        "latency_sec": response.latency_sec,
        "success": response.success,
    }
    with open(_COST_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def load_daily_cost() -> float:
    """Load total cost for today from the ledger."""
    if not _COST_LEDGER.exists():
        return 0.0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = 0.0
    with open(_COST_LEDGER, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    if entry.get("timestamp", "").startswith(today) and entry.get("success"):
                        total += entry.get("cost_usd", 0.0)
                except json.JSONDecodeError:
                    pass
    return total


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class SolLLM:
    """
    LLM client for the SOL RSI pipeline.

    Routes tasks to the most cost-appropriate model tier:
      - lightweight  (gpt-5.4-nano):  reflection, question_gen
      - primary      (gpt-5.4-mini):  synthesis, interpretation, claim_draft
      - reasoning    (gpt-5.4):       hypothesis, deep analysis

    Supports OpenAI direct API (OPENAI_API_KEY) and GitHub Models
    (GITHUB_TOKEN) with automatic provider selection and fallback.
    """

    def __init__(
        self,
        budget: dict | None = None,
        verbose: bool = True,
    ):
        self.budget = {**DEFAULT_BUDGET, **(budget or {})}
        self.verbose = verbose

        # Cumulative tracking for this session
        self.session_calls = 0
        self.session_cost_usd = 0.0
        self.session_tokens_in = 0
        self.session_tokens_out = 0

        # Build one OpenAI-compatible client per available provider
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required: pip install openai")

        self._provider_clients: dict[str, Any] = {}
        for provider_key, provider_cfg in PROVIDERS.items():
            if provider_cfg.get("sdk", "openai") != "openai":
                continue  # Only openai-SDK providers supported in the client
            api_key = self._resolve_key(provider_cfg)
            if not api_key:
                continue
            endpoint = provider_cfg.get("endpoint", "")
            # OpenAI direct API uses the default endpoint (no override needed)
            if provider_key == "openai" and "api.openai.com" in endpoint:
                self._provider_clients[provider_key] = OpenAI(api_key=api_key)
            else:
                self._provider_clients[provider_key] = OpenAI(
                    base_url=endpoint,
                    api_key=api_key,
                )

        if not self._provider_clients:
            raise EnvironmentError(
                "No API key found. Set OPENAI_API_KEY for OpenAI direct access, "
                "or GITHUB_TOKEN for GitHub Models access."
            )

        if self.verbose:
            providers_str = ", ".join(self._provider_clients)
            print(f"  [LLM] Active providers: {providers_str}")

    @staticmethod
    def _resolve_key(provider_cfg: dict) -> str | None:
        """Resolve the API key for a provider from environment variables."""
        env_var = provider_cfg.get("env_var", "GITHUB_TOKEN")
        key = os.environ.get(env_var)
        if not key and env_var == "GITHUB_TOKEN":
            key = os.environ.get("GITHUB_MODELS_TOKEN") or os.environ.get("GH_TOKEN")
        return key or None

    def _get_client_for_slot(self, slot_key: str) -> tuple[Any, str, str]:
        """
        Return (client, model_id, provider_key) for a slot.

        Prefers the slot's configured provider. Falls back to GitHub Models
        using the slot's github_fallback_id if the preferred provider is
        unavailable.
        """
        model_cfg = MODELS[slot_key]
        preferred_provider = model_cfg.get("provider", "github")

        if preferred_provider in self._provider_clients:
            return (
                self._provider_clients[preferred_provider],
                model_cfg["id"],
                preferred_provider,
            )

        # Preferred provider unavailable — fall back to GitHub Models
        github_client = self._provider_clients.get("github")
        if github_client:
            fallback_id = model_cfg.get("github_fallback_id") or model_cfg["id"]
            return github_client, fallback_id, "github"

        # Any remaining available provider
        for pkey, pclient in self._provider_clients.items():
            return pclient, model_cfg["id"], pkey

        raise EnvironmentError(
            f"No available provider client for slot '{slot_key}' "
            f"(preferred: {preferred_provider})."
        )

    def _route_task(self, task: str) -> str:
        """Map a task type to the best available model slot."""
        desired_slot = TASK_ROUTING.get(task, "primary")
        # If the desired slot doesn't exist in MODELS, fall back to primary
        if desired_slot not in MODELS:
            desired_slot = "primary"
        return desired_slot

    # ------------------------------------------------------------------
    # Budget checks
    # ------------------------------------------------------------------

    def _check_budget(self) -> tuple[bool, str]:
        """Return (ok, reason) — False if budget exhausted."""
        if self.session_calls >= self.budget["max_calls_per_cycle"]:
            return False, f"max_calls_per_cycle reached ({self.session_calls})"
        if self.session_cost_usd >= self.budget["max_cost_per_cycle_usd"]:
            return False, f"cycle cost cap reached (${self.session_cost_usd:.2f})"
        daily = load_daily_cost() + self.session_cost_usd
        if daily >= self.budget["max_cost_per_day_usd"]:
            return False, f"daily cost cap reached (${daily:.2f})"
        return True, "OK"

    # ------------------------------------------------------------------
    # Core completion
    # ------------------------------------------------------------------

    def _call_model(
        self,
        messages: list[dict],
        model_key: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Call a specific model slot and return a response."""
        model_cfg = MODELS[model_key]
        is_reasoning = model_cfg.get("is_reasoning", False)

        client, model_id, provider_key = self._get_client_for_slot(model_key)

        response = LLMResponse(
            model=model_id,
            role=model_key,
            provider=provider_key,
        )

        t0 = time.time()
        try:
            kwargs: dict[str, Any] = {
                "model": model_id,
                "messages": messages,
            }

            # Reasoning models (o-series) use different params
            if is_reasoning:
                kwargs["max_completion_tokens"] = max_tokens
                # Reasoning models don't accept temperature or json response_format
            else:
                kwargs["max_tokens"] = max_tokens
                kwargs["temperature"] = temperature
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

            result = client.chat.completions.create(**kwargs)

            response.content = result.choices[0].message.content or ""
            response.input_tokens = getattr(result.usage, "prompt_tokens", 0)
            response.output_tokens = getattr(result.usage, "completion_tokens", 0)
            response.success = True

        except Exception as e:
            response.success = False
            response.error = f"{type(e).__name__}: {e}"
            if self.verbose:
                print(f"    [LLM] {model_key}/{model_id} ({provider_key}) error: {response.error}")

        response.latency_sec = round(time.time() - t0, 2)

        # Compute cost using the slot's configured rates (not provider-specific)
        in_cost = (response.input_tokens / 1000) * model_cfg["cost_per_1k_input"]
        out_cost = (response.output_tokens / 1000) * model_cfg["cost_per_1k_output"]
        response.cost_usd = round(in_cost + out_cost, 6)

        return response

    def complete(
        self,
        prompt: str,
        system: str = "",
        task: str = "general",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Send a prompt to the LLM with task-based routing and automatic fallback.

        Task routing selects the cheapest model tier sufficient for the task:
          - lightweight tasks (reflection, question_gen) → nano model
          - standard tasks   (synthesis, consolidation) → mini model
          - heavy tasks      (hypothesis)               → full model

        Falls back to primary then fallback slot on failure.

        Args:
            prompt: User message content.
            system: System prompt (optional).
            task: Task type for routing and temperature selection.
            temperature: Override default temperature for this task.
            max_tokens: Override max output tokens.

        Returns:
            LLMResponse with content, cost, metadata.
        """
        ok, reason = self._check_budget()
        if not ok:
            return LLMResponse(
                success=False,
                error=f"Budget exhausted: {reason}",
                task=task,
            )

        temp = temperature if temperature is not None else TASK_TEMPERATURES.get(task, 0.4)
        max_tok = max_tokens or self.budget["max_tokens_per_call"]

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Try the task-routed slot first
        routed_slot = self._route_task(task)
        response = self._try_with_retries(messages, routed_slot, max_tok, temp)

        # If routed slot failed and it isn't primary, try primary
        if not response.success and routed_slot != "primary":
            if self.verbose:
                print(f"    [LLM] {routed_slot} failed, trying primary...")
            response = self._try_with_retries(messages, "primary", max_tok, temp)

        # Final fallback
        if not response.success and routed_slot != "fallback":
            if self.verbose:
                print(f"    [LLM] Primary failed, trying fallback...")
            response = self._try_with_retries(messages, "fallback", max_tok, temp)

        response.task = task

        # Track & log
        self.session_calls += 1
        self.session_cost_usd += response.cost_usd
        self.session_tokens_in += response.input_tokens
        self.session_tokens_out += response.output_tokens
        _log_cost(response)

        if self.verbose and response.success:
            print(f"    [LLM] {response.role}/{response.model} ({response.provider}): "
                  f"{response.input_tokens}+{response.output_tokens} tokens, "
                  f"${response.cost_usd:.4f}, {response.latency_sec}s")

        return response

    def complete_json(
        self,
        prompt: str,
        system: str = "",
        schema: dict | None = None,
        task: str = "general",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Request structured JSON output from the LLM with task-based routing.

        If a schema is provided, it's included in the system prompt as
        guidance. The response is parsed into response.parsed.
        """
        schema_instruction = ""
        if schema:
            schema_instruction = (
                "\n\nRespond with a JSON object matching this schema:\n"
                f"```json\n{json.dumps(schema, indent=2)}\n```\n"
                "Return ONLY valid JSON, no markdown fencing."
            )

        full_system = (system or "") + schema_instruction
        if not full_system.strip():
            full_system = "Respond with valid JSON only. No markdown fencing."

        ok, reason = self._check_budget()
        if not ok:
            return LLMResponse(
                success=False,
                error=f"Budget exhausted: {reason}",
                task=task,
            )

        temp = temperature if temperature is not None else TASK_TEMPERATURES.get(task, 0.4)
        max_tok = max_tokens or self.budget["max_tokens_per_call"]

        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": prompt},
        ]

        # Try task-routed slot with JSON mode
        routed_slot = self._route_task(task)
        response = self._try_with_retries(messages, routed_slot, max_tok, temp, json_mode=True)

        if not response.success and routed_slot != "primary":
            if self.verbose:
                print(f"    [LLM] {routed_slot} JSON failed, trying primary...")
            response = self._try_with_retries(messages, "primary", max_tok, temp, json_mode=True)

        if not response.success and routed_slot != "fallback":
            if self.verbose:
                print(f"    [LLM] Primary JSON failed, trying fallback...")
            response = self._try_with_retries(messages, "fallback", max_tok, temp, json_mode=True)

        response.task = task

        # Parse JSON from response
        if response.success and response.content:
            try:
                # Strip markdown fencing if model included it anyway
                text = response.content.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                response.parsed = json.loads(text)
            except json.JSONDecodeError as e:
                response.parsed = None
                response.error = f"JSON parse failed: {e}"
                if self.verbose:
                    print(f"    [LLM] JSON parse error: {e}")

        # Track & log
        self.session_calls += 1
        self.session_cost_usd += response.cost_usd
        self.session_tokens_in += response.input_tokens
        self.session_tokens_out += response.output_tokens
        _log_cost(response)

        if self.verbose and response.success:
            print(f"    [LLM] {response.role}/{response.model} ({response.provider}): "
                  f"{response.input_tokens}+{response.output_tokens} tokens, "
                  f"${response.cost_usd:.4f}, {response.latency_sec}s")

        return response

    def _try_with_retries(
        self,
        messages: list[dict],
        model_key: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Try a model with retries."""
        max_retries = self.budget["max_retries"]
        delay = self.budget["retry_delay_sec"]

        last_response = LLMResponse(success=False, error="no attempts made")
        for attempt in range(max_retries + 1):
            if attempt > 0:
                if self.verbose:
                    print(f"    [LLM] Retry {attempt}/{max_retries} after {delay}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff

            response = self._call_model(messages, model_key, max_tokens, temperature, json_mode)
            if response.success:
                return response
            last_response = response

        return last_response

    # ------------------------------------------------------------------
    # Session summary
    # ------------------------------------------------------------------

    def session_summary(self) -> dict:
        """Return summary of this session's LLM usage."""
        return {
            "calls": self.session_calls,
            "cost_usd": round(self.session_cost_usd, 4),
            "tokens_in": self.session_tokens_in,
            "tokens_out": self.session_tokens_out,
        }

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    @staticmethod
    def is_available() -> bool:
        """Check if an LLM client can be created (any API key present)."""
        return bool(
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GITHUB_MODELS_TOKEN")
            or os.environ.get("GH_TOKEN")
        )

