import importlib
import subprocess
import sys
import unittest


def _stop_test_process(child):
    """Stop only a child process created by this test module."""
    if child.poll() is not None:
        return

    child.terminate()

    try:
        child.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5.0)


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

    def test_spawn_managed_process_starts_real_child(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        spawner = getattr(
            process,
            "spawn_managed_process",
            None,
        )
        handle_type = getattr(
            process,
            "ManagedProcessHandle",
            None,
        )

        self.assertTrue(
            callable(spawner),
            "spawn_managed_process must exist",
        )
        self.assertTrue(
            callable(handle_type),
            "ManagedProcessHandle must exist",
        )

        command = (
            sys.executable,
            "-c",
            "import time; time.sleep(30)",
        )

        handle = spawner(
            command=command,
            model="test-model.gguf",
            port=8080,
            log_path="thrilla-test.log",
        )

        try:
            self.assertIsInstance(
                handle,
                handle_type,
            )
            self.assertEqual(
                process.ProcessOwnership.THRILLA_MANAGED,
                handle.record.ownership,
            )
            self.assertEqual(
                handle.process.pid,
                handle.record.pid,
            )
            self.assertGreater(
                handle.record.pid,
                0,
            )
            self.assertIsNone(
                handle.process.poll(),
                "spawned managed child must still be running",
            )
        finally:
            _stop_test_process(
                handle.process
            )

    def test_spawn_managed_process_records_requested_metadata(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        command = (
            sys.executable,
            "-c",
            "import time; time.sleep(30)",
        )

        handle = process.spawn_managed_process(
            command=command,
            model="metadata-model.gguf",
            port=8123,
            log_path="runtime-startup.log",
        )

        try:
            self.assertEqual(
                "metadata-model.gguf",
                handle.record.model,
                "managed record must preserve requested model",
            )
            self.assertEqual(
                8123,
                handle.record.port,
            )
            self.assertEqual(
                "runtime-startup.log",
                handle.record.log_path,
            )
            self.assertEqual(
                command,
                handle.record.command,
            )
            self.assertEqual(
                sys.executable,
                handle.record.executable,
            )
            self.assertTrue(
                handle.record.start_time,
                "managed record must contain start time",
            )
            self.assertTrue(
                handle.record.owner_token,
                "managed record must contain owner token",
            )
            self.assertTrue(
                process.can_control_process(
                    handle.record,
                    handle.record.owner_token,
                )
            )
        finally:
            _stop_test_process(
                handle.process
            )

    def test_each_managed_spawn_gets_unique_owner_token(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        command = (
            sys.executable,
            "-c",
            "import time; time.sleep(30)",
        )

        first = process.spawn_managed_process(
            command=command,
            model="first.gguf",
            port=8201,
            log_path="first.log",
        )

        second = None

        try:
            second = process.spawn_managed_process(
                command=command,
                model="second.gguf",
                port=8202,
                log_path="second.log",
            )

            self.assertNotEqual(
                first.record.owner_token,
                second.record.owner_token,
                "each managed spawn must receive a unique owner token",
            )

            self.assertGreaterEqual(
                len(first.record.owner_token),
                32,
            )
            self.assertGreaterEqual(
                len(second.record.owner_token),
                32,
            )
        finally:
            if second is not None:
                _stop_test_process(
                    second.process
                )

            _stop_test_process(
                first.process
            )

    def test_spawn_managed_process_rejects_empty_command(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        try:
            process.spawn_managed_process(
                command=(),
                model="model.gguf",
                port=8080,
                log_path="runtime.log",
            )
        except Exception as error:
            self.assertIsInstance(
                error,
                ValueError,
                "empty command must raise ValueError",
            )
            self.assertEqual(
                "command must not be empty",
                str(error),
            )
        else:
            self.fail(
                "empty command must be rejected"
            )


if __name__ == "__main__":
    unittest.main()
