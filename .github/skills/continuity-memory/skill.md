name: Continuity Memory
description: Repo-backed continuity across VS Code chats (durable memory + session notes).

Workflow:
1. Ensure `knowledge/continuity/` exists and is initialized.
2. At chat start, read `knowledge/continuity/project_memory.md`.
3. At chat end, append a session note to `knowledge/continuity/session_notes.jsonl`.

References:
- tools/continuity/continuity_cli.py
- tools/continuity/continuity_end_of_chat.ps1
- scripts/init_continuity.ps1
- scripts/end_of_chat.ps1
- templates/session_note_template.json
- templates/project_memory_template.md
