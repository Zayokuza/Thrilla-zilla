import importlib
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


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

    def tearDown(self):
        for filename in (
            "thrilla-test.log",
            "runtime-startup.log",
            "first.log",
            "second.log",
        ):
            try:
                Path(filename).unlink()
            except FileNotFoundError:
                pass

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

    def test_spawn_managed_process_captures_stdout_and_stderr(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        with tempfile.TemporaryDirectory() as temp:
            log_path = Path(temp) / "startup.log"

            command = (
                sys.executable,
                "-c",
                (
                    "import sys; "
                    "print('THRILLA-START-OUT', flush=True); "
                    "print('THRILLA-START-ERR', "
                    "file=sys.stderr, flush=True)"
                ),
            )

            handle = process.spawn_managed_process(
                command=command,
                model="startup-test.gguf",
                port=8301,
                log_path=str(log_path),
            )

            try:
                handle.process.wait(
                    timeout=5.0
                )

                self.assertTrue(
                    log_path.exists(),
                    "managed spawn must create startup log",
                )

                content = log_path.read_text(
                    encoding="utf-8"
                )

                self.assertIn(
                    "THRILLA-START-OUT",
                    content,
                )
                self.assertIn(
                    "THRILLA-START-ERR",
                    content,
                )
            finally:
                _stop_test_process(
                    handle.process
                )

    def test_spawn_managed_process_creates_missing_log_directories(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        with tempfile.TemporaryDirectory() as temp:
            log_path = (
                Path(temp)
                / "runtime"
                / "logs"
                / "startup.log"
            )

            command = (
                sys.executable,
                "-c",
                "print('NESTED-LOG-READY', flush=True)",
            )

            try:
                handle = process.spawn_managed_process(
                    command=command,
                    model="nested-log.gguf",
                    port=8302,
                    log_path=str(log_path),
                )
            except FileNotFoundError:
                self.fail(
                    "spawn must create missing log parent directories"
                )

            try:
                handle.process.wait(
                    timeout=5.0
                )

                self.assertTrue(
                    log_path.is_file(),
                )

                self.assertIn(
                    "NESTED-LOG-READY",
                    log_path.read_text(
                        encoding="utf-8"
                    ),
                )
            finally:
                _stop_test_process(
                    handle.process
                )

    def test_spawn_managed_process_appends_existing_startup_log(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        with tempfile.TemporaryDirectory() as temp:
            log_path = Path(temp) / "startup.log"

            log_path.write_text(
                "PREVIOUS-STARTUP\n",
                encoding="utf-8",
            )

            command = (
                sys.executable,
                "-c",
                "print('CURRENT-STARTUP', flush=True)",
            )

            handle = process.spawn_managed_process(
                command=command,
                model="append-test.gguf",
                port=8303,
                log_path=str(log_path),
            )

            try:
                handle.process.wait(
                    timeout=5.0
                )

                content = log_path.read_text(
                    encoding="utf-8"
                )

                self.assertIn(
                    "PREVIOUS-STARTUP",
                    content,
                    (
                        "existing startup log content "
                        "must be preserved"
                    ),
                )

                self.assertIn(
                    "CURRENT-STARTUP",
                    content,
                )
            finally:
                _stop_test_process(
                    handle.process
                )

    def test_shutdown_refuses_unproven_or_external_ownership(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        shutdown = getattr(
            process,
            "shutdown_managed_process",
            None,
        )

        result_type = getattr(
            process,
            "ShutdownResult",
            None,
        )

        self.assertTrue(
            callable(shutdown),
            "shutdown_managed_process must exist",
        )

        self.assertTrue(
            callable(result_type),
            "ShutdownResult must exist",
        )

        with tempfile.TemporaryDirectory() as temp:
            command = (
                sys.executable,
                "-c",
                "import time; time.sleep(30)",
            )

            handle = process.spawn_managed_process(
                command=command,
                model="shutdown-auth.gguf",
                port=8401,
                log_path=str(
                    Path(temp) / "auth.log"
                ),
            )

            try:
                wrong_token = shutdown(
                    handle=handle,
                    owner_token="wrong-owner-token",
                    timeout=0.1,
                )

                self.assertFalse(
                    wrong_token.authorized,
                    "wrong owner token must refuse shutdown",
                )

                self.assertIsNone(
                    handle.process.poll(),
                    "wrong token must not stop managed child",
                )

                external_record = process.RuntimeProcessRecord(
                    ownership=process.ProcessOwnership.EXTERNAL,
                    pid=handle.record.pid,
                    executable=handle.record.executable,
                    command=handle.record.command,
                    model=handle.record.model,
                    port=handle.record.port,
                    start_time=handle.record.start_time,
                    owner_token="",
                    log_path=handle.record.log_path,
                )

                external_handle = process.ManagedProcessHandle(
                    record=external_record,
                    process=handle.process,
                )

                external = shutdown(
                    handle=external_handle,
                    owner_token=handle.record.owner_token,
                    timeout=0.1,
                )

                self.assertFalse(
                    external.authorized,
                    "external ownership must refuse shutdown",
                )

                self.assertIsNone(
                    handle.process.poll(),
                    "external record must not stop child",
                )
            finally:
                _stop_test_process(
                    handle.process
                )

    def test_shutdown_managed_process_terminates_owned_child(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        with tempfile.TemporaryDirectory() as temp:
            command = (
                sys.executable,
                "-c",
                "import time; time.sleep(30)",
            )

            handle = process.spawn_managed_process(
                command=command,
                model="shutdown-owned.gguf",
                port=8402,
                log_path=str(
                    Path(temp) / "owned.log"
                ),
            )

            try:
                result = process.shutdown_managed_process(
                    handle=handle,
                    owner_token=handle.record.owner_token,
                    timeout=1.0,
                )

                self.assertTrue(
                    result.authorized,
                )

                self.assertTrue(
                    result.terminated,
                )

                self.assertFalse(
                    result.escalated,
                )

                self.assertFalse(
                    result.already_stopped,
                )

                self.assertIsNotNone(
                    handle.process.poll(),
                    "owned managed child must stop",
                )

                self.assertEqual(
                    handle.process.returncode,
                    result.returncode,
                )
            finally:
                _stop_test_process(
                    handle.process
                )

    def test_shutdown_managed_process_escalates_after_timeout(self):
        if os.name == "nt":
            self.skipTest(
                "Windows terminate is already forceful"
            )

        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        with tempfile.TemporaryDirectory() as temp:
            log_path = Path(temp) / "ignore-term.log"

            command = (
                sys.executable,
                "-c",
                (
                    "import signal,time; "
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                    "print('TERM-IGNORE-READY', flush=True); "
                    "time.sleep(30)"
                ),
            )

            handle = process.spawn_managed_process(
                command=command,
                model="shutdown-escalate.gguf",
                port=8403,
                log_path=str(log_path),
            )

            try:
                deadline = time.monotonic() + 2.0

                while time.monotonic() < deadline:
                    if (
                        log_path.exists()
                        and "TERM-IGNORE-READY"
                        in log_path.read_text(
                            encoding="utf-8"
                        )
                    ):
                        break

                    time.sleep(0.01)
                else:
                    self.fail(
                        "test child never installed SIGTERM handler"
                    )

                result = process.shutdown_managed_process(
                    handle=handle,
                    owner_token=handle.record.owner_token,
                    timeout=0.05,
                )

                self.assertTrue(
                    result.authorized,
                )

                self.assertTrue(
                    result.terminated,
                )

                self.assertTrue(
                    result.escalated,
                    "shutdown timeout must escalate to kill",
                )

                self.assertIsNotNone(
                    handle.process.poll(),
                )
            finally:
                _stop_test_process(
                    handle.process
                )

    def test_shutdown_refuses_record_pid_mismatch(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        with tempfile.TemporaryDirectory() as temp:
            command = (
                sys.executable,
                "-c",
                "import time; time.sleep(30)",
            )

            original = process.spawn_managed_process(
                command=command,
                model="pid-proof.gguf",
                port=8404,
                log_path=str(
                    Path(temp) / "pid.log"
                ),
            )

            mismatched_record = process.RuntimeProcessRecord(
                ownership=process.ProcessOwnership.THRILLA_MANAGED,
                pid=original.record.pid + 1,
                executable=original.record.executable,
                command=original.record.command,
                model=original.record.model,
                port=original.record.port,
                start_time=original.record.start_time,
                owner_token=original.record.owner_token,
                log_path=original.record.log_path,
            )

            mismatched_handle = process.ManagedProcessHandle(
                record=mismatched_record,
                process=original.process,
            )

            try:
                result = process.shutdown_managed_process(
                    handle=mismatched_handle,
                    owner_token=mismatched_record.owner_token,
                    timeout=0.1,
                )

                self.assertFalse(
                    result.authorized,
                    "PID mismatch must refuse shutdown",
                )

                self.assertIsNone(
                    original.process.poll(),
                    "PID mismatch must not stop actual child",
                )
            finally:
                _stop_test_process(
                    original.process
                )

    def test_shutdown_reports_already_exited_managed_child(self):
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        with tempfile.TemporaryDirectory() as temp:
            command = (
                sys.executable,
                "-c",
                "pass",
            )

            handle = process.spawn_managed_process(
                command=command,
                model="already-stopped.gguf",
                port=8405,
                log_path=str(
                    Path(temp) / "stopped.log"
                ),
            )

            handle.process.wait(
                timeout=5.0
            )

            result = process.shutdown_managed_process(
                handle=handle,
                owner_token=handle.record.owner_token,
                timeout=0.1,
            )

            self.assertTrue(
                result.authorized,
            )

            self.assertTrue(
                result.already_stopped,
                (
                    "already exited process must be "
                    "reported as already stopped"
                ),
            )

            self.assertFalse(
                result.terminated,
            )

            self.assertFalse(
                result.escalated,
            )

            self.assertEqual(
                handle.process.returncode,
                result.returncode,
            )


if __name__ == "__main__":
    unittest.main()
