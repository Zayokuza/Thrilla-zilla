import importlib
import unittest


class RuntimeTypeTests(unittest.TestCase):
    def _load(self, module_name):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            self.fail(
                "Stage 3 runtime module is missing: {0}".format(error)
            )

    def test_runtime_state_defines_complete_lifecycle(self):
        state = self._load("thrilla.runtime.state")

        expected = {
            "UNKNOWN",
            "STOPPED",
            "DISCOVERING",
            "SELECTING",
            "STARTING",
            "LOADING_MODEL",
            "HEALTH_CHECKING",
            "READY",
            "BUSY",
            "STOPPING",
            "FAILED",
            "CRASHED",
            "RECOVERING",
        }

        actual = {item.name for item in state.RuntimeState}

        self.assertEqual(expected, actual)

    def test_model_role_defines_runtime_model_roles(self):
        models = self._load("thrilla.runtime.models")

        expected = {
            "PRIMARY",
            "CODING",
            "PLANNER",
            "EMBEDDING",
            "ALTERNATE",
            "UNKNOWN",
        }

        actual = {item.name for item in models.ModelRole}

        self.assertEqual(expected, actual)

    def test_model_candidate_records_required_metadata(self):
        models = self._load("thrilla.runtime.models")

        candidate = models.ModelCandidate(
            path="/models/example.gguf",
            filename="example.gguf",
            size_bytes=123456,
            architecture="qwen2",
            quantization="Q4_K_M",
            role=models.ModelRole.CODING,
            context_capability=32768,
            readable=True,
            compatibility="llama.cpp",
            source="discovery",
            last_verified="2026-08-13T21:00:00-05:00",
            score=95.0,
        )

        self.assertEqual("/models/example.gguf", candidate.path)
        self.assertEqual("example.gguf", candidate.filename)
        self.assertEqual(123456, candidate.size_bytes)
        self.assertEqual("qwen2", candidate.architecture)
        self.assertEqual("Q4_K_M", candidate.quantization)
        self.assertEqual(models.ModelRole.CODING, candidate.role)
        self.assertEqual(32768, candidate.context_capability)
        self.assertIs(True, candidate.readable)
        self.assertEqual("llama.cpp", candidate.compatibility)
        self.assertEqual("discovery", candidate.source)
        self.assertEqual(
            "2026-08-13T21:00:00-05:00",
            candidate.last_verified,
        )
        self.assertEqual(95.0, candidate.score)


if __name__ == "__main__":
    unittest.main()
