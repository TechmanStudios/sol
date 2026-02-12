"""
SOL LLM — Client
==================
Unified LLM client for the SOL RSI pipeline.

Uses GitHub Models API (OpenAI-compatible endpoint) with:
  - Primary:   GPT-5 Chat
  - Fallback:  GPT-5 Nano (reasoning model)
  - Reasoning: OpenAI o3

Features:
  - Automatic fallback on primary failure
  - Cost tracking per call and cumulative
  - Structured JSON output mode
  - Rate limiting / budget enforcement
  - Retry with backoff

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
        MODELS,
        DEFAULT_BUDGET,
        TASK_TEMPERATURES,
    )
except ImportError:
    from config import (
        GITHUB_MODELS_ENDPOINT,
        MODELS,
        DEFAULT_BUDGET,
        TASK_TEMPERATURES,
    )


# ---------------------------------------------------------------------------
# .env auto-loading
# ---------------------------------------------------------------------------

def _load_dotenv():
    """Load .env from SOL root if GITHUB_TOKEN is not already set."""
    if os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_MODELS_TOKEN"):
        return  # already configured
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
    role: str = ""                      # "primary" or "fallback"
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

    Wraps GitHub Models API with automatic fallback, cost tracking,
    and budget enforcement.
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

        # Resolve API key — check multiple env var names
        self.api_key = (
            os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GITHUB_MODELS_TOKEN")
            or os.environ.get("GH_TOKEN")
        )
        if not self.api_key:
            raise EnvironmentError(
                "No GitHub token found. Set GITHUB_TOKEN environment variable "
                "with a fine-grained PAT that has GitHub Models API access."
            )

        # Lazy-import openai to avoid top-level dependency
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package required: pip install openai"
            )

        self._client = OpenAI(
            base_url=GITHUB_MODELS_ENDPOINT,
            api_key=self.api_key,
        )

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
        """Call a specific model and return a response."""
        model_cfg = MODELS[model_key]
        model_id = model_cfg["id"]
        is_reasoning = model_cfg.get("is_reasoning", False)

        response = LLMResponse(
            model=model_id,
            role=model_key,
        )

        t0 = time.time()
        try:
            kwargs: dict[str, Any] = {
                "model": model_id,
                "messages": messages,
            }

            # Reasoning models (o-series, gpt-5 non-chat) use different params
            if is_reasoning:
                kwargs["max_completion_tokens"] = max_tokens
                # Reasoning models don't accept temperature or json response_format
            else:
                kwargs["max_tokens"] = max_tokens
                kwargs["temperature"] = temperature
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

            result = self._client.chat.completions.create(**kwargs)

            response.content = result.choices[0].message.content or ""
            response.input_tokens = getattr(result.usage, "prompt_tokens", 0)
            response.output_tokens = getattr(result.usage, "completion_tokens", 0)
            response.success = True

        except Exception as e:
            response.success = False
            response.error = f"{type(e).__name__}: {e}"
            if self.verbose:
                print(f"    [LLM] {model_key} ({model_id}) error: {response.error}")

        response.latency_sec = round(time.time() - t0, 2)

        # Compute cost
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
        Send a prompt to the LLM with automatic fallback.

        Args:
            prompt: User message content.
            system: System prompt (optional).
            task: Task type for temperature/budget tracking.
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

        # Try primary
        response = self._try_with_retries(messages, "primary", max_tok, temp)

        # Fallback if primary failed
        if not response.success:
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
            print(f"    [LLM] {response.role}/{response.model}: "
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
        Request structured JSON output from the LLM.

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

        # Try primary with JSON mode
        response = self._try_with_retries(messages, "primary", max_tok, temp, json_mode=True)
        if not response.success:
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
            print(f"    [LLM] {response.role}/{response.model}: "
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
        """Check if an LLM client can be created (API key present)."""
        return bool(
            os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GITHUB_MODELS_TOKEN")
            or os.environ.get("GH_TOKEN")
        )
