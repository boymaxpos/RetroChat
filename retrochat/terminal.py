"""Output adaptation for old plain-text terminals."""

from __future__ import annotations

import re
import sys
from typing import TextIO


_ANSI_ESCAPE = re.compile(
    r"(?:\x1B\][^\x07\x1B]*(?:\x07|\x1B\\))"
    r"|(?:\x1B[@-_][0-?]*[ -/]*[@-~])"
)

_UNICODE_REPLACEMENTS = str.maketrans(
    {
        "•": "*",
        "‣": "*",
        "◦": "*",
        "→": "->",
        "⇒": "->",
        "⟶": "->",
        "←": "<-",
        "⇐": "<-",
        "⟵": "<-",
        "✓": "[OK]",
        "✔": "[OK]",
        "✅": "[OK]",
        "☑": "[OK]",
        "✗": "[X]",
        "✘": "[X]",
        "❌": "[X]",
        "—": "-",
        "–": "-",
        "−": "-",
        "“": '"',
        "”": '"',
        "„": '"',
        "«": '"',
        "»": '"',
        "‘": "'",
        "’": "'",
        "‚": "'",
        "…": "...",
        " ": " ",
        "─": "-",
        "━": "-",
        "═": "-",
        "│": "|",
        "┃": "|",
        "║": "|",
        "┌": "+",
        "┐": "+",
        "└": "+",
        "┘": "+",
        "├": "+",
        "┤": "+",
        "┬": "+",
        "┴": "+",
        "┼": "+",
        "╔": "+",
        "╗": "+",
        "╚": "+",
        "╝": "+",
        "╠": "+",
        "╣": "+",
        "╦": "+",
        "╩": "+",
        "╬": "+",
    }
)


def _is_emoji(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x26FF
        or 0x2700 <= codepoint <= 0x27BF
    )


def sanitize_unicode(text: str) -> str:
    """Convert terminal-hostile symbols while preserving normal Unicode text."""
    translated = text.translate(_UNICODE_REPLACEMENTS)
    characters: list[str] = []
    for character in translated:
        codepoint = ord(character)
        if character in ("\n", "\t"):
            characters.append(character)
        elif codepoint < 32 or 0x7F <= codepoint <= 0x9F:
            continue
        elif character in ("\ufe0e", "\ufe0f", "\u200d"):
            continue
        elif 0x2500 <= codepoint <= 0x257F:
            characters.append("+")
        elif _is_emoji(character):
            characters.append("[?]")
        else:
            characters.append(character)
    return "".join(characters)


def normalize_terminal_text(text: str) -> str:
    """Remove terminal control sequences and normalize plain-text layout."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _ANSI_ESCAPE.sub("", normalized)
    return sanitize_unicode(normalized).expandtabs(4)


class TerminalAdapter:
    """Write normalized, old-terminal-safe text to a stream."""

    def __init__(self, stream: TextIO = sys.stdout) -> None:
        self._stream = stream

    def transform(self, text: str) -> str:
        return normalize_terminal_text(text)

    def write(self, text: str) -> None:
        self._stream.write(self.transform(text))
        self._stream.flush()
