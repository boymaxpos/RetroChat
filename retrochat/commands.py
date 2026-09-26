"""ASCII command parsing for the RetroChat CLI."""

from __future__ import annotations

from enum import Enum


class Command(Enum):
    HELP = "help"
    NEW = "new"
    EXIT = "exit"
    UNKNOWN = "unknown"


def parse_command(text: str) -> Command | None:
    """Return a command for slash input, or None for a chat message."""
    normalized = text.strip()
    if not normalized.startswith("/"):
        return None
    return {
        "/help": Command.HELP,
        "/new": Command.NEW,
        "/exit": Command.EXIT,
    }.get(normalized, Command.UNKNOWN)
