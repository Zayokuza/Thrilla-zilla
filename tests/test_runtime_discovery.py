import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class RuntimeDiscoveryTests(unittest.TestCase):

    def test_find_llama_server_uses_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "llama-server"
            executable.write_text(
                "#!/bin/sh\nexit 0\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            try:
                discovery = importlib.import_module(
                    "thrilla.runtime.discovery"
                )
            except Exception as error:
                self.fail(
                    "runtime discovery must support llama-server lookup: "
                    "{0}".format(error)
                )

            finder = getattr(
                discovery,
                "find_llama_server",
                None,
            )

            self.assertTrue(
                callable(finder),
                "find_llama_server must exist",
            )

            with patch.dict(
                os.environ,
                {"PATH": temp_dir},
            ):
                found = finder()

            self.assertIsNotNone(found)
            self.assertEqual(
                executable.resolve(),
                Path(found).resolve(),
            )

    def test_find_llama_server_uses_termux_prefix_when_path_misses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir)
            bin_dir = prefix / "bin"
            bin_dir.mkdir()

            executable = bin_dir / "llama-server"
            executable.write_text(
                "#!/bin/sh\nexit 0\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            discovery = importlib.import_module(
                "thrilla.runtime.discovery"
            )

            with patch.dict(
                os.environ,
                {
                    "PATH": "",
                    "PREFIX": str(prefix),
                },
            ):
                found = discovery.find_llama_server()

            self.assertIsNotNone(
                found,
                "llama-server must be discovered under $PREFIX/bin",
            )
            self.assertEqual(
                executable.resolve(),
                Path(found).resolve(),
            )


if __name__ == "__main__":
    unittest.main()
