# Swap LLM Models

Use this prompt when you need to update SOL's LLM model configuration — e.g. when new models become available, you get new API credits, or need to switch providers.

## Quick reference

| Action | Command |
|--------|---------|
| Show current config | `python tools/sol-llm/update_models.py show` |
| Swap a model | `python tools/sol-llm/update_models.py set <slot> <model-id>` |
| Scan for available models | `python tools/sol-llm/update_models.py scan` |
| Test all models | `python tools/sol-llm/update_models.py test` |
| See change history | `python tools/sol-llm/update_models.py history` |
| Rollback last change | `python tools/sol-llm/update_models.py rollback <slot>` |
| Add a provider | `python tools/sol-llm/update_models.py add-provider <key> --endpoint <url> --env-var <VAR>` |

## Slots

- **primary** — main model for general tasks (hypothesis, interpretation, claims)
- **fallback** — cheaper/faster model used when primary fails
- **reasoning** — specialized reasoning model (o-series, DeepSeek-R1, etc.)

## Workflow

1. User tells you what model(s) they want to use or that new credits are available
2. Run `show` to see current state
3. If unsure what's available, run `scan` to probe the API
4. Run `set <slot> <model-id>` with appropriate flags
5. Run `test` to verify connectivity
6. Report results to user

## Examples

```bash
# User says "switch SOL to Modal GLM-5"
python tools/sol-llm/update_models.py add-provider modal_glm5 --endpoint https://api.us-west-2.modal.direct/v1 --env-var MODAL_API_KEY
python tools/sol-llm/update_models.py set primary zai-org/GLM-5-FP8 --provider modal_glm5 --name "GLM-5 FP8"
python tools/sol-llm/update_models.py set fallback zai-org/GLM-5-FP8 --provider modal_glm5 --name "GLM-5 FP8"
python tools/sol-llm/update_models.py set reasoning zai-org/GLM-5-FP8 --provider modal_glm5 --name "GLM-5 FP8" --reasoning False
python tools/sol-llm/update_models.py test

# User says "I got Claude 4.6 credits"
python tools/sol-llm/update_models.py add-provider anthropic --endpoint https://api.anthropic.com --env-var ANTHROPIC_API_KEY
python tools/sol-llm/update_models.py set primary claude-4.6 --provider anthropic --name "Claude 4.6"
python tools/sol-llm/update_models.py test

# User says "switch primary to gpt-5.3-codex"
python tools/sol-llm/update_models.py set primary gpt-5.3-codex --reason "upgraded to codex variant"
python tools/sol-llm/update_models.py test

# User says "that broke things, go back"
python tools/sol-llm/update_models.py rollback primary
python tools/sol-llm/update_models.py test
```

## Config file

All model config lives in `tools/sol-llm/models.json`. The CLI tool edits this file. You can also edit the JSON directly if preferred — `config.py` reads from it at import time.

## Notes

- Reasoning models (o-series, gpt-5 non-chat) are auto-detected and use `max_completion_tokens` instead of `max_tokens`, and skip `temperature`.
- The `scan` command tries ~50 model IDs against the API. Run it periodically to discover new models.
- All swaps are logged in `models.json → history` for audit and rollback.
- Multiple providers are supported (Modal, Anthropic, Google, OpenAI direct). Each uses its own env var for the API key.
- If your provider allows only one concurrent request, keep one SOL run using LLM at a time (client-side single-flight lock is enabled).
