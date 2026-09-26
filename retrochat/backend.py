"""Backend interface shared by RetroChat model gateways."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class BackendError(RuntimeError):
    """A backend failure safe to show in the terminal UI."""


class ChatBackend(ABC):
    """Small interface required by the future RetroChat CLI."""

    @abstractmethod
    async def start_conversation(self) -> None:
        """Start a new conversation and make it current."""

    @abstractmethod
    def send_message(self, message: str) -> AsyncIterator[str]:
        """Send one message and stream final assistant text chunks."""

    @abstractmethod
    async def reset_conversation(self) -> None:
        """Discard current context and start a fresh conversation."""

    @abstractmethod
    async def interrupt(self) -> bool:
        """Interrupt the active turn, returning whether one existed."""

    @abstractmethod
    async def close(self) -> None:
        """Release backend processes and resources."""
