# Continuity (Repo-Backed Memory)

VS Code chat threads do not automatically share global chat history.
This tool provides a lightweight, repo-backed memory so you can carry context across sessions.

## Files
- `knowledge/continuity/project_memory.md` — curated durable context (what/why/state/constraints/next steps)
- `knowledge/continuity/session_notes.jsonl` — append-only timestamped notes (JSONL)
- `knowledge/continuity/snapshots/` — optional snapshots of prior generated `project_memory.md`
- `knowledge/continuity/chat_transcripts/` — optional saved transcripts (clipboard capture)

## Quick start
1. Initialize files:
   - `python tools/continuity/continuity_cli.py init`
2. Add a note:
   - `python tools/continuity/continuity_cli.py add --title "What we did" --note "..." --tags "continuity,setup"`
   - Or run the interactive helper: `./tools/continuity/continuity_end_of_chat.ps1`
3. Search notes:
   - `python tools/continuity/continuity_cli.py search "keyword"`
4. Show latest notes:
   - `python tools/continuity/continuity_cli.py tail --limit 10`

## Suggested workflow
- Start of a new chat: open/read `knowledge/continuity/project_memory.md`.
- End of a chat: append a short entry to `session_notes.jsonl`, then optionally update `project_memory.md` with any durable changes.

### Automation
- VS Code Task: **Continuity: Auto Note (End of Chat)**
   - Runs a non-interactive note capture, refreshes `project_memory.md` with more history, writes a snapshot before overwriting, and closes the task terminal when done.
- Workspace shortcut (in `.vscode/keybindings.json`): `Ctrl+Alt+N`

### Snapshots

When `refresh` runs with `--snapshot`, it writes the previous version of `knowledge/continuity/project_memory.md` to:
- `knowledge/continuity/snapshots/`

This guards against accidental loss of older generated context.

### Including the current chat transcript

`tools/continuity/continuity_auto_note.ps1` can optionally include a transcript from your clipboard.

- Default mode is `ClipboardMode=auto` (only includes clipboard when it looks like multi-line text)
- You can force behavior with `-ClipboardMode always` or disable with `-ClipboardMode never`
- If the clipboard content is large, the script saves the full transcript to `knowledge/continuity/chat_transcripts/` and includes a preview in the note
