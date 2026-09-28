# RetroChat

RetroChat will provide a plain-text ChatGPT conversation terminal for a
Windows 98 computer connected to a Mac mini over SSH.

This repository has completed Phase 7. It provides a plain-text interactive
CLI with streamed replies, conversation context, `/help`, `/new`, and `/exit`.
All output passes through a terminal adapter that replaces incompatible Unicode
symbols and removes terminal control sequences while preserving Chinese text.
The deployed service uses an independent Codex ChatGPT login owned by the
restricted `retrochat` account and does not use an API key.

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
  | account-local ChatGPT authentication
  v
OpenAI model
```

## Requirements

- macOS 27.0 on Apple Silicon
- Python 3.14.7 (`/opt/homebrew/bin/python3`)
- Codex CLI 0.155.1
- A ChatGPT login for the account that runs RetroChat

## Run RetroChat

```sh
python3 retrochat.py
```

RetroChat finds Codex on `PATH`, in the usual per-user installation location,
or inside the ChatGPT/Codex macOS application bundle. To select an installation
explicitly, set `RETROCHAT_CODEX` to the absolute Codex executable path.

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

## Phase 5 local SSH validation

The CLI has been exercised end to end through an isolated OpenSSH server bound
only to localhost. This confirmed that an SSH session can start RetroChat and
reach its command loop without changing macOS Remote Login settings. Phase 5
also added Codex executable discovery for the minimal `PATH` commonly supplied
to non-interactive SSH sessions.

During Phase 5, the Mac's system Remote Login service was not enabled or
modified. Permanent OpenSSH/macOS integration was completed in Phase 6.

## Phase 6 macOS SSH integration

macOS Remote Login is enabled using the system OpenSSH 10.3 service. Access is
limited to the `boymax` account, and "Allow remote users full disk access" is
disabled. No changes were made to `/etc/ssh/sshd_config`, the firewall, system
security policy, or launchd configuration.

The macOS application firewall was disabled during verification. Remote Login
was therefore kept on the trusted local network while Phase 7 added the
dedicated account and access controls.

An end-to-end test connected to the Mac's LAN address over port 22, allocated a
PTY, started RetroChat, reached Codex through the existing ChatGPT login, and
received a live model response. The temporary SSH test key and temporary app
copy used for this verification were removed after the test.

macOS privacy controls prevent an SSH process without full disk access from
reading this checkout under `~/Documents`. RetroChat should not solve this by
granting broad disk access. Phase 7 instead deployed a root-owned runtime under
`/usr/local/libexec` and restricted a dedicated `retrochat` account. The Mac's
LAN address observed during Phase 6 was `192.168.31.39`; it may change unless
the router reserves it.

## Phase 7 restricted account

Phase 7 deploys RetroChat as a dedicated, hidden, non-admin macOS account named
`retrochat`. Remote Login is limited to that account; `boymax` is no longer in
the SSH allow-list. A root-owned launcher forces every SSH session directly
into RetroChat, while the per-user OpenSSH policy disables forwarding, SFTP,
user RC files, and additional sessions.

The installed runtime is root-owned at `/usr/local/libexec/retrochat`, including
a fixed Codex CLI copy. The launcher is `/usr/local/bin/retrochat-login`, and
the SSH restriction is `/etc/ssh/sshd_config.d/200-retrochat.conf`. Codex
credentials remain under `/Users/retrochat/.codex` with file-backed credential
storage and must be treated like a password.

Verification confirmed all of the following:

- A requested shell command starts RetroChat instead of executing the command.
- SFTP and SSH port forwarding fail.
- A real SSH/PTY conversation returned `PHASE7_OK` from the model.
- `/exit` closes the SSH session cleanly.
- The temporary verification public key was removed after testing.
- Password and keyboard-interactive authentication remain available for the
  future Windows 98/PuTTY client.
- The automatically granted Secure Token and APFS volume ownership were removed
  from `retrochat`; FileVault remains enabled for the primary user.

The installation, verification, finalization, and cleanup scripts are under
`scripts/`. The deployed policy and launcher templates are under `deploy/`.

## Security limits

The PoC uses an ephemeral Codex thread, a private temporary working directory,
read-only sandboxing, disabled sandbox network access, and an approval policy
of `never`. It also rejects server-initiated tool requests. The dedicated
account and forced SSH command provide OS-level separation, but the service
should still be exposed only to a trusted LAN while password login is enabled.

## Source layout

- `retrochat/backend.py` - backend interface and user-facing backend errors
- `retrochat/app.py` - asynchronous plain-text command loop
- `retrochat/commands.py` - ASCII slash-command parser
- `retrochat/codex_protocol.py` - concurrent JSONL App Server transport
- `retrochat/codex_backend.py` - conversation and streaming implementation
- `retrochat/prompts.py` - terminal-oriented model instructions
- `retrochat/terminal.py` - terminal-safe text normalization and output
- `retrochat.py` - CLI entry point
- `deploy/` - root-owned launcher, Codex config, and per-user SSH policy
- `scripts/` - Phase 7 installation, verification, finalization, and cleanup
- `docs/phase-7-security-design.md` - deployed security design and audit record

## Not implemented yet

- Configurable UTF-8/CP936 terminal encoding
- Windows 98 testing
- PuTTY public-key enrollment and optional public-key-only authentication
