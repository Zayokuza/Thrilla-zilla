import importlib
import unittest


class RuntimeProcessTests(unittest.TestCase):

    def test_process_ownership_defines_external_and_thrilla_managed(self):
        try:
            process = importlib.import_module(
                "thrilla.runtime.process"
            )
        except Exception as error:
            self.fail(
                "runtime process module must exist: {0}".format(
                    error
                )
            )

        ownership = getattr(
            process,
            "ProcessOwnership",
            None,
        )

        self.assertTrue(
            callable(ownership),
            "ProcessOwnership must exist",
        )

        self.assertEqual(
            "EXTERNAL",
            ownership.EXTERNAL.value,
        )
        self.assertEqual(
            "THRILLA_MANAGED",
            ownership.THRILLA_MANAGED.value,
        )

    def test_runtime_process_record_contains_required_metadata(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        record_type = getattr(
            process,
            "RuntimeProcessRecord",
            None,
        )

        self.assertTrue(
            callable(record_type),
            "RuntimeProcessRecord must exist",
        )

        command = (
            "/usr/bin/llama-server",
            "-m",
            "/models/primary.gguf",
        )

        record = record_type(
            ownership=process.ProcessOwnership.THRILLA_MANAGED,
            pid=12345,
            executable="/usr/bin/llama-server",
            command=command,
            model="/models/primary.gguf",
            port=8080,
            start_time="2026-08-15T00:00:00-05:00",
            owner_token="thrilla-token",
            log_path="/tmp/thrilla-llama.log",
        )

        self.assertEqual(
            process.ProcessOwnership.THRILLA_MANAGED,
            record.ownership,
        )
        self.assertEqual(
            12345,
            record.pid,
        )
        self.assertEqual(
            "/usr/bin/llama-server",
            record.executable,
        )
        self.assertEqual(
            command,
            record.command,
        )
        self.assertEqual(
            "/models/primary.gguf",
            record.model,
        )
        self.assertEqual(
            8080,
            record.port,
        )
        self.assertEqual(
            "2026-08-15T00:00:00-05:00",
            record.start_time,
        )
        self.assertEqual(
            "thrilla-token",
            record.owner_token,
        )
        self.assertEqual(
            "/tmp/thrilla-llama.log",
            record.log_path,
        )

    def test_external_process_never_grants_thrilla_control(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        controller = getattr(
            process,
            "can_control_process",
            None,
        )

        self.assertTrue(
            callable(controller),
            "can_control_process must exist",
        )

        record = process.RuntimeProcessRecord(
            ownership=process.ProcessOwnership.EXTERNAL,
            pid=23456,
            executable="/usr/bin/llama-server",
            command=(
                "/usr/bin/llama-server",
            ),
            model="external-model",
            port=8080,
            start_time="",
            owner_token="",
            log_path="",
        )

        self.assertFalse(
            controller(
                record,
                "fake-owner-token",
            ),
            "external process must never grant Thrilla control",
        )

    def test_managed_process_control_requires_exact_owner_token(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        record = process.RuntimeProcessRecord(
            ownership=process.ProcessOwnership.THRILLA_MANAGED,
            pid=34567,
            executable="/usr/bin/llama-server",
            command=(
                "/usr/bin/llama-server",
            ),
            model="thrilla-primary",
            port=8080,
            start_time="2026-08-15T00:00:00-05:00",
            owner_token="thrilla-owner-token",
            log_path="/tmp/thrilla.log",
        )

        self.assertTrue(
            process.can_control_process(
                record,
                "thrilla-owner-token",
            ),
            "matching owner token must grant control",
        )

        self.assertFalse(
            process.can_control_process(
                record,
                "wrong-owner-token",
            ),
            "wrong owner token must not grant control",
        )

        self.assertFalse(
            process.can_control_process(
                record,
                "",
            ),
            "empty owner token must not grant control",
        )


if __name__ == "__main__":
    unittest.main()
