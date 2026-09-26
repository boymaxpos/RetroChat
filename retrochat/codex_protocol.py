"""Version-local JSONL transport for Codex App Server."""

from __future__ import annotations

import asyncio
import json
import shutil
from typing import Any

from .backend import BackendError


CLIENT_NAME = "retrochat"
CLIENT_VERSION = "0.2.0-phase2"


class CodexProtocolError(BackendError):
    """A failure starting or communicating with Codex App Server."""


class AppServerClient:
    """Multiplex JSON-RPC responses and notifications over JSONL stdio."""

    def __init__(self) -> None:
        self.process: asyncio.subprocess.Process | None = None
        self._next_id = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._notifications: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._stderr_lines: list[str] = []
        self._reader_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._write_lock = asyncio.Lock()

    async def start(self) -> None:
        if self.process is not None:
            return

        codex = shutil.which("codex")
        if codex is None:
            raise CodexProtocolError("Codex is not installed or is not on PATH.")

        try:
            self.process = await asyncio.create_subprocess_exec(
                codex,
                "app-server",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as exc:
            raise CodexProtocolError("Cannot start Codex App Server.") from exc

        self._reader_task = asyncio.create_task(self._read_stdout())
        self._stderr_task = asyncio.create_task(self._drain_stderr())
        await self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": CLIENT_NAME,
                    "title": "RetroChat",
                    "version": CLIENT_VERSION,
                }
            },
        )
        await self.notify("initialized", {})

    async def _read_stdout(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        failure: CodexProtocolError | None = None
        try:
            while line := await self.process.stdout.readline():
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if "method" in message and "id" in message:
                    await self._reject_server_request(message)
                    continue

                request_id = message.get("id")
                if request_id is not None:
                    future = self._pending.pop(request_id, None)
                    if future is not None and not future.done():
                        future.set_result(message)
                    continue

                if "method" in message:
                    await self._notifications.put(message)
        except (BrokenPipeError, ConnectionResetError) as exc:
            failure = CodexProtocolError("Codex App Server connection was lost.")
            failure.__cause__ = exc
        finally:
            if failure is None:
                failure = CodexProtocolError(self._exit_message())
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(failure)
            self._pending.clear()
            await self._notifications.put(None)

    async def _drain_stderr(self) -> None:
        assert self.process is not None and self.process.stderr is not None
        while line := await self.process.stderr.readline():
            text = line.decode("utf-8", errors="replace").rstrip()
            self._stderr_lines.append(text)
            del self._stderr_lines[:-20]

    def _exit_message(self) -> str:
        details = self._stderr_lines[-1] if self._stderr_lines else ""
        if "auth" in details.lower() or "login" in details.lower():
            return "ChatGPT authentication is required. Run 'codex login' first."
        return "Codex App Server stopped unexpectedly."

    async def _send(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise CodexProtocolError("Codex App Server is not running.")
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        async with self._write_lock:
            self.process.stdin.write((payload + "\n").encode("utf-8"))
            try:
                await self.process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError) as exc:
                raise CodexProtocolError(
                    "Codex App Server stopped unexpectedly."
                ) from exc

    async def notify(self, method: str, params: dict[str, Any]) -> None:
        await self._send({"method": method, "params": params})

    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[request_id] = future
        try:
            await self._send({"method": method, "id": request_id, "params": params})
            message = await future
        finally:
            self._pending.pop(request_id, None)

        if "error" in message:
            error = message["error"]
            raise CodexProtocolError(error.get("message", f"{method} failed."))
        return message.get("result") or {}

    async def next_notification(self) -> dict[str, Any]:
        message = await self._notifications.get()
        if message is None:
            raise CodexProtocolError(self._exit_message())
        return message

    async def _reject_server_request(self, message: dict[str, Any]) -> None:
        try:
            await self._send(
                {
                    "id": message["id"],
                    "error": {
                        "code": -32601,
                        "message": "RetroChat does not permit tool execution.",
                    },
                }
            )
        except CodexProtocolError:
            pass

    async def close(self) -> None:
        process = self.process
        if process is None:
            return

        if process.stdin is not None and not process.stdin.is_closing():
            process.stdin.close()
            try:
                await process.stdin.wait_closed()
            except (BrokenPipeError, ConnectionResetError):
                pass

        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except TimeoutError:
                process.kill()
                await process.wait()

        tasks = [
            task
            for task in (self._reader_task, self._stderr_task)
            if task is not None
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.process = None
