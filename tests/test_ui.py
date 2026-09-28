import unittest

from retrochat.ui import BANNER, HELP_TEXT, UI_WIDTH


class AsciiUiTests(unittest.TestCase):
    def test_banner_is_ascii_and_fits_win98_terminal(self) -> None:
        BANNER.encode("ascii")
        self.assertIn("MAC GATEWAY ONLINE", BANNER)
        self.assertIn("Commands: /help  /new  /exit", BANNER)
        for line in BANNER.splitlines():
            self.assertLessEqual(len(line), UI_WIDTH)

    def test_logo_has_matching_fixed_width_borders(self) -> None:
        box_lines = BANNER.splitlines()[:11]
        self.assertEqual(len(box_lines), 11)
        self.assertTrue(all(len(line) == UI_WIDTH for line in box_lines))
        self.assertEqual(box_lines[0], "+" + "-" * (UI_WIDTH - 2) + "+")
        self.assertEqual(box_lines[-1], box_lines[0])

    def test_help_is_ascii_fixed_width_and_complete(self) -> None:
        HELP_TEXT.encode("ascii")
        self.assertTrue(all(len(line) == UI_WIDTH for line in HELP_TEXT.splitlines()))
        for command in ("/help", "/new", "/exit", "Ctrl+C", "Ctrl+D"):
            self.assertIn(command, HELP_TEXT)


if __name__ == "__main__":
    unittest.main()
