---
description: Update repo-backed continuity memory at chat end
---

Workflow:
1. Write a short session note (what changed, what we decided, what’s next).
2. Append it to `knowledge/continuity/session_notes.jsonl`.
3. If any durable facts changed (goals, constraints, architecture decisions), update `knowledge/continuity/project_memory.md`.

Session note JSON shape (example):
{"ts":"2026-01-26T00:00:00+00:00","title":"...","note":"...","tags":["..."],"source":"vscode-chat"}
