"""
SOL LLM — Client
==================
Unified LLM client for the SOL RSI pipeline.

Uses OpenAI-compatible endpoints configured in models.json
(for example GitHub Models, OpenAI direct, or Modal GLM-5).

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
import random
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .config import (
        PROVIDERS,
        MODELS,
        DEFAULT_BUDGET,
        TASK_TEMPERATURES,
    )
except ImportError:
    from config import (
        PROVIDERS,
        MODELS,
        DEFAULT_BUDGET,
        TASK_TEMPERATURES,
    )


# ---------------------------------------------------------------------------
# .env auto-loading
# ---------------------------------------------------------------------------

def _load_dotenv():
    """Load .env from SOL root for provider API keys if needed."""
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


def _env_budget_overrides() -> dict[str, Any]:
    """Read optional runtime budget overrides from environment variables."""
    env_to_key: dict[str, tuple[str, type]] = {
        "SOL_LLM_MAX_TOKENS": ("max_tokens_per_call", int),
        "SOL_LLM_MAX_RETRIES": ("max_retries", int),
        "SOL_LLM_RETRY_DELAY_SEC": ("retry_delay_sec", float),
        "SOL_LLM_RETRY_JITTER_SEC": ("retry_jitter_sec", float),
        "SOL_LLM_TIMEOUT_SEC": ("timeout_sec", float),
        "SOL_LLM_REQUEST_TIMEOUT_SEC": ("request_timeout_sec", float),
        "SOL_LLM_LOCK_TIMEOUT_SEC": ("lock_timeout_sec", float),
    }
    overrides: dict[str, Any] = {}
    for env_name, (budget_key, cast_type) in env_to_key.items():
        raw = os.environ.get(env_name)
        if raw is None or raw == "":
            continue
        try:
            overrides[budget_key] = cast_type(raw)
        except (TypeError, ValueError):
            continue
    return overrides


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
_REQUEST_LOCK = _SOL_ROOT / "data" / "rsi" / "llm_request.lock"
_LOCK_GUARD = threading.Lock()


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
        "error": response.error,
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


def _acquire_single_flight_lock(timeout_sec: float, stale_after_sec: float = 300.0) -> None:
    """Acquire a process-wide + cross-process lock for one in-flight LLM request."""
    start = time.time()
    poll_sec = 0.2
    _REQUEST_LOCK.parent.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            with _LOCK_GUARD:
                fd = os.open(str(_REQUEST_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(f"pid={os.getpid()}\n")
                    f.write(f"ts={datetime.now(timezone.utc).isoformat()}\n")
            return
        except FileExistsError:
            try:
                age_sec = time.time() - _REQUEST_LOCK.stat().st_mtime
                if age_sec > stale_after_sec:
                    _REQUEST_LOCK.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue

            if (time.time() - start) >= timeout_sec:
                raise TimeoutError(
                    f"Timed out waiting for single-flight LLM lock after {timeout_sec:.1f}s"
                )
            time.sleep(poll_sec)


def _release_single_flight_lock() -> None:
    """Release single-flight lock if held."""
    with _LOCK_GUARD:
        _REQUEST_LOCK.unlink(missing_ok=True)


def _extract_message_text(message: Any) -> str:
    """Extract text from OpenAI-compatible chat message variants."""
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
        if parts:
            return "\n".join(parts)

    reasoning = getattr(message, "reasoning_content", None)
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning
    return ""


def _strip_markdown_fence(text: str) -> str:
    """Strip a top-level markdown code fence if present."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped
    if lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _extract_fenced_json_block(text: str) -> str | None:
    """Extract JSON from a fenced markdown block if one exists."""
    raw = text
    fence = "```"
    idx = 0
    while True:
        start = raw.find(fence, idx)
        if start < 0:
            return None
        lang_end = raw.find("\n", start)
        if lang_end < 0:
            return None
        header = raw[start + 3:lang_end].strip().lower()
        end = raw.find(fence, lang_end + 1)
        if end < 0:
            return None
        body = raw[lang_end + 1:end].strip()
        if header in {"", "json", "jsonc", "javascript", "js"} and body:
            if body.startswith("{") or body.startswith("["):
                return body
        idx = end + 3


def _extract_first_balanced_json(text: str) -> str | None:
    """Extract the first balanced JSON object/array from free-form text."""
    starts: list[tuple[int, str, str]] = []
    obj_idx = text.find("{")
    arr_idx = text.find("[")
    if obj_idx >= 0:
        starts.append((obj_idx, "{", "}"))
    if arr_idx >= 0:
        starts.append((arr_idx, "[", "]"))
    if not starts:
        return None

    starts.sort(key=lambda t: t[0])
    for start, opener, closer in starts:
        depth = 0
        in_string = False
        escaped = False
        for pos in range(start, len(text)):
            ch = text[pos]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start:pos + 1]
    return None


def _parse_json_from_text(content: str) -> tuple[dict | list | None, str | None]:
    """Parse JSON from strict or hybrid markdown/text response."""
    text = content.strip()
    if not text:
        return None, "empty response"

    candidates: list[str] = []
    candidates.append(text)

    unfenced = _strip_markdown_fence(text)
    if unfenced not in candidates:
        candidates.append(unfenced)

    fenced = _extract_fenced_json_block(text)
    if fenced and fenced not in candidates:
        candidates.append(fenced)

    balanced = _extract_first_balanced_json(text)
    if balanced and balanced not in candidates:
        candidates.append(balanced)

    last_error: str | None = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, (dict, list)):
                return parsed, None
            last_error = "JSON root is not object/array"
        except json.JSONDecodeError as exc:
            last_error = str(exc)

    return None, f"JSON parse failed: {last_error or 'unknown parse error'}"


def _is_retryable_error(error: str | None) -> bool:
    """Return True for transient transport/provider errors worth retrying."""
    if not error:
        return False
    text = error.lower()
    retryable_tokens = [
        "timeout",
        "timed out",
        "502",
        "503",
        "504",
        "connection",
        "rate limit",
        "temporarily unavailable",
    ]
    return any(token in text for token in retryable_tokens)


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
        env_overrides = _env_budget_overrides()
        self.budget = {**DEFAULT_BUDGET, **env_overrides, **(budget or {})}
        self.verbose = verbose

        # Cumulative tracking for this session
        self.session_calls = 0
        self.session_cost_usd = 0.0
        self.session_tokens_in = 0
        self.session_tokens_out = 0

        # Lazy-import openai to avoid top-level dependency
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package required: pip install openai"
            )
        self._openai_cls = OpenAI
        self._provider_clients: dict[str, Any] = {}

    @staticmethod
    def _resolve_api_key(provider_cfg: dict) -> str | None:
        """Resolve API key from provider env var."""
        env_var = provider_cfg.get("env_var", "MODAL_API_KEY")
        return os.environ.get(env_var)

    def _get_client_for_provider(self, provider_key: str):
        """Get or create OpenAI-compatible client for provider."""
        if provider_key in self._provider_clients:
            return self._provider_clients[provider_key]

        provider_cfg = PROVIDERS.get(provider_key)
        if not provider_cfg:
            raise KeyError(f"Unknown provider '{provider_key}' in model config")

        api_key = self._resolve_api_key(provider_cfg)
        if not api_key:
            env_var = provider_cfg.get("env_var", "API_KEY")
            raise EnvironmentError(
                f"Missing API key for provider '{provider_key}'. Set {env_var}."
            )

        request_timeout = float(
            self.budget.get(
                "request_timeout_sec",
                self.budget.get("timeout_sec", 75),
            )
        )

        client = self._openai_cls(
            base_url=provider_cfg["endpoint"],
            api_key=api_key,
            timeout=request_timeout,
        )
        self._provider_clients[provider_key] = client
        return client

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
        provider_key = model_cfg.get("provider", "modal_glm5")

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

            client = self._get_client_for_provider(provider_key)

            lock_timeout = float(
                self.budget.get(
                    "lock_timeout_sec",
                    self.budget.get("timeout_sec", 30),
                )
            )
            stale_timeout = max(lock_timeout * 2.0, 300.0)
            _acquire_single_flight_lock(timeout_sec=lock_timeout, stale_after_sec=stale_timeout)
            try:
                result = client.chat.completions.create(**kwargs)
            finally:
                _release_single_flight_lock()

            response.content = _extract_message_text(result.choices[0].message)
            response.input_tokens = getattr(result.usage, "prompt_tokens", 0)
            response.output_tokens = getattr(result.usage, "completion_tokens", 0)
            response.success = True

        except Exception as e:
            response.success = False
            response.error = f"{type(e).__name__}: {e}"
            if self.verbose:
                print(
                    f"    [LLM] {model_key} ({provider_key}/{model_id}) error: {response.error}"
                )

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

        strict_system = (system or "") + schema_instruction
        if not strict_system.strip():
            strict_system = "Respond with valid JSON only. No markdown fencing."

        hybrid_instruction = (
            "\n\nHYBRID FORMAT MODE:\n"
            "- You may include a brief markdown explanation.\n"
            "- Include exactly one fenced ```json block with the final payload.\n"
            "- The JSON block must be valid and self-contained.\n"
            "- If unsure, return only the JSON block."
        )
        hybrid_system = (system or "") + schema_instruction + hybrid_instruction
        if not hybrid_system.strip():
            hybrid_system = (
                "Return markdown optionally, but always include exactly one fenced "
                "```json block containing valid JSON."
            )

        ok, reason = self._check_budget()
        if not ok:
            return LLMResponse(
                success=False,
                error=f"Budget exhausted: {reason}",
                task=task,
            )

        temp = temperature if temperature is not None else TASK_TEMPERATURES.get(task, 0.4)
        max_tok = max_tokens or self.budget["max_tokens_per_call"]

        strict_messages = [
            {"role": "system", "content": strict_system},
            {"role": "user", "content": prompt},
        ]
        hybrid_messages = [
            {"role": "system", "content": hybrid_system},
            {"role": "user", "content": prompt},
        ]

        def _attempt_parse(
            messages: list[dict],
            model_key: str,
            *,
            json_mode: bool,
            label: str,
        ) -> LLMResponse:
            attempt = self._try_with_retries(messages, model_key, max_tok, temp, json_mode=json_mode)
            if not attempt.success:
                return attempt
            parsed, parse_error = _parse_json_from_text(attempt.content)
            if parsed is not None:
                attempt.parsed = parsed
                return attempt
            attempt.success = False
            attempt.error = parse_error
            if self.verbose and parse_error:
                print(f"    [LLM] {label} parse error: {parse_error}")
            return attempt

        response = _attempt_parse(strict_messages, "primary", json_mode=True, label="primary strict")

        if not response.success:
            if self.verbose:
                print("    [LLM] Primary strict JSON failed, trying fallback strict...")
            response = _attempt_parse(strict_messages, "fallback", json_mode=True, label="fallback strict")

        if not response.success:
            if self.verbose:
                print("    [LLM] Strict JSON failed, trying hybrid markdown+JSON...")
            response = _attempt_parse(hybrid_messages, "fallback", json_mode=False, label="fallback hybrid")

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
        jitter = float(self.budget.get("retry_jitter_sec", 1.0))

        last_response = LLMResponse(success=False, error="no attempts made")
        for attempt in range(max_retries + 1):
            if attempt > 0:
                sleep_sec = delay + random.uniform(0.0, max(0.0, jitter))
                if self.verbose:
                    print(
                        f"    [LLM] Retry {attempt}/{max_retries} after {sleep_sec:.1f}s..."
                    )
                time.sleep(sleep_sec)
                delay *= 2  # Exponential backoff

            response = self._call_model(messages, model_key, max_tokens, temperature, json_mode)
            if response.success:
                return response
            if attempt < max_retries and not _is_retryable_error(response.error):
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
        """Check if any configured model provider has a usable API key."""
        for model_cfg in MODELS.values():
            provider_key = model_cfg.get("provider", "modal_glm5")
            provider_cfg = PROVIDERS.get(provider_key, {})
            env_var = provider_cfg.get("env_var", "MODAL_API_KEY")
            key = os.environ.get(env_var)
            if key:
                return True
        return False
