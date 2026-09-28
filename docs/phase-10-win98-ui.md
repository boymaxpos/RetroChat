# Phase 10 Windows 98 ASCII interface

Status: implemented and locally verified; physical PuTTY verification pending.

## Design target

The reference Toshiba/PuTTY 0.77 screen provides a fixed-pitch terminal of
about 80 columns with reliable basic ASCII rendering. The interface therefore
uses a 72-column layout so the right border has room before PuTTY's wrapping
boundary.

The interface deliberately uses only printable 7-bit ASCII:

- `+`, `-`, and `|` for frames
- letters, digits, spaces, slash, underscore, and backslash for the logo
- no ANSI colors or cursor movement
- no Unicode box-drawing characters
- no terminal-size query or client-specific escape sequence

This keeps the display stable on Windows 98 even when font and character-set
support differ from modern terminals.

## Login screen

```text
+----------------------------------------------------------------------+
|                                                                      |
|   ____      _              ____ _           _                        |
|  |  _ \ ___| |_ _ __ ___ / ___| |__   __ _| |_                       |
|  | |_) / _ \ __| '__/ _ \ |   | '_ \ / _` | __|                      |
|  |  _ <  __/ |_| | | (_) | |___| | | | (_| | |_                      |
|  |_| \_\___|\__|_|  \___/ \____|_| |_|\__,_|\__|                     |
|                                                                      |
|  VERSION 0.1  |  MAC GATEWAY ONLINE  |  WINDOWS 98 TERMINAL          |
|                                                                      |
+----------------------------------------------------------------------+

Commands: /help  /new  /exit
You>
```

`/help` displays a matching fixed-width command panel. Normal prompts and
streamed model output remain unchanged.

## Deployment

Exit every RetroChat session, then run locally on the Mac:

```sh
sudo /Users/boymax/Documents/Projects/RetroChat/scripts/deploy-phase10-ui.sh
```

The script validates every staged Python module, checks that the banner and
help panel are ASCII and within 72 columns, backs up the current runtime, and
replaces only the RetroChat Python package and launcher. It does not change SSH
policy, users, passwords, Codex credentials, or the Codex executable.

## Physical acceptance checklist

- The right border is visible and no logo line wraps.
- Backslashes and underscores in the logo are distinct.
- `MAC GATEWAY ONLINE` is readable.
- `/help` shows a complete aligned frame.
- An English prompt produces a streamed reply.
- `/new`, Ctrl+C, Ctrl+D, and `/exit` retain their existing behavior.
