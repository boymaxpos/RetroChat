"""Codex-backed implementation of the RetroChat backend interface."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, Protocol

from .backend import BackendError, ChatBackend
from .codex_protocol import AppServerClient
from .prompts import TERMINAL_INSTRUCTIONS


class AppServerTransport(Protocol):
    async def start(self) -> None: ...

    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]: ...

    async def next_notification(self) -> dict[str, Any]: ...

    async def close(self) -> None: ...


class FinalTextParser:
    """Extract final assistant-facing text from one Codex turn."""

    def __init__(self) -> None:
        self._phases: dict[str, str | None] = {}
        self._streamed_items: set[str] = set()
        self.wrote_text = False
        self.turn_status: str | None = None
        self.turn_error: str | None = None

    def feed(self, message: dict[str, Any]) -> list[str]:
        method = message.get("method")
        params = message.get("params") or {}

        if method == "item/started":
            item = params.get("item") or {}
            if item.get("type") == "agentMessage":
                self._phases[item.get("id", "")] = item.get("phase")
            return []

        if method == "item/agentMessage/delta":
            item_id = params.get("itemId", "")
            phase = self._phases.get(item_id)
            delta = params.get("delta", "")
            if phase in (None, "final_answer") and delta:
                self._streamed_items.add(item_id)
                self.wrote_text = True
                return [delta]
            return []

        if method == "item/completed":
            item = params.get("item") or {}
            item_id = item.get("id", "")
            phase = item.get("phase", self._phases.get(item_id))
            if (
                item.get("type") == "agentMessage"
                and phase in (None, "final_answer")
                and item_id not in self._streamed_items
                and item.get("text")
            ):
                self.wrote_text = True
                return [item["text"]]
            return []

        if method == "turn/completed":
            turn = params.get("turn") or {}
            self.turn_status = turn.get("status")
            error = turn.get("error") or {}
            self.turn_error = error.get("message")
        return []


class CodexBackend(ChatBackend):
    """Maintain one safe, streaming Codex conversation."""

    def __init__(
        self,
        client_factory: Callable[[], AppServerTransport] = AppServerClient,
    ) -> None:
        self._client_factory = client_factory
        self._client: AppServerTransport | None = None
        self._thread_id: str | None = None
        self._active_turn_id: str | None = None
        self._turn_lock = asyncio.Lock()
        self._working_dir: tempfile.TemporaryDirectory[str] | None = None

    async def _connect(self) -> AppServerTransport:
        if self._client is None:
            self._client = self._client_factory()
            await self._client.start()
        return self._client

    async def start_conversation(self) -> None:
        if self._active_turn_id is not None:
            raise BackendError("Cannot start a new conversation during an active turn.")

        client = await self._connect()
        if self._working_dir is None:
            self._working_dir = tempfile.TemporaryDirectory(prefix="retrochat-")

        result = await client.request(
            "thread/start",
            {
                "cwd": str(Path(self._working_dir.name).resolve()),
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "ephemeral": True,
                "developerInstructions": TERMINAL_INSTRUCTIONS,
                "serviceName": "retrochat",
            },
        )
        thread_id = (result.get("thread") or {}).get("id")
        if not thread_id:
            raise BackendError("Codex App Server did not return a thread ID.")
        self._thread_id = thread_id

    async def reset_conversation(self) -> None:
        await self.start_conversation()

    async def send_message(self, message: str) -> AsyncIterator[str]:
        if not message.strip():
            raise BackendError("Message cannot be empty.")

        async with self._turn_lock:
            if self._thread_id is None:
                await self.start_conversation()
            client = await self._connect()
            assert self._thread_id is not None
            thread_id = self._thread_id

            result = await client.request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": message}],
                    "approvalPolicy": "never",
                    "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
                },
            )
            turn_id = (result.get("turn") or {}).get("id")
            if not turn_id:
                raise BackendError("Codex App Server did not return a turn ID.")

            self._active_turn_id = turn_id
            parser = FinalTextParser()
            try:
                while parser.turn_status is None:
                    notification = await client.next_notification()
                    if not self._belongs_to_turn(notification, thread_id, turn_id):
                        continue
                    for delta in parser.feed(notification):
                        yield delta
            finally:
                self._active_turn_id = None

            if parser.turn_status == "interrupted":
                raise BackendError("Generation was interrupted.")
            if parser.turn_status != "completed":
                detail = parser.turn_error or parser.turn_status or "unknown status"
                raise BackendError(f"Model turn did not complete: {detail}")
            if not parser.wrote_text:
                raise BackendError("The model completed without a textual response.")

    @staticmethod
    def _belongs_to_turn(
        notification: dict[str, Any], thread_id: str, turn_id: str
    ) -> bool:
        params = notification.get("params") or {}
        event_thread_id = params.get("threadId")
        event_turn_id = params.get("turnId")
        if notification.get("method") == "turn/completed":
            event_turn_id = (params.get("turn") or {}).get("id", event_turn_id)
        return event_thread_id == thread_id and event_turn_id == turn_id

    async def interrupt(self) -> bool:
        if self._thread_id is None or self._active_turn_id is None:
            return False
        client = await self._connect()
        await client.request(
            "turn/interrupt",
            {"threadId": self._thread_id, "turnId": self._active_turn_id},
        )
        return True

    async def close(self) -> None:
        client = self._client
        if client is not None:
            if self._active_turn_id is not None:
                try:
                    await self.interrupt()
                except BackendError:
                    pass
            await client.close()
        self._client = None
        self._thread_id = None
        self._active_turn_id = None
        if self._working_dir is not None:
            self._working_dir.cleanup()
            self._working_dir = None
