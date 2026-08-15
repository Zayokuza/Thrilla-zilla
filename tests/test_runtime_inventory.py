import importlib
import tempfile
import unittest
from pathlib import Path


class RuntimeInventoryTests(unittest.TestCase):

    def test_candidate_from_gguf_records_file_metadata(self):
        discovery = importlib.import_module(
            "thrilla.runtime.discovery"
        )
        models = importlib.import_module(
            "thrilla.runtime.models"
        )

        builder = getattr(
            discovery,
            "candidate_from_gguf",
            None,
        )

        self.assertTrue(
            callable(builder),
            "candidate_from_gguf must exist",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            model = Path(temp_dir) / "model.gguf"
            payload = b"GGUF-model-payload"
            model.write_bytes(payload)

            candidate = builder(
                model,
                source="unit-test",
            )

            self.assertIsInstance(
                candidate,
                models.ModelCandidate,
            )
            self.assertEqual(
                str(model.resolve()),
                candidate.path,
            )
            self.assertEqual(
                "model.gguf",
                candidate.filename,
            )
            self.assertEqual(
                len(payload),
                candidate.size_bytes,
            )
            self.assertEqual(
                "unknown",
                candidate.architecture,
            )
            self.assertEqual(
                "unknown",
                candidate.quantization,
            )
            self.assertEqual(
                models.ModelRole.UNKNOWN,
                candidate.role,
            )
            self.assertEqual(
                0,
                candidate.context_capability,
            )
            self.assertTrue(candidate.readable)
            self.assertEqual(
                "unknown",
                candidate.compatibility,
            )
            self.assertEqual(
                "unit-test",
                candidate.source,
            )
            self.assertTrue(candidate.last_verified)
            self.assertEqual(
                0.0,
                candidate.score,
            )

    def test_infer_model_role_recognizes_specialist_filenames(self):
        discovery = importlib.import_module(
            "thrilla.runtime.discovery"
        )
        models = importlib.import_module(
            "thrilla.runtime.models"
        )

        infer = getattr(
            discovery,
            "infer_model_role",
            None,
        )

        self.assertTrue(
            callable(infer),
            "infer_model_role must exist",
        )

        cases = [
            (
                "Qwen2.5-Coder-7B-Instruct.gguf",
                models.ModelRole.CODING,
            ),
            (
                "planner-kuza.gguf",
                models.ModelRole.PLANNER,
            ),
            (
                "nomic-embed-text-v1.5.gguf",
                models.ModelRole.EMBEDDING,
            ),
            (
                "gemma-3-4b-it.gguf",
                models.ModelRole.UNKNOWN,
            ),
        ]

        for filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(
                    expected,
                    infer(filename),
                )

    def test_infer_quantization_reads_common_gguf_filename_tokens(self):
        discovery = importlib.import_module(
            "thrilla.runtime.discovery"
        )

        infer = getattr(
            discovery,
            "infer_quantization",
            None,
        )

        self.assertTrue(
            callable(infer),
            "infer_quantization must exist",
        )

        self.assertEqual(
            "Q4_K_M",
            infer(
                "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf"
            ),
        )

        self.assertEqual(
            "IQ4_XS",
            infer(
                "example-IQ4_XS.gguf"
            ),
        )

        self.assertEqual(
            "unknown",
            infer(
                "model.gguf"
            ),
        )

    def test_build_model_inventory_returns_candidates_and_filters_artifacts(self):
        discovery = importlib.import_module(
            "thrilla.runtime.discovery"
        )
        models = importlib.import_module(
            "thrilla.runtime.models"
        )

        builder = getattr(
            discovery,
            "build_model_inventory",
            None,
        )

        self.assertTrue(
            callable(builder),
            "build_model_inventory must exist",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            primary = root / "Gemma-3-4B-Q4_K_M.gguf"
            primary.write_bytes(b"GGUF-primary")

            coder = root / "Qwen2.5-Coder-7B-Q4_K_M.gguf"
            coder.write_bytes(b"GGUF-coder")

            planner = root / "planner-kuza.gguf"
            planner.write_bytes(b"GGUF-planner")

            embedding = root / "nomic-embed-text-Q4_K_M.gguf"
            embedding.write_bytes(b"GGUF-embedding")

            vocab = root / "ggml-vocab-qwen2.gguf"
            vocab.write_bytes(b"GGUF-vocab")

            tests_dir = root / "tests"
            tests_dir.mkdir()

            artifact = tests_dir / "synthetic.gguf"
            artifact.write_bytes(b"GGUF-test")

            inventory = builder(
                [root],
                source="unit-root",
            )

            self.assertEqual(
                4,
                len(inventory),
            )

            self.assertTrue(
                all(
                    isinstance(
                        candidate,
                        models.ModelCandidate,
                    )
                    for candidate in inventory
                )
            )

            by_name = {
                candidate.filename: candidate
                for candidate in inventory
            }

            self.assertNotIn(
                vocab.name,
                by_name,
            )
            self.assertNotIn(
                artifact.name,
                by_name,
            )

            self.assertEqual(
                models.ModelRole.CODING,
                by_name[coder.name].role,
            )
            self.assertEqual(
                models.ModelRole.PLANNER,
                by_name[planner.name].role,
            )
            self.assertEqual(
                models.ModelRole.EMBEDDING,
                by_name[embedding.name].role,
            )
            self.assertEqual(
                models.ModelRole.UNKNOWN,
                by_name[primary.name].role,
            )

            self.assertEqual(
                "Q4_K_M",
                by_name[primary.name].quantization,
            )

            self.assertTrue(
                all(
                    candidate.source == "unit-root"
                    for candidate in inventory
                )
            )


if __name__ == "__main__":
    unittest.main()
