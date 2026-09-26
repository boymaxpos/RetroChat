import unittest

from retrochat.commands import Command, parse_command


class CommandTests(unittest.TestCase):
    def test_known_commands(self) -> None:
        self.assertIs(parse_command("/help"), Command.HELP)
        self.assertIs(parse_command(" /new "), Command.NEW)
        self.assertIs(parse_command("/exit"), Command.EXIT)

    def test_unknown_slash_command(self) -> None:
        self.assertIs(parse_command("/model"), Command.UNKNOWN)

    def test_normal_message(self) -> None:
        self.assertIsNone(parse_command("Tell me about Windows 98"))


if __name__ == "__main__":
    unittest.main()
