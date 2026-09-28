# RetroChat

RetroChat turns a Windows 98 PC into a plain-text ChatGPT terminal. The PC
connects to a Mac mini over SSH with PuTTY, and the Mac runs a restricted
RetroChat service backed by Codex and an account-local ChatGPT login.

The project is designed for old terminals: the interface is English-only,
uses printable 7-bit ASCII, and does not require ANSI color, Unicode, cursor
positioning, terminal detection, or extra client software beyond PuTTY.

```text
+----------------------------------------------------------------------+
|                                                                      |
|   ____      _              ____ _           _                       |
|  |  _ \ ___| |_ _ __ ___ / ___| |__   __ _| |_                     |
|  | |_) / _ \ __| '__/ _ \ |   | '_ \ / _` | __|                    |
|  |  _ <  __/ |_| | | (_) | |___| | | | (_| | |_                    |
|  |_| \_\___|\__|_|  \___/ \____|_| |_|\__,_|\__|                    |
|                                                                      |
|  VERSION 0.1  |  MAC GATEWAY ONLINE  |  WINDOWS 98 TERMINAL         |
|                                                                      |
+----------------------------------------------------------------------+

Commands: /help  /new  /exit
```

## Features

- Streaming ChatGPT responses in a simple interactive terminal
- Conversation context with `/new` to start over
- Fixed-width RetroChat logo and framed help screen for PuTTY 0.77
- Automatic conversion of common Unicode punctuation and symbols to ASCII
- Removal of ANSI escape sequences and unsafe terminal control characters
- Dedicated hidden macOS account with a forced RetroChat command
- SSH restrictions that disable SFTP, forwarding, user RC files, and extra
  sessions
- No OpenAI API key required

## How it works

```text
Windows 98 + PuTTY
        |
        | SSH
        v
Restricted macOS account
        |
        v
RetroChat CLI
        |
        v
Codex App Server
        |
        v
OpenAI model
```

RetroChat communicates with the Codex App Server over JSONL on standard I/O.
The deployed service uses the ChatGPT login belonging to the restricted
`retrochat` macOS account. Credentials are stored only on the Mac mini and
must be protected like a password.

## Requirements

- A Mac mini running macOS on Apple Silicon
- Python 3.14 or later
- Codex CLI 0.155.1 or a compatible release
- A ChatGPT login for the macOS account that runs RetroChat
- A Windows 98 computer with PuTTY 0.77 or another compatible SSH client
- A trusted local network

The currently validated host uses macOS 27.0 and Python 3.14.7 at
`/opt/homebrew/bin/python3`.

## Run from the source tree

```sh
python3 retrochat.py
```

RetroChat looks for Codex on `PATH`, in the usual per-user installation
location, and inside the ChatGPT/Codex macOS application bundle. To select a
specific executable, set `RETROCHAT_CODEX` to its absolute path.

Available commands:

```text
/help - Show commands
/new  - Start a new conversation
/exit - Exit RetroChat
```

While a response is streaming, `Ctrl+C` stops the current response. At the
input prompt, `Ctrl+C` keeps RetroChat open and points to `/exit`. `Ctrl+D`
closes the session.

Run the offline test suite with:

```sh
python3 -m unittest discover -s tests -v
```

## Mac mini deployment

The hardened installation runs under a hidden, non-admin macOS account named
`retrochat`. Every SSH login is forced directly into RetroChat instead of a
general-purpose shell.

The deployed components are:

- Runtime and fixed Codex executable: `/usr/local/libexec/retrochat`
- Forced login launcher: `/usr/local/bin/retrochat-login`
- OpenSSH restriction: `/etc/ssh/sshd_config.d/200-retrochat.conf`
- Account-local Codex data: `/Users/retrochat/.codex`

Installation, verification, access finalization, UI deployment, and cleanup
utilities are provided under `scripts/`. Root-owned launcher and SSH policy
templates are under `deploy/`, with design and test notes under `docs/`.

macOS privacy controls prevent an SSH process without Full Disk Access from
reading a checkout under `~/Documents`. The deployment avoids granting that
broad permission by copying a root-owned runtime into `/usr/local/libexec`.

## Windows 98 and PuTTY

Connect to the Mac mini with the `retrochat` username. Password and
keyboard-interactive authentication remain available for the legacy client.
The interface is sized for a 72-column terminal and uses ASCII borders rather
than Unicode box-drawing characters.

Recommended PuTTY settings:

- Use SSH with a terminal window at least 72 columns wide
- Use an English-capable fixed-width font
- Keep the session on a trusted LAN
- Use the verified Mac host-key fingerprint when accepting the server

Chinese input and localization are intentionally outside the current project
scope. The terminal adapter keeps model output compatible with the English
Windows 98 client.

## Security model

The service combines operating-system separation with a restricted Codex
runtime:

- The SSH account is hidden, non-admin, and dedicated to RetroChat
- A forced command prevents interactive shell access
- SFTP, TCP forwarding, agent forwarding, X11 forwarding, user RC files, and
  additional SSH sessions are disabled
- Codex runs in a private temporary directory with read-only sandboxing,
  disabled sandbox network access, and an approval policy of `never`
- Server-initiated tool requests are rejected
- The account has no Secure Token or APFS volume ownership

These controls reduce risk but do not make the service suitable for exposure
to the public internet while password login is enabled. Run it only on a
trusted network or add a properly managed VPN and stronger authentication.

## Verified behavior

The following behavior has been tested end to end:

- A Windows 98 PuTTY client can connect and hold an English conversation
- Model responses stream through a real SSH pseudo-terminal
- `/help`, `/new`, `/exit`, `Ctrl+C`, and `Ctrl+D` behave as documented
- Unicode and terminal control sequences are converted or removed safely
- Requested shell commands start RetroChat instead of executing the command
- SFTP and SSH port forwarding are rejected
- `/exit` closes the SSH session cleanly
- FileVault remains enabled for the primary macOS user

The redesigned ASCII banner and help screen are implemented and covered by
offline tests. Deploying that interface to the root-owned runtime and checking
its final appearance on the physical Windows 98 display remain the next
on-device tasks.

## Repository layout

- `retrochat/app.py` - asynchronous command loop
- `retrochat/backend.py` - backend interface and user-facing errors
- `retrochat/codex_backend.py` - conversation and streaming implementation
- `retrochat/codex_protocol.py` - concurrent JSONL App Server transport
- `retrochat/commands.py` - slash-command parser
- `retrochat/prompts.py` - terminal-oriented model instructions
- `retrochat/terminal.py` - terminal-safe text normalization
- `retrochat/ui.py` - fixed-width ASCII banner and help screen
- `retrochat.py` - command-line entry point
- `deploy/` - launcher, Codex configuration, and SSH policy templates
- `scripts/` - installation, deployment, verification, and cleanup tools
- `docs/` - security design, interface notes, and physical test procedures
- `tests/` - offline unit tests
