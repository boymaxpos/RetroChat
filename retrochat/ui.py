"""Static 7-bit ASCII presentation for the Windows 98 terminal."""

from __future__ import annotations


UI_WIDTH = 72


def _box(lines: list[str]) -> str:
    """Build a fixed-width ASCII box and reject accidental overflow."""
    inner_width = UI_WIDTH - 2
    if any(len(line) > inner_width for line in lines):
        raise ValueError("RetroChat UI line exceeds the terminal width.")
    border = "+" + ("-" * inner_width) + "+"
    body = ["|" + line.ljust(inner_width) + "|" for line in lines]
    return "\n".join([border, *body, border])


BANNER = _box(
    [
        "",
        "   ____      _              ____ _           _",
        r"  |  _ \ ___| |_ _ __ ___ / ___| |__   __ _| |_",
        r"  | |_) / _ \ __| '__/ _ \ |   | '_ \ / _` | __|",
        r"  |  _ <  __/ |_| | | (_) | |___| | | | (_| | |_",
        r"  |_| \_\___|\__|_|  \___/ \____|_| |_|\__,_|\__|",
        "",
        "  VERSION 0.1  |  MAC GATEWAY ONLINE  |  WINDOWS 98 TERMINAL",
        "",
    ]
) + "\n\nCommands: /help  /new  /exit"


HELP_TEXT = _box(
    [
        "",
        "  RETROCHAT COMMANDS",
        "",
        "  /help     Show this command list",
        "  /new      Start a new conversation",
        "  /exit     Close RetroChat",
        "",
        "  Ctrl+C    Stop the current response",
        "  Ctrl+D    Close the connection",
        "",
    ]
)
