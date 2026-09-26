"""Plain-text RetroChat command loop."""

from __future__ import annotations

import asyncio
import signal
import sys
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TextIO

from .backend import BackendError, ChatBackend
from .codex_backend import CodexBackend
from .commands import Command, parse_command
from .terminal import TerminalAdapter


BANNER = """\
RETROCHAT 0.1
Mac Gateway Connected
----------------------------

/help  Commands
/new   New conversation
/exit  Exit
"""

HELP_TEXT = """\
/help - Show commands
/new  - New conversation
/exit - Exit RetroChat
"""

_INTERRUPTED = object()


class AsyncStdinReader:
    """Read terminal lines without blocking the asyncio event loop."""

    def __init__(self, stream: TextIO = sys.stdin) -> None:
        self._stream = stream

    async def readline(self) -> str | None:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str | None] = loop.create_future()
        file_descriptor = self._stream.fileno()

        def ready() -> None:
            if future.done():
                return
            line = self._stream.readline()
            future.set_result(None if line == "" else line.rstrip("\r\n"))

        loop.add_reader(file_descriptor, ready)
        try:
            return await future
        finally:
            loop.remove_reader(file_descriptor)


class RetroChatApp:
    """Coordinate terminal input, commands, and one chat backend."""

    def __init__(
        self,
        backend: ChatBackend,
        read_line: Callable[[], Awaitable[str | None]],
        output: TextIO = sys.stdout,
        interrupt_event: asyncio.Event | None = None,
    ) -> None:
        self._backend = backend
        self._read_line = read_line
        self._terminal = TerminalAdapter(output)
        self._interrupt_event = interrupt_event or asyncio.Event()

    def request_interrupt(self) -> None:
        self._interrupt_event.set()

    def _write(self, text: str) -> None:
        self._terminal.write(text)

    async def run(self) -> int:
        self._write(BANNER + "\n")
        try:
            await self._backend.start_conversation()
            while True:
                line = await self._wait_for_input()
                if line is _INTERRUPTED:
                    self._write("\nUse /exit to quit.\n\n")
                    continue
                if line is None:
                    self._write("\nGoodbye.\n")
                    return 0

                assert isinstance(line, str)
                text = line.strip()
                if not text:
                    self._write("\n")
                    continue

                command = parse_command(text)
                if command is Command.HELP:
                    self._write("\n" + HELP_TEXT + "\n")
                elif command is Command.NEW:
                    await self._backend.reset_conversation()
                    self._write("\n[New conversation]\n\n")
                elif command is Command.EXIT:
                    self._write("\nGoodbye.\n")
                    return 0
                elif command is Command.UNKNOWN:
                    self._write("\n[ERROR] Unknown command. Type /help.\n\n")
                else:
                    await self._stream_response(text)
        except BackendError as exc:
            self._write(f"\n[ERROR] {exc}\n")
            return 1
        finally:
            await self._backend.close()

    async def _wait_for_input(self) -> str | None | object:
        self._interrupt_event.clear()
        self._write("You> ")
        input_task = asyncio.create_task(self._read_line())
        interrupt_task = asyncio.create_task(self._interrupt_event.wait())
        done, _ = await asyncio.wait(
            {input_task, interrupt_task}, return_when=asyncio.FIRST_COMPLETED
        )

        if input_task in done:
            interrupt_task.cancel()
            with suppress(asyncio.CancelledError):
                await interrupt_task
            return input_task.result()

        input_task.cancel()
        with suppress(asyncio.CancelledError):
            await input_task
        return _INTERRUPTED

    async def _stream_response(self, message: str) -> None:
        self._interrupt_event.clear()
        self._write("\nGPT> ")

        async def consume() -> None:
            async for delta in self._backend.send_message(message):
                self._write(delta)

        response_task = asyncio.create_task(consume())
        interrupt_task = asyncio.create_task(self._interrupt_event.wait())
        done, _ = await asyncio.wait(
            {response_task, interrupt_task}, return_when=asyncio.FIRST_COMPLETED
        )

        if response_task in done:
            interrupt_task.cancel()
            with suppress(asyncio.CancelledError):
                await interrupt_task
            await response_task
            self._write("\n\n")
            return

        try:
            try:
                await self._backend.interrupt()
            except BackendError:
                response_task.cancel()
                with suppress(asyncio.CancelledError, BackendError):
                    await response_task
                raise
            try:
                await asyncio.wait_for(response_task, timeout=10)
            except BackendError as exc:
                if "interrupted" not in str(exc).lower():
                    raise
            except TimeoutError:
                response_task.cancel()
                with suppress(asyncio.CancelledError):
                    await response_task
            self._write("\n[Stopped]\n\n")
        finally:
            self._interrupt_event.clear()


async def run_cli() -> int:
    interrupt_event = asyncio.Event()
    reader = AsyncStdinReader()
    app = RetroChatApp(CodexBackend(), reader.readline, interrupt_event=interrupt_event)
    loop = asyncio.get_running_loop()
    installed_signal_handler = False
    try:
        loop.add_signal_handler(signal.SIGINT, app.request_interrupt)
        installed_signal_handler = True
    except (NotImplementedError, RuntimeError):
        pass

    try:
        return await app.run()
    finally:
        if installed_signal_handler:
            loop.remove_signal_handler(signal.SIGINT)


def main() -> int:
    try:
        return asyncio.run(run_cli())
    except KeyboardInterrupt:
        print("\nUse /exit to quit.")
        return 130
