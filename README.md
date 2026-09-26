# RetroChat

RetroChat will provide a plain-text ChatGPT conversation terminal for a
Windows 98 computer connected to a Mac mini over SSH.

This repository is currently at Phase 4. It provides a plain-text interactive
CLI with streamed replies, conversation context, `/help`, `/new`, and `/exit`.
All output passes through a terminal adapter that replaces incompatible Unicode
symbols and removes terminal control sequences while preserving Chinese text.
RetroChat reuses the existing Codex ChatGPT login and does not use an API key.

## Current architecture

```text
RetroChat CLI
  |
  v
ChatBackend
  |
  v
CodexBackend
  |
  | JSONL over stdio
  v
Codex App Server
  |
  | existing ChatGPT authentication
  v
OpenAI model
```

## Requirements

- macOS 27.0 on Apple Silicon
- Python 3.14.7 (`/opt/homebrew/bin/python3`)
- Codex CLI 0.155.1
- An existing ChatGPT login reported by `codex login status`

## Run RetroChat

```sh
python3 retrochat.py
```

Available commands:

```text
/help - Show commands
/new  - New conversation
/exit - Exit RetroChat
```

Ctrl+C while the model is responding stops the current generation. Ctrl+C at
the input prompt keeps RetroChat open and points to `/exit`. Ctrl+D exits.

Run the offline unit tests:

```sh
python3 -m unittest discover -s tests -v
```

## Terminal compatibility

The Phase 4 adapter converts common bullets, arrows, status marks, smart quotes,
dashes, emoji, and box-drawing characters to ASCII-safe equivalents. It also
normalizes line endings and removes ANSI and unsafe control characters. It does
not yet perform UTF-8/CP936 byte encoding; that remains part of the later
Chinese terminal phase.

## Phase 4 security limits

The PoC uses an ephemeral Codex thread, a temporary working directory,
read-only sandboxing, disabled sandbox network access, and an approval policy
of `never`. It also rejects server-initiated tool requests. Codex remains an
agent runtime, so stronger OS-level isolation is still required before exposing
RetroChat as a restricted SSH login.

## Source layout

- `retrochat/backend.py` - backend interface and user-facing backend errors
- `retrochat/app.py` - asynchronous plain-text command loop
- `retrochat/commands.py` - ASCII slash-command parser
- `retrochat/codex_protocol.py` - concurrent JSONL App Server transport
- `retrochat/codex_backend.py` - conversation and streaming implementation
- `retrochat/prompts.py` - terminal-oriented model instructions
- `retrochat/terminal.py` - terminal-safe text normalization and output
- `retrochat.py` - CLI entry point

## Not implemented yet

- Configurable UTF-8/CP936 terminal encoding
- SSH integration or macOS Remote Login configuration
- Windows 98 testing
