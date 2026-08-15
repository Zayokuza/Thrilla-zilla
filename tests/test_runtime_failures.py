import importlib
import tempfile
import unittest
from pathlib import Path


class RuntimeFailureTests(unittest.TestCase):

    def test_failure_types_cover_stage3_failure_categories(self):
        try:
            failures = importlib.import_module(
                "thrilla.runtime.failures"
            )
        except Exception as error:
            self.fail(
                "runtime failures module must exist: {0}".format(
                    error
                )
            )

        kind = getattr(
            failures,
            "RuntimeFailureKind",
            None,
        )
        record_type = getattr(
            failures,
            "RuntimeFailure",
            None,
        )

        self.assertTrue(
            callable(kind),
            "RuntimeFailureKind must exist",
        )
        self.assertTrue(
            callable(record_type),
            "RuntimeFailure must exist",
        )

        self.assertEqual(
            (
                "executable_missing",
                "model_missing",
                "invalid_gguf",
                "incompatible_model",
                "port_occupied",
                "startup_timeout",
                "process_crash",
                "memory_failure",
                "http_health_failure",
                "model_api_failure",
                "unexpected_exit",
                "permission_failure",
            ),
            tuple(
                item.value
                for item in kind
            ),
        )

        record = record_type(
            kind=kind.STARTUP_TIMEOUT,
            what_failed="model startup",
            why="deadline expired",
            where="127.0.0.1:8080",
            attempted_recovery="health polling",
            remaining_options=(
                "retry",
                "select lighter model",
            ),
        )

        self.assertEqual(
            "model startup",
            record.what_failed,
        )
        self.assertEqual(
            "deadline expired",
            record.why,
        )
        self.assertEqual(
            "127.0.0.1:8080",
            record.where,
        )
        self.assertEqual(
            "health polling",
            record.attempted_recovery,
        )
        self.assertEqual(
            (
                "retry",
                "select lighter model",
            ),
            record.remaining_options,
        )

    def test_spawn_exception_classifier_distinguishes_root_causes(self):
        failures = importlib.import_module(
            "thrilla.runtime.failures"
        )

        classifier = getattr(
            failures,
            "failure_from_spawn_exception",
            None,
        )

        self.assertTrue(
            callable(classifier),
            "failure_from_spawn_exception must exist",
        )

        cases = (
            (
                FileNotFoundError("llama-server missing"),
                failures.RuntimeFailureKind.EXECUTABLE_MISSING,
            ),
            (
                PermissionError("permission denied"),
                failures.RuntimeFailureKind.PERMISSION_FAILURE,
            ),
            (
                MemoryError("allocation failed"),
                failures.RuntimeFailureKind.MEMORY_FAILURE,
            ),
        )

        for error, expected_kind in cases:
            with self.subTest(
                expected_kind=expected_kind
            ):
                result = classifier(
                    error,
                    where="runtime spawn",
                )

                self.assertEqual(
                    expected_kind,
                    result.kind,
                )
                self.assertTrue(
                    result.what_failed,
                )
                self.assertTrue(
                    result.why,
                )
                self.assertEqual(
                    "runtime spawn",
                    result.where,
                )
                self.assertTrue(
                    result.remaining_options,
                )

    def test_port_failure_classifier_reports_occupied_port(self):
        failures = importlib.import_module(
            "thrilla.runtime.failures"
        )
        ports = importlib.import_module(
            "thrilla.runtime.ports"
        )

        classifier = getattr(
            failures,
            "failure_from_port_inspection",
            None,
        )

        self.assertTrue(
            callable(classifier),
            "failure_from_port_inspection must exist",
        )

        status = ports.PortInspection(
            host="127.0.0.1",
            port=8080,
            listening=True,
            bindable=False,
        )

        result = classifier(
            status
        )

        self.assertEqual(
            failures.RuntimeFailureKind.PORT_OCCUPIED,
            result.kind,
        )
        self.assertEqual(
            "127.0.0.1:8080",
            result.where,
        )
        self.assertIn(
            "select another permitted port",
            result.remaining_options,
        )

    def test_readiness_failure_classifier_reports_startup_timeout(self):
        failures = importlib.import_module(
            "thrilla.runtime.failures"
        )
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        classifier = getattr(
            failures,
            "failure_from_readiness",
            None,
        )

        self.assertTrue(
            callable(classifier),
            "failure_from_readiness must exist",
        )

        readiness = health.ReadinessResult(
            ready=False,
            timed_out=True,
            attempts=5,
            elapsed_seconds=2.0,
            models=(),
            detail="connection refused",
        )

        result = classifier(
            readiness,
            where="127.0.0.1:8080",
        )

        self.assertEqual(
            failures.RuntimeFailureKind.STARTUP_TIMEOUT,
            result.kind,
        )

        self.assertEqual(
            "127.0.0.1:8080",
            result.where,
        )

        self.assertIn(
            "5",
            result.why,
        )

    def test_models_probe_classifier_distinguishes_health_and_api_failures(self):
        failures = importlib.import_module(
            "thrilla.runtime.failures"
        )
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        classifier = getattr(
            failures,
            "failure_from_models_probe",
            None,
        )

        self.assertTrue(
            callable(classifier),
            "failure_from_models_probe must exist",
        )

        cases = (
            (
                health.ModelsEndpointProbe(
                    url="http://127.0.0.1:8080/v1/models",
                    reachable=False,
                    openai_compatible=False,
                    models=(),
                    detail="connection refused",
                    expected_model="expected",
                    model_match=False,
                ),
                failures.RuntimeFailureKind.HTTP_HEALTH_FAILURE,
            ),
            (
                health.ModelsEndpointProbe(
                    url="http://127.0.0.1:8080/v1/models",
                    reachable=True,
                    openai_compatible=False,
                    models=(),
                    detail="unexpected /v1/models payload",
                    expected_model="expected",
                    model_match=False,
                ),
                failures.RuntimeFailureKind.MODEL_API_FAILURE,
            ),
            (
                health.ModelsEndpointProbe(
                    url="http://127.0.0.1:8080/v1/models",
                    reachable=True,
                    openai_compatible=True,
                    models=("other-model",),
                    detail="models endpoint responded",
                    expected_model="expected",
                    model_match=False,
                ),
                failures.RuntimeFailureKind.INCOMPATIBLE_MODEL,
            ),
        )

        for probe, expected_kind in cases:
            with self.subTest(
                expected_kind=expected_kind
            ):
                result = classifier(
                    probe
                )

                self.assertEqual(
                    expected_kind,
                    result.kind,
                )

                self.assertEqual(
                    probe.url,
                    result.where,
                )

    def test_process_returncode_classifier_distinguishes_crash_and_exit(self):
        failures = importlib.import_module(
            "thrilla.runtime.failures"
        )

        classifier = getattr(
            failures,
            "failure_from_process_returncode",
            None,
        )

        self.assertTrue(
            callable(classifier),
            "failure_from_process_returncode must exist",
        )

        crash = classifier(
            -9,
            where="pid 1234",
        )

        exit_failure = classifier(
            1,
            where="pid 5678",
        )

        self.assertEqual(
            failures.RuntimeFailureKind.PROCESS_CRASH,
            crash.kind,
        )

        self.assertEqual(
            failures.RuntimeFailureKind.UNEXPECTED_EXIT,
            exit_failure.kind,
        )

        self.assertIsNone(
            classifier(
                None,
                where="pid 9999",
            ),
            "running process must not be classified as failed",
        )

    def test_model_file_classifier_reports_missing_and_invalid_gguf(self):
        failures = importlib.import_module(
            "thrilla.runtime.failures"
        )

        inspector = getattr(
            failures,
            "inspect_model_file_failure",
            None,
        )

        self.assertTrue(
            callable(inspector),
            "inspect_model_file_failure must exist",
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            missing = inspector(
                root / "missing.gguf"
            )

            invalid_path = root / "invalid.gguf"
            invalid_path.write_bytes(
                b"NOTG-valid-model-data"
            )

            invalid = inspector(
                invalid_path
            )

            valid_path = root / "valid.gguf"
            valid_path.write_bytes(
                b"GGUF-test-model-data"
            )

            valid = inspector(
                valid_path
            )

        self.assertEqual(
            failures.RuntimeFailureKind.MODEL_MISSING,
            missing.kind,
        )

        self.assertEqual(
            failures.RuntimeFailureKind.INVALID_GGUF,
            invalid.kind,
        )

        self.assertIsNone(
            valid,
            "GGUF magic must pass lightweight model-file inspection",
        )


if __name__ == "__main__":
    unittest.main()
