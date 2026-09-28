import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from retrochat.codex_protocol import find_codex_executable


class FindCodexExecutableTests(unittest.TestCase):
    def _make_executable(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        path.chmod(0o700)
        return path

    def test_explicit_path_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex = self._make_executable(Path(directory) / "custom-codex")
            with patch.dict(os.environ, {"RETROCHAT_CODEX": str(codex)}):
                self.assertEqual(find_codex_executable(), str(codex.resolve()))

    def test_invalid_explicit_path_does_not_silently_fall_back(self) -> None:
        with patch.dict(
            os.environ,
            {"RETROCHAT_CODEX": "/missing/retrochat-codex"},
        ):
            self.assertIsNone(find_codex_executable())

    def test_local_bin_fallback_supports_minimal_ssh_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex = self._make_executable(home / ".local/bin/codex")
            with (
                patch.dict(os.environ, {}, clear=True),
                patch("retrochat.codex_protocol.Path.home", return_value=home),
                patch("retrochat.codex_protocol.shutil.which", return_value=None),
            ):
                self.assertEqual(find_codex_executable(), str(codex.resolve()))


if __name__ == "__main__":
    unittest.main()
