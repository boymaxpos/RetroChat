import asyncio
import io
import unittest
from collections.abc import AsyncIterator

from retrochat.app import RetroChatApp
from retrochat.backend import BackendError, ChatBackend


class FakeBackend(ChatBackend):
    def __init__(self, responses: dict[str, list[str]] | None = None) -> None:
        self.responses = responses or {}
        self.started = 0
        self.reset = 0
        self.closed = 0
        self.interrupted = 0
        self.messages: list[str] = []

    async def start_conversation(self) -> None:
        self.started += 1

    async def send_message(self, message: str) -> AsyncIterator[str]:
        self.messages.append(message)
        for chunk in self.responses.get(message, ["response"]):
            yield chunk

    async def reset_conversation(self) -> None:
        self.reset += 1

    async def interrupt(self) -> bool:
        self.interrupted += 1
        return True

    async def close(self) -> None:
        self.closed += 1


def line_reader(lines: list[str | None]):
    remaining = iter(lines)

    async def read() -> str | None:
        await asyncio.sleep(0)
        return next(remaining)

    return read


class RetroChatAppTests(unittest.IsolatedAsyncioTestCase):
    async def test_help_new_and_exit(self) -> None:
        backend = FakeBackend()
        output = io.StringIO()
        app = RetroChatApp(
            backend,
            line_reader(["/help", "/new", "/exit"]),
            output=output,
        )

        self.assertEqual(await app.run(), 0)
        text = output.getvalue()
        self.assertIn("/help - Show commands", text)
        self.assertIn("[New conversation]", text)
        self.assertIn("Goodbye.", text)
        self.assertEqual(backend.reset, 1)
        self.assertEqual(backend.closed, 1)

    async def test_streams_multiple_messages(self) -> None:
        backend = FakeBackend({"hello": ["Hel", "lo"], "follow up": ["Context"]})
        output = io.StringIO()
        app = RetroChatApp(
            backend,
            line_reader(["hello", "follow up", "/exit"]),
            output=output,
        )

        self.assertEqual(await app.run(), 0)
        self.assertEqual(backend.messages, ["hello", "follow up"])
        self.assertIn("GPT> Hello", output.getvalue())
        self.assertIn("GPT> Context", output.getvalue())

    async def test_all_model_output_uses_terminal_adapter(self) -> None:
        backend = FakeBackend({"symbols": ["Hello ✅ ", "→ Windows — 中文"]})
        output = io.StringIO()
        app = RetroChatApp(
            backend,
            line_reader(["symbols", "/exit"]),
            output=output,
        )

        self.assertEqual(await app.run(), 0)
        self.assertIn("GPT> Hello [OK] -> Windows - 中文", output.getvalue())

    async def test_unknown_command_does_not_reach_backend(self) -> None:
        backend = FakeBackend()
        output = io.StringIO()
        app = RetroChatApp(
            backend,
            line_reader(["/future", "/exit"]),
            output=output,
        )

        self.assertEqual(await app.run(), 0)
        self.assertIn("Unknown command", output.getvalue())
        self.assertEqual(backend.messages, [])

    async def test_eof_exits_cleanly(self) -> None:
        backend = FakeBackend()
        output = io.StringIO()
        app = RetroChatApp(backend, line_reader([None]), output=output)

        self.assertEqual(await app.run(), 0)
        self.assertIn("Goodbye.", output.getvalue())
        self.assertEqual(backend.closed, 1)

    async def test_idle_interrupt_keeps_app_running(self) -> None:
        backend = FakeBackend()
        output = io.StringIO()
        interrupt_event = asyncio.Event()
        calls = 0

        async def read() -> str | None:
            nonlocal calls
            calls += 1
            if calls == 1:
                interrupt_event.set()
                await asyncio.Event().wait()
            return "/exit"

        app = RetroChatApp(
            backend,
            read,
            output=output,
            interrupt_event=interrupt_event,
        )

        self.assertEqual(await app.run(), 0)
        self.assertIn("Use /exit to quit.", output.getvalue())

    async def test_interrupt_stops_active_generation(self) -> None:
        interrupt_event = asyncio.Event()
        release = asyncio.Event()

        class InterruptibleBackend(FakeBackend):
            async def send_message(self, message: str) -> AsyncIterator[str]:
                self.messages.append(message)
                yield "partial"
                interrupt_event.set()
                await release.wait()
                raise BackendError("Generation was interrupted.")

            async def interrupt(self) -> bool:
                self.interrupted += 1
                release.set()
                return True

        backend = InterruptibleBackend()
        output = io.StringIO()
        app = RetroChatApp(
            backend,
            line_reader(["long response", "/exit"]),
            output=output,
            interrupt_event=interrupt_event,
        )

        self.assertEqual(await app.run(), 0)
        self.assertEqual(backend.interrupted, 1)
        self.assertIn("partial", output.getvalue())
        self.assertIn("[Stopped]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
