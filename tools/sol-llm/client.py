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

import hashlib
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
    """Load .env from ~/.env, workspace root, and SOL root if keys are missing from environment."""
    candidate_paths = [
        Path.home() / ".env",
        Path(__file__).resolve().parents[3] / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(".env"),
    ]
    for env_path in candidate_paths:
        if not env_path.exists():
            continue
        with open(env_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and val and key not in os.environ:
                    os.environ[key] = val

_load_dotenv()


# ---------------------------------------------------------------------------
# Response wrapper
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Wrapper around an LLM API response with cost and thought-telemetry tracking."""
    content: str = ""
    parsed: dict | list | None = None   # For JSON mode
    model: str = ""
    role: str = ""                      # "primary", "fallback", or "reasoning"
    input_tokens: int = 0
    output_tokens: int = 0
    thought_tokens: int = 0
    cached_input_tokens: int = 0
    cost_usd: float = 0.0
    latency_sec: float = 0.0
    task: str = ""
    success: bool = True
    error: str | None = None
    interaction_id: str = ""
    previous_interaction_id: str = ""
    thinking_level: str = ""
    thought_step_count: int = 0
    thought_summaries: list[str] = field(default_factory=list)
    thought_signature_digests: list[str] = field(default_factory=list)
    function_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_executions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.content

    @property
    def total_input_tokens(self) -> int:
        return self.input_tokens

    @property
    def total_output_tokens(self) -> int:
        return self.output_tokens

    @property
    def total_thought_tokens(self) -> int:
        return self.thought_tokens

    @property
    def total_cached_input_tokens(self) -> int:
        return self.cached_input_tokens

    def to_dict(self) -> dict:
        return asdict(self)


def _extract_step_text_items(raw_items: Any) -> str:
    """Extract concatenated text from a list/tuple of Content items or string."""
    if raw_items is None:
        return ""
    if isinstance(raw_items, str):
        return raw_items
    if isinstance(raw_items, (list, tuple)):
        parts: list[str] = []
        for item in raw_items:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                item_type = item.get("type", "text")
                if item_type in ("text", "output_text", "thought", None):
                    txt = item.get("text") or item.get("content") or ""
                    if isinstance(txt, str):
                        parts.append(txt)
            else:
                item_type = getattr(item, "type", "text")
                if item_type in ("text", "output_text", "thought", None):
                    txt = getattr(item, "text", None)
                    if isinstance(txt, str):
                        parts.append(txt)
        return "".join(parts)
    return str(raw_items)


def _coerce_arguments_dict(raw_args: Any) -> dict[str, Any]:
    """Normalize function_call arguments from SDK object, dict, or JSON string."""
    if raw_args is None:
        return {}
    if isinstance(raw_args, dict):
        return dict(raw_args)
    if isinstance(raw_args, str):
        s = raw_args.strip()
        if not s:
            return {}
        try:
            parsed = json.loads(s)
            return dict(parsed) if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {"raw": raw_args}
    if hasattr(raw_args, "items"):
        try:
            return dict(raw_args.items())
        except Exception:
            pass
    if hasattr(raw_args, "__dict__"):
        return {k: v for k, v in vars(raw_args).items() if not k.startswith("_")}
    return {}


def extract_gemini_interaction_telemetry(interaction: Any) -> dict[str, Any]:
    """Extract multi-hop output text, thought summaries, signature digests, function_calls, and token usage."""
    interaction_id = str(getattr(interaction, "id", "") or "")
    steps = getattr(interaction, "outputs", None) or getattr(interaction, "steps", None) or []

    model_output_chunks: list[str] = []
    thought_summaries: list[str] = []
    thought_signature_digests: list[str] = []
    function_calls: list[dict[str, Any]] = []
    thought_step_count = 0

    for step in steps:
        step_type = getattr(step, "type", None) or (step.get("type") if isinstance(step, dict) else None)
        if step_type == "thought":
            thought_step_count += 1
            raw_summary = getattr(step, "summary", None) or getattr(step, "text", None) or (
                step.get("summary") or step.get("text") if isinstance(step, dict) else ""
            )
            summary_str = _extract_step_text_items(raw_summary).strip()
            if summary_str:
                thought_summaries.append(summary_str)
            sig = getattr(step, "signature", None) or getattr(step, "thought_signature", None) or (
                step.get("signature") or step.get("thought_signature") if isinstance(step, dict) else None
            )
            sig_bytes = sig if isinstance(sig, bytes) else str(sig or summary_str or f"step-{thought_step_count}").encode("utf-8")
            thought_signature_digests.append(hashlib.sha256(sig_bytes).hexdigest())
        elif step_type == "function_call":
            call_id = str(
                getattr(step, "id", None)
                or getattr(step, "call_id", None)
                or (step.get("id") or step.get("call_id") if isinstance(step, dict) else "")
                or f"fc-{len(function_calls) + 1}"
            )
            fn_name = str(
                getattr(step, "name", None)
                or (step.get("name") if isinstance(step, dict) else "")
                or ""
            )
            raw_args = getattr(step, "arguments", None) if not isinstance(step, dict) else step.get("arguments")
            fn_args = _coerce_arguments_dict(raw_args)
            function_calls.append(
                {
                    "id": call_id,
                    "name": fn_name,
                    "arguments": fn_args,
                }
            )
            sig = getattr(step, "signature", None) or (step.get("signature") if isinstance(step, dict) else None)
            if sig:
                sig_bytes = sig if isinstance(sig, bytes) else str(sig).encode("utf-8")
                sig_hex = hashlib.sha256(sig_bytes).hexdigest()
                if sig_hex not in thought_signature_digests:
                    thought_signature_digests.append(sig_hex)
        elif step_type in ("model_output", "text", "output_text"):
            raw_content = getattr(step, "content", None) if not isinstance(step, dict) else step.get("content")
            raw_text = getattr(step, "text", None) if not isinstance(step, dict) else step.get("text")
            if isinstance(raw_content, (list, tuple)):
                chunk_text = _extract_step_text_items(raw_content)
            elif isinstance(raw_text, str) and raw_text:
                chunk_text = raw_text
            elif isinstance(raw_content, str) and raw_content:
                chunk_text = raw_content
            else:
                chunk_text = ""
            if chunk_text:
                model_output_chunks.append(chunk_text)

    output_text = getattr(interaction, "output_text", None)
    if model_output_chunks:
        joined_chunks = "".join(model_output_chunks)
        # Prefer multi-hop concatenation if it is at least as complete as output_text
        if not output_text or len(joined_chunks) >= len(str(output_text)):
            content = joined_chunks
        else:
            content = str(output_text)
    else:
        content = str(output_text or "")

    usage = getattr(interaction, "usage", None) or getattr(interaction, "usage_metadata", None)

    def _read_usage_int(*keys: str) -> int:
        if usage is None:
            return 0
        for k in keys:
            val = usage.get(k) if isinstance(usage, dict) else getattr(usage, k, None)
            if val is not None and int(val) > 0:
                return int(val)
        return 0

    input_tokens = _read_usage_int(
        "total_input_tokens", "input_tokens", "prompt_token_count", "prompt_tokens"
    )
    output_tokens = _read_usage_int(
        "total_output_tokens", "output_tokens", "candidates_token_count", "completion_tokens"
    )
    thought_tokens = _read_usage_int(
        "total_thought_tokens", "thought_tokens", "thoughts_token_count"
    )
    cached_input_tokens = _read_usage_int(
        "total_cached_input_tokens", "cached_input_tokens", "cached_content_token_count", "cached_tokens"
    )

    return {
        "interaction_id": interaction_id,
        "content": content,
        "thought_step_count": thought_step_count,
        "thought_summaries": thought_summaries,
        "thought_signature_digests": thought_signature_digests,
        "function_calls": function_calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thought_tokens": thought_tokens,
        "cached_input_tokens": cached_input_tokens,
        "total_input_tokens": input_tokens,
        "total_output_tokens": output_tokens,
        "total_thought_tokens": thought_tokens,
        "total_cached_input_tokens": cached_input_tokens,
    }


def _poll_interaction_until_complete(
    client: Any,
    interaction: Any,
    poll_interval_s: float = 0.5,
    max_wait_s: float = 120.0,
) -> Any:
    """Poll `client.interactions.get` when status is in_progress / queued."""
    if hasattr(client.interactions, "get"):
        status = str(getattr(interaction, "status", "") or "").lower()
        poll_deadline = time.time() + max(0.1, float(max_wait_s))
        while status in ("in_progress", "queued", "running", "pending", "processing") and time.time() < poll_deadline:
            time.sleep(max(0.005, float(poll_interval_s)))
            interaction = client.interactions.get(id=interaction.id)
            status = str(getattr(interaction, "status", "") or "").lower()
    return interaction


def run_gemini_interaction_with_tools(
    client: Any,
    *,
    model: str = "gemini-4-argon",
    input_payload: Any = None,
    prompt: Any = None,
    system_instruction: str = "",
    thinking_level: str = "high",
    max_output_tokens: int = 32768,
    previous_interaction_id: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_dispatcher: Any | None = None,
    max_tool_rounds: int = 2,
    response_format: dict[str, Any] | None = None,
    background: bool = False,
    poll_interval_s: float = 0.5,
    max_wait_s: float = 120.0,
) -> dict[str, Any]:
    """
    Execute a stateful Gemini Interactions API turn with optional multi-turn
    `function_call` -> `function_result` loops chained via `previous_interaction_id`.

    Accumulates `thought_summaries`, `thought_signature_digests`, `tool_executions`,
    and token `usage` across all tool turns and final structured JSON output turns.
    """
    if input_payload is None and prompt is not None:
        input_payload = prompt
    effective_max_tokens = max(
        int(max_output_tokens or 32768),
        32768 if str(model).startswith("gemini-4") else 4096,
    )
    gen_config: dict[str, Any] = {
        "max_output_tokens": effective_max_tokens,
        "thinking_level": thinking_level or "high",
        "thinking_summaries": "auto",
    }

    has_tools = bool(tools and tool_dispatcher is not None and max_tool_rounds > 0)
    max_rounds = int(max_tool_rounds) if has_tools else 0

    current_input: Any = input_payload
    current_prev_id: str | None = previous_interaction_id or None

    all_thought_summaries: list[str] = []
    all_thought_signature_digests: list[str] = []
    all_function_calls: list[dict[str, Any]] = []
    tool_executions: list[dict[str, Any]] = []
    interaction_chain: list[str] = []

    total_thought_steps = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_thought_tokens = 0
    total_cached_input_tokens = 0
    final_content = ""
    last_interaction_id = previous_interaction_id or ""

    for round_idx in range(max_rounds + 1):
        create_kwargs: dict[str, Any] = {
            "model": model,
            "input": current_input,
            "generation_config": gen_config,
        }
        if system_instruction:
            create_kwargs["system_instruction"] = system_instruction
        if current_prev_id:
            create_kwargs["previous_interaction_id"] = current_prev_id
        if background:
            create_kwargs["background"] = True
        if tools and (not has_tools or round_idx < max_rounds):
            create_kwargs["tools"] = tools

        # When tools are active, omit response_format on tool-exploration turns so
        # the model can freely emit step.type == "function_call" without JSON grammar lock.
        if response_format is not None and (not has_tools or round_idx >= max_rounds):
            create_kwargs["response_format"] = response_format

        try:
            interaction = client.interactions.create(**create_kwargs)
        except Exception:
            if "response_format" in create_kwargs and tools:
                # Some endpoints require tools on a function_result turn and disallow response_format simultaneously
                fallback_kwargs = dict(create_kwargs)
                fallback_kwargs.pop("response_format", None)
                fallback_kwargs["tools"] = tools
                interaction = client.interactions.create(**fallback_kwargs)
            else:
                raise

        interaction = _poll_interaction_until_complete(
            client,
            interaction,
            poll_interval_s=poll_interval_s,
            max_wait_s=max_wait_s,
        )
        telemetry = extract_gemini_interaction_telemetry(interaction)

        if telemetry["interaction_id"]:
            last_interaction_id = telemetry["interaction_id"]
            interaction_chain.append(telemetry["interaction_id"])
        total_thought_steps += int(telemetry["thought_step_count"])
        for ts in telemetry["thought_summaries"]:
            if ts not in all_thought_summaries:
                all_thought_summaries.append(ts)
        for sig_d in telemetry["thought_signature_digests"]:
            if sig_d not in all_thought_signature_digests:
                all_thought_signature_digests.append(sig_d)

        total_input_tokens += int(telemetry["input_tokens"])
        total_output_tokens += int(telemetry["output_tokens"])
        total_thought_tokens += int(telemetry["thought_tokens"])
        total_cached_input_tokens = max(total_cached_input_tokens, int(telemetry["cached_input_tokens"]))

        if telemetry["content"]:
            final_content = telemetry["content"]

        fcalls = telemetry["function_calls"]
        if not fcalls or not has_tools or round_idx >= max_rounds:
            break

        function_results: list[dict[str, Any]] = []
        for fc in fcalls:
            all_function_calls.append(fc)
            t0_call = time.perf_counter()
            try:
                tool_res = tool_dispatcher(fc["name"], fc["arguments"])
            except Exception as exc:
                tool_res = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            elapsed_ms = round((time.perf_counter() - t0_call) * 1000.0, 3)
            tool_executions.append(
                {
                    "round_index": round_idx,
                    "call_id": fc["id"],
                    "tool_name": fc["name"],
                    "arguments": fc["arguments"],
                    "result": tool_res,
                    "duration_ms": elapsed_ms,
                    "interaction_id": telemetry["interaction_id"],
                }
            )
            function_results.append(
                {
                    "type": "function_result",
                    "name": fc["name"],
                    "call_id": fc["id"],
                    "result": [
                        {
                            "type": "text",
                            "text": json.dumps(tool_res, sort_keys=True, default=str),
                        }
                    ],
                }
            )

        current_prev_id = telemetry["interaction_id"] or current_prev_id
        current_input = function_results

    # If response_format was requested alongside tools and the model ended without valid JSON text,
    # perform a final schema-constrained synthesis turn chained to the last interaction ID.
    if response_format is not None and has_tools:
        needs_json_turn = not final_content.strip()
        if not needs_json_turn:
            try:
                txt = final_content.strip()
                if txt.startswith("```"):
                    txt = txt.split("\n", 1)[1] if "\n" in txt else txt[3:]
                    if txt.endswith("```"):
                        txt = txt[:-3]
                json.loads(txt.strip())
            except Exception:
                needs_json_turn = True
        if needs_json_turn and last_interaction_id:
            final_kwargs: dict[str, Any] = {
                "model": model,
                "input": "Synthesize the final structured JSON response incorporating the substrate tool results above.",
                "generation_config": gen_config,
                "previous_interaction_id": last_interaction_id,
                "response_format": response_format,
            }
            if system_instruction:
                final_kwargs["system_instruction"] = system_instruction
            try:
                final_inter = client.interactions.create(**final_kwargs)
                final_inter = _poll_interaction_until_complete(
                    client,
                    final_inter,
                    poll_interval_s=poll_interval_s,
                    max_wait_s=max_wait_s,
                )
                f_tel = extract_gemini_interaction_telemetry(final_inter)
                if f_tel["interaction_id"]:
                    last_interaction_id = f_tel["interaction_id"]
                    interaction_chain.append(f_tel["interaction_id"])
                total_thought_steps += int(f_tel["thought_step_count"])
                for ts in f_tel["thought_summaries"]:
                    if ts not in all_thought_summaries:
                        all_thought_summaries.append(ts)
                for sig_d in f_tel["thought_signature_digests"]:
                    if sig_d not in all_thought_signature_digests:
                        all_thought_signature_digests.append(sig_d)
                total_input_tokens += int(f_tel["input_tokens"])
                total_output_tokens += int(f_tel["output_tokens"])
                total_thought_tokens += int(f_tel["thought_tokens"])
                total_cached_input_tokens = max(total_cached_input_tokens, int(f_tel["cached_input_tokens"]))
                if f_tel["content"]:
                    final_content = f_tel["content"]
            except Exception:
                pass

    return {
        "interaction_id": last_interaction_id,
        "interaction_chain": interaction_chain,
        "content": final_content,
        "thought_step_count": max(total_thought_steps, len(all_thought_summaries)),
        "thought_summaries": all_thought_summaries,
        "thought_signature_digests": all_thought_signature_digests,
        "function_calls": all_function_calls,
        "tool_executions": tool_executions,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "thought_tokens": total_thought_tokens,
        "cached_input_tokens": total_cached_input_tokens,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_thought_tokens": total_thought_tokens,
        "total_cached_input_tokens": total_cached_input_tokens,
    }



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
        "thought_tokens": response.thought_tokens,
        "cached_input_tokens": response.cached_input_tokens,
        "cost_usd": response.cost_usd,
        "latency_sec": response.latency_sec,
        "interaction_id": response.interaction_id,
        "thinking_level": response.thinking_level,
        "thought_step_count": response.thought_step_count,
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


def load_recent_calls_count(seconds: int) -> int:
    """Load count of calls in the last X seconds from the ledger."""
    if not _COST_LEDGER.exists():
        return 0
    now = datetime.now(timezone.utc)
    count = 0
    with open(_COST_LEDGER, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    ts_str = entry.get("timestamp", "")
                    if ts_str:
                        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if (now - dt).total_seconds() <= seconds:
                            count += 1
                except (json.JSONDecodeError, ValueError):
                    pass
    return count


def load_daily_calls_count() -> int:
    """Load total number of calls made today from the ledger."""
    if not _COST_LEDGER.exists():
        return 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0
    with open(_COST_LEDGER, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    if entry.get("timestamp", "").startswith(today):
                        count += 1
                except (json.JSONDecodeError, ValueError):
                    pass
    return count


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class SolLLM:
    """
    LLM client for the SOL RSI & Reflective Agentic Domain pipeline.

    Supports Google Gemini Interactions API (`google-genai`, `gemini-4-argon`)
    and OpenAI-compatible endpoints with automatic fallback, thought signature
    telemetry, stateful `previous_interaction_id` chaining, and budget enforcement.
    """

    def __init__(
        self,
        budget: dict | None = None,
        verbose: bool = True,
        gemini_client: Any = None,
    ):
        self.budget = {**DEFAULT_BUDGET, **(budget or {})}
        self.verbose = verbose

        # Cumulative tracking for this session
        self.session_calls = 0
        self.session_cost_usd = 0.0
        self.session_tokens_in = 0
        self.session_tokens_out = 0

        # Resolve primary API key for backward compatibility
        self.api_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GITHUB_MODELS_TOKEN")
            or os.environ.get("GH_TOKEN")
            or os.environ.get("OPENAI_API_KEY")
        )

        self._clients: dict[str, Any] = {}
        if gemini_client is not None:
            self._clients["google:google-genai"] = gemini_client
            self._clients["google"] = gemini_client

    def _is_google_genai_model(self, model_key: str) -> bool:
        model_cfg = MODELS.get(model_key, {})
        sdk = model_cfg.get("sdk", "")
        model_id = str(model_cfg.get("id", ""))
        provider_key = model_cfg.get("provider", "google")
        if sdk == "google-genai" or model_id.startswith("gemini-4") or model_id.startswith("gemini-3.8"):
            return True
        try:
            from .config import PROVIDERS
        except ImportError:
            from config import PROVIDERS
        prov_cfg = PROVIDERS.get(provider_key, {})
        return prov_cfg.get("sdk") == "google-genai"

    def _get_genai_client(self, api_key: str):
        """Instantiate google-genai Client for the given API key."""
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError("google-genai package required: pip install google-genai") from exc
        return genai.Client(api_key=api_key)

    def _get_client_for_model(self, model_key: str):
        """Lazily resolve the SDK client for a specific model slot/provider."""
        model_cfg = MODELS[model_key]
        provider_key = model_cfg.get("provider", "google")

        try:
            from .config import PROVIDERS
        except ImportError:
            from config import PROVIDERS

        prov_cfg = PROVIDERS.get(provider_key)
        if not prov_cfg:
            raise ValueError(f"Unknown provider '{provider_key}' for model slot '{model_key}'.")

        if self._is_google_genai_model(model_key):
            cache_key = f"{provider_key}:google-genai"
            if cache_key in self._clients:
                return self._clients[cache_key]
            if provider_key in self._clients:
                return self._clients[provider_key]

            env_var = prov_cfg.get("env_var", "GEMINI_API_KEY")
            fallback_env_var = prov_cfg.get("fallback_env_var", "GOOGLE_API_KEY")
            api_key = (
                os.environ.get(env_var)
                or os.environ.get(fallback_env_var)
                or os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
            )
            if not api_key:
                raise EnvironmentError(
                    f"API key for provider '{provider_key}' ({env_var} or {fallback_env_var}) not found in environment."
                )

            client = self._get_genai_client(api_key)
            self._clients[cache_key] = client
            self._clients[provider_key] = client
            return client

        if provider_key in self._clients:
            return self._clients[provider_key]

        # Lazy-import openai to avoid top-level dependency
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package required: pip install openai"
            )

        env_var = prov_cfg.get("env_var", "")
        api_key = os.environ.get(env_var)

        # Fallback for github token name variations
        if provider_key == "github" and not api_key:
            api_key = (
                os.environ.get("GITHUB_TOKEN")
                or os.environ.get("GITHUB_MODELS_TOKEN")
                or os.environ.get("GH_TOKEN")
            )
        elif provider_key == "google" and not api_key:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if not api_key:
            raise EnvironmentError(
                f"API key for provider '{provider_key}' ({env_var}) not found in environment. "
                f"Please define it in your .env file."
            )

        endpoint = prov_cfg.get("endpoint", "")
        # For google provider using OpenAI compatibility layer
        if provider_key == "google" and "generativelanguage.googleapis.com" in endpoint:
            if "/v1beta/openai" not in endpoint and "/v1/openai" not in endpoint:
                endpoint = endpoint.rstrip("/") + "/v1beta/openai"

        client = OpenAI(
            base_url=endpoint,
            api_key=api_key,
        )
        self._clients[provider_key] = client
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
        
        # Daily cost check
        daily_cost = load_daily_cost() + self.session_cost_usd
        if daily_cost >= self.budget["max_cost_per_day_usd"]:
            return False, f"daily cost cap reached (${daily_cost:.2f})"
            
        # Per-minute calls circuit breaker
        max_min_calls = self.budget.get("max_calls_per_minute", 10)
        recent_calls = load_recent_calls_count(60)
        if recent_calls >= max_min_calls:
            return False, f"rate limit: too many calls in the last minute ({recent_calls}/{max_min_calls})"
            
        # Per-day calls circuit breaker
        max_day_calls = self.budget.get("max_calls_per_day", 100)
        daily_calls = load_daily_calls_count()
        if daily_calls >= max_day_calls:
            return False, f"rate limit: too many calls today ({daily_calls}/{max_day_calls})"
            
        return True, "OK"

    # ------------------------------------------------------------------
    # Core completion
    # ------------------------------------------------------------------

    def _call_gemini_interactions(
        self,
        client: Any,
        messages: list[dict],
        model_key: str,
        max_tokens: int,
        json_mode: bool = False,
        schema: dict | None = None,
        thinking_level: str | None = None,
        previous_interaction_id: str | None = None,
        background: bool = False,
        poll_interval_s: float = 0.5,
        max_wait_s: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_dispatcher: Any | None = None,
        max_tool_rounds: int = 2,
    ) -> LLMResponse:
        """Call Google Gemini Interactions API (`client.interactions.create`) for gemini-4-argon."""
        model_cfg = MODELS[model_key]
        model_id = model_cfg["id"]
        effective_thinking = thinking_level or model_cfg.get("thinking_level", "high")
        # gemini-4-argon requires max_output_tokens >= 32768 so reasoning tokens never starve JSON output
        effective_max_tokens = max(
            int(max_tokens or 32768),
            int(model_cfg.get("max_output_tokens", 32768)),
            32768 if model_id.startswith("gemini-4") else 4096,
        )

        system_parts: list[str] = []
        user_parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))
            if role == "system":
                if content.strip():
                    system_parts.append(content)
            else:
                user_parts.append(content)

        system_instruction = "\n\n".join(system_parts).strip()
        user_input = "\n\n".join(user_parts).strip() or "Proceed."

        response_format: dict[str, Any] | None = None
        if json_mode:
            fmt: dict[str, Any] = {
                "type": "text",
                "mime_type": "application/json",
            }
            schema_dict = (
                schema.model_json_schema()
                if schema is not None and hasattr(schema, "model_json_schema")
                else schema
            )
            if isinstance(schema_dict, dict) and schema_dict.get("type") == "object" and "properties" in schema_dict:
                fmt["schema"] = schema_dict
            response_format = fmt

        timeout_sec = float(max_wait_s if max_wait_s is not None else self.budget.get("timeout_sec", 120))
        telemetry = run_gemini_interaction_with_tools(
            client=client,
            model=model_id,
            input_payload=user_input,
            system_instruction=system_instruction,
            thinking_level=effective_thinking,
            max_output_tokens=effective_max_tokens,
            previous_interaction_id=previous_interaction_id,
            tools=tools,
            tool_dispatcher=tool_dispatcher,
            max_tool_rounds=max_tool_rounds,
            response_format=response_format,
            background=background,
            poll_interval_s=poll_interval_s,
            max_wait_s=timeout_sec,
        )
        return LLMResponse(
            content=telemetry["content"],
            model=model_id,
            role=model_key,
            input_tokens=telemetry["input_tokens"],
            output_tokens=telemetry["output_tokens"],
            thought_tokens=telemetry["thought_tokens"],
            cached_input_tokens=telemetry["cached_input_tokens"],
            interaction_id=telemetry["interaction_id"],
            previous_interaction_id=previous_interaction_id or "",
            thinking_level=effective_thinking,
            thought_step_count=telemetry["thought_step_count"],
            thought_summaries=telemetry["thought_summaries"],
            thought_signature_digests=telemetry["thought_signature_digests"],
            function_calls=telemetry["function_calls"],
            tool_executions=telemetry["tool_executions"],
            success=True,
        )

    def _call_model(
        self,
        messages: list[dict],
        model_key: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool = False,
        schema: dict | None = None,
        thinking_level: str | None = None,
        previous_interaction_id: str | None = None,
        background: bool = False,
        poll_interval_s: float = 0.5,
        max_wait_s: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_dispatcher: Any | None = None,
        max_tool_rounds: int = 2,
    ) -> LLMResponse:
        """Call a specific model and return a response."""
        model_cfg = MODELS[model_key]
        model_id = model_cfg["id"]
        is_reasoning = model_cfg.get("is_reasoning", False)

        response = LLMResponse(
            model=model_id,
            role=model_key,
            previous_interaction_id=previous_interaction_id or "",
            thinking_level=thinking_level or model_cfg.get("thinking_level", ""),
        )

        t0 = time.time()
        try:
            client = self._get_client_for_model(model_key)

            if self._is_google_genai_model(model_key) and hasattr(client, "interactions"):
                response = self._call_gemini_interactions(
                    client=client,
                    messages=messages,
                    model_key=model_key,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    schema=schema,
                    thinking_level=thinking_level,
                    previous_interaction_id=previous_interaction_id,
                    background=background,
                    poll_interval_s=poll_interval_s,
                    max_wait_s=max_wait_s,
                    tools=tools,
                    tool_dispatcher=tool_dispatcher,
                    max_tool_rounds=max_tool_rounds,
                )
            else:
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

                result = client.chat.completions.create(**kwargs)

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

        # Compute cost (accounting for 95% implicit cache discount on cached_input_tokens)
        uncached_in = max(0, response.input_tokens - response.cached_input_tokens)
        cached_in = max(0, response.cached_input_tokens)
        in_cost = (
            (uncached_in / 1000.0) * model_cfg["cost_per_1k_input"]
            + (cached_in / 1000.0) * model_cfg["cost_per_1k_input"] * 0.05
        )
        out_cost = ((response.output_tokens + response.thought_tokens) / 1000.0) * model_cfg["cost_per_1k_output"]
        response.cost_usd = round(in_cost + out_cost, 6)

        return response

    def complete(
        self,
        prompt: str,
        system: str = "",
        task: str = "general",
        temperature: float | None = None,
        max_tokens: int | None = None,
        thinking_level: str | None = None,
        previous_interaction_id: str | None = None,
        background: bool = False,
        slot: str | None = None,
        poll_interval_s: float = 0.5,
        max_wait_s: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_dispatcher: Any | None = None,
        max_tool_rounds: int = 2,
    ) -> LLMResponse:
        """
        Send a prompt to the LLM with automatic fallback.
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

        extra_kwargs: dict[str, Any] = {}
        if thinking_level is not None:
            extra_kwargs["thinking_level"] = thinking_level
        if previous_interaction_id is not None:
            extra_kwargs["previous_interaction_id"] = previous_interaction_id
        if background:
            extra_kwargs["background"] = background
            extra_kwargs["poll_interval_s"] = poll_interval_s
            if max_wait_s is not None:
                extra_kwargs["max_wait_s"] = max_wait_s
        if tools is not None:
            extra_kwargs["tools"] = tools
            extra_kwargs["tool_dispatcher"] = tool_dispatcher
            extra_kwargs["max_tool_rounds"] = max_tool_rounds

        primary_slot = slot if (slot and slot in MODELS) else "primary"
        # Try requested/primary slot
        response = self._try_with_retries(messages, primary_slot, max_tok, temp, **extra_kwargs)

        # Fallback if primary failed
        if not response.success and primary_slot != "fallback":
            if self.verbose:
                print(f"    [LLM] Primary failed, trying fallback...")
            response = self._try_with_retries(messages, "fallback", max_tok, temp, **extra_kwargs)

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
        schema: Any | None = None,
        task: str = "general",
        temperature: float | None = None,
        max_tokens: int | None = None,
        slot: str | None = None,
        thinking_level: str | None = None,
        previous_interaction_id: str | None = None,
        background: bool = False,
        poll_interval_s: float = 0.5,
        max_wait_s: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_dispatcher: Any | None = None,
        max_tool_rounds: int = 2,
    ) -> LLMResponse:
        """
        Request structured JSON output from the LLM.

        If a schema is provided, it's included in the system prompt as
        guidance and passed to Gemini's structured output schema when applicable.
        The response is parsed into response.parsed.
        """
        schema_dict = (
            schema.model_json_schema()
            if schema is not None and hasattr(schema, "model_json_schema")
            else schema
        )
        schema_instruction = ""
        if isinstance(schema_dict, dict):
            schema_instruction = (
                "\n\nRespond with a JSON object matching this schema:\n"
                f"```json\n{json.dumps(schema_dict, indent=2)}\n```\n"
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

        extra_kwargs: dict[str, Any] = {}
        if schema_dict is not None:
            extra_kwargs["schema"] = schema_dict
        if thinking_level is not None:
            extra_kwargs["thinking_level"] = thinking_level
        if previous_interaction_id is not None:
            extra_kwargs["previous_interaction_id"] = previous_interaction_id
        if background:
            extra_kwargs["background"] = background
            extra_kwargs["poll_interval_s"] = poll_interval_s
            if max_wait_s is not None:
                extra_kwargs["max_wait_s"] = max_wait_s
        if tools is not None:
            extra_kwargs["tools"] = tools
            extra_kwargs["tool_dispatcher"] = tool_dispatcher
            extra_kwargs["max_tool_rounds"] = max_tool_rounds

        primary_slot = slot if (slot and slot in MODELS) else "primary"
        # Try primary/requested slot with JSON mode
        response = self._try_with_retries(messages, primary_slot, max_tok, temp, json_mode=True, **extra_kwargs)
        if not response.success and primary_slot != "fallback":
            if self.verbose:
                print(f"    [LLM] Primary JSON failed, trying fallback...")
            response = self._try_with_retries(messages, "fallback", max_tok, temp, json_mode=True, **extra_kwargs)


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
                response.parsed = json.loads(text.strip())
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
        **extra_kwargs: Any,
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

            if extra_kwargs:
                response = self._call_model(messages, model_key, max_tokens, temperature, json_mode, **extra_kwargs)
            else:
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
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GITHUB_MODELS_TOKEN")
            or os.environ.get("GH_TOKEN")
            or os.environ.get("OPENAI_API_KEY")
        )

