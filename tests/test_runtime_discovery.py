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

    def test_discover_gguf_files_recursively_finds_models(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "models" / "coding"
            nested.mkdir(parents=True)

            model = nested / "coder.gguf"
            model.write_bytes(b"GGUF")

            ignored = nested / "notes.txt"
            ignored.write_text(
                "not a model",
                encoding="utf-8",
            )

            discovery = importlib.import_module(
                "thrilla.runtime.discovery"
            )

            discover = getattr(
                discovery,
                "discover_gguf_files",
                None,
            )

            self.assertTrue(
                callable(discover),
                "discover_gguf_files must exist",
            )

            found = discover([root])

            self.assertEqual(
                [str(model.resolve())],
                found,
            )

    def test_discover_gguf_files_deduplicates_overlapping_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            models = root / "models"
            models.mkdir()

            model = models / "primary.gguf"
            model.write_bytes(b"GGUF")

            discovery = importlib.import_module(
                "thrilla.runtime.discovery"
            )

            found = discovery.discover_gguf_files(
                [
                    root,
                    root,
                ]
            )

            self.assertEqual(
                [str(model.resolve())],
                found,
            )


if __name__ == "__main__":
    unittest.main()
