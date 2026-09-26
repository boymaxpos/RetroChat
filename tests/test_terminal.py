import io
import unittest

from retrochat.terminal import (
    TerminalAdapter,
    normalize_terminal_text,
    sanitize_unicode,
)


class TerminalSanitizerTests(unittest.TestCase):
    def test_required_symbol_conversion(self) -> None:
        self.assertEqual(
            sanitize_unicode("Hello ✅ → Windows — test"),
            "Hello [OK] -> Windows - test",
        )

    def test_preserves_english_and_chinese(self) -> None:
        self.assertEqual(
            sanitize_unicode("Windows 98 中文输入和输出"),
            "Windows 98 中文输入和输出",
        )

    def test_quotes_arrows_and_status_symbols(self) -> None:
        self.assertEqual(
            sanitize_unicode("“yes” ‘no’ ← ✓ ✗"),
            '"yes" \'no\' <- [OK] [X]',
        )

    def test_box_drawing_becomes_ascii(self) -> None:
        self.assertEqual(
            sanitize_unicode("┌──┐\n│OK│\n└──┘"),
            "+--+\n|OK|\n+--+",
        )

    def test_unmapped_emoji_becomes_placeholder(self) -> None:
        self.assertEqual(sanitize_unicode("Retro 🤖 chat"), "Retro [?] chat")

    def test_removes_ansi_and_unsafe_controls(self) -> None:
        self.assertEqual(
            normalize_terminal_text("\x1b[31mRed\x1b[0m\x00 text"),
            "Red text",
        )

    def test_normalizes_newlines_and_tabs(self) -> None:
        self.assertEqual(
            normalize_terminal_text("A\r\nB\rC\tD"),
            "A\nB\nC   D",
        )

    def test_adapter_writes_without_changing_source(self) -> None:
        output = io.StringIO()
        adapter = TerminalAdapter(output)
        original = "你好 → Windows 98"

        adapter.write(original)

        self.assertEqual(original, "你好 → Windows 98")
        self.assertEqual(output.getvalue(), "你好 -> Windows 98")


if __name__ == "__main__":
    unittest.main()
