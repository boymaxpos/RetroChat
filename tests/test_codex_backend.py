import asyncio
import unittest
from typing import Any

from retrochat.backend import BackendError, ChatBackend
from retrochat.codex_backend import CodexBackend, FinalTextParser


class FakeClient:
    def __init__(self) -> None:
        self.started = False
        self.closed = False
        self.requests: list[tuple[str, dict[str, Any]]] = []
        self.notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.thread_number = 0
        self.turn_number = 0

    async def start(self) -> None:
        self.started = True

    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.requests.append((method, params))
        if method == "thread/start":
            self.thread_number += 1
            return {"thread": {"id": f"thread-{self.thread_number}"}}
        if method == "turn/start":
            self.turn_number += 1
            return {"turn": {"id": f"turn-{self.turn_number}"}}
        return {}

    async def next_notification(self) -> dict[str, Any]:
        return await self.notifications.get()

    async def close(self) -> None:
        self.closed = True

    def queue_completed_turn(self, thread_id: str, turn_id: str, text: str) -> None:
        self.notifications.put_nowait(
            {
                "method": "item/started",
                "params": {
                    "threadId": thread_id,
                    "turnId": turn_id,
                    "item": {
                        "id": f"item-{turn_id}",
                        "type": "agentMessage",
                        "text": "",
                        "phase": "final_answer",
                    },
                },
            }
        )
        self.notifications.put_nowait(
            {
                "method": "item/agentMessage/delta",
                "params": {
                    "threadId": thread_id,
                    "turnId": turn_id,
                    "itemId": f"item-{turn_id}",
                    "delta": text,
                },
            }
        )
        self.notifications.put_nowait(
            {
                "method": "turn/completed",
                "params": {
                    "threadId": thread_id,
                    "turnId": turn_id,
                    "turn": {"id": turn_id, "status": "completed", "error": None},
                },
            }
        )


class FinalTextParserTests(unittest.TestCase):
    def test_filters_commentary_and_streams_final_text(self) -> None:
        parser = FinalTextParser()
        parser.feed(
            {
                "method": "item/started",
                "params": {
                    "item": {
                        "id": "commentary",
                        "type": "agentMessage",
                        "phase": "commentary",
                    }
                },
            }
        )
        self.assertEqual(
            parser.feed(
                {
                    "method": "item/agentMessage/delta",
                    "params": {"itemId": "commentary", "delta": "hidden"},
                }
            ),
            [],
        )

        parser.feed(
            {
                "method": "item/started",
                "params": {
                    "item": {
                        "id": "final",
                        "type": "agentMessage",
                        "phase": "final_answer",
                    }
                },
            }
        )
        self.assertEqual(
            parser.feed(
                {
                    "method": "item/agentMessage/delta",
                    "params": {"itemId": "final", "delta": "visible"},
                }
            ),
            ["visible"],
        )


class CodexBackendTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = FakeClient()
        self.backend = CodexBackend(lambda: self.client)

    async def asyncTearDown(self) -> None:
        await self.backend.close()

    async def test_implements_backend_interface(self) -> None:
        self.assertIsInstance(self.backend, ChatBackend)

    async def test_continuation_reuses_thread(self) -> None:
        await self.backend.start_conversation()
        self.client.queue_completed_turn("thread-1", "turn-1", "first")
        first = [chunk async for chunk in self.backend.send_message("one")]
        self.client.queue_completed_turn("thread-1", "turn-2", "second")
        second = [chunk async for chunk in self.backend.send_message("two")]

        self.assertEqual(first, ["first"])
        self.assertEqual(second, ["second"])
        turn_requests = [
            params for method, params in self.client.requests if method == "turn/start"
        ]
        self.assertEqual(
            [request["threadId"] for request in turn_requests],
            ["thread-1", "thread-1"],
        )

    async def test_reset_starts_new_thread(self) -> None:
        await self.backend.start_conversation()
        await self.backend.reset_conversation()
        thread_requests = [
            request for request in self.client.requests if request[0] == "thread/start"
        ]
        self.assertEqual(len(thread_requests), 2)

    async def test_interrupt_sends_active_ids(self) -> None:
        await self.backend.start_conversation()
        self.client.queue_completed_turn("thread-1", "turn-1", "unused")
        generator = self.backend.send_message("long answer")
        pending_chunk = asyncio.create_task(anext(generator))
        await asyncio.sleep(0)

        self.assertTrue(await self.backend.interrupt())
        self.assertIn(
            (
                "turn/interrupt",
                {"threadId": "thread-1", "turnId": "turn-1"},
            ),
            self.client.requests,
        )
        await pending_chunk
        await generator.aclose()

    async def test_empty_message_is_rejected(self) -> None:
        with self.assertRaisesRegex(BackendError, "cannot be empty"):
            await anext(self.backend.send_message("   "))

    async def test_close_releases_client(self) -> None:
        await self.backend.start_conversation()
        await self.backend.close()
        self.assertTrue(self.client.closed)


if __name__ == "__main__":
    unittest.main()
