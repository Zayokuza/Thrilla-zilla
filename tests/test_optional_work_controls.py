"""Optional live-work controls behavior."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from thrilla.app import ThrillaApp
from thrilla.config import Config
from thrilla.jobs import JobState
from thrilla.router import Route


class OptionalWorkControlsTests(unittest.TestCase):
    def make_app(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        config = Config.defaults()
        config.state_root = str(Path(temp.name) / "state")
        config.donor_root = str(Path(temp.name) / "donors")
        config.save_history = False

        app = ThrillaApp(config)
        self.addCleanup(app.close)
        app._header = Mock()
        return app

    def test_research_runs_without_forcing_work_screen(self):
        app = self.make_app()
        run_research_job = Mock(return_value="research-1")
        app.workflows = SimpleNamespace(
            run_research_job=run_research_job,
        )
        app._track_job = Mock()
        app._active_work_screen = Mock(
            side_effect=AssertionError(
                "research must not force the optional work screen"
            )
        )

        with patch.object(
            app,
            "_input_line",
            side_effect=["/research local ai", "/back"],
        ):
            app.ask()

        run_research_job.assert_called_once_with("local ai")
        app._track_job.assert_called_once_with("research-1")
        app._active_work_screen.assert_not_called()

    def test_repair_runs_without_forcing_work_screen(self):
        app = self.make_app()
        run_repair_job = Mock(return_value="repair-1")
        app.workflows = SimpleNamespace(
            run_repair_job=run_repair_job,
        )
        app._track_job = Mock()
        app._active_work_screen = Mock(
            side_effect=AssertionError(
                "repair must not force the optional work screen"
            )
        )

        with patch.object(
            app,
            "_input_line",
            side_effect=["/repair fix the parser", "/back"],
        ):
            app.ask()

        run_repair_job.assert_called_once_with(
            "fix the parser"
        )
        app._track_job.assert_called_once_with("repair-1")
        app._active_work_screen.assert_not_called()

    def test_normal_chat_is_foreground_and_does_not_open_work_controls(self):
        app = self.make_app()
        app.memory.observe = Mock(return_value=())
        app._direct_provider_answer = Mock(return_value=None)
        app._resolve_ask_answer = Mock(return_value="hello back")
        run_answer_job = Mock(
            side_effect=AssertionError(
                "ordinary chat must not become a background control job"
            )
        )
        app.workflows = SimpleNamespace(
            run_answer_job=run_answer_job,
        )
        app._active_work_screen = Mock(
            side_effect=AssertionError(
                "ordinary chat must not open the work screen"
            )
        )

        decision = SimpleNamespace(
            route=Route.GENERAL,
            confidence=0.99,
            explanation="test",
        )

        with patch(
            "thrilla.app.route_request",
            return_value=decision,
        ), patch.object(
            app,
            "_input_line",
            side_effect=["hello", "/back"],
        ):
            app.ask()

        app._resolve_ask_answer.assert_called_once()
        run_answer_job.assert_not_called()
        app._active_work_screen.assert_not_called()

    def test_completed_background_job_is_surfaced_once(self):
        app = self.make_app()
        snapshot = SimpleNamespace(
            job_id="answer-1",
            kind="answer",
            goal="background answer",
            state=JobState.COMPLETED,
            result="background finished",
            error="",
        )
        app._active_job_ids = ["answer-1"]
        app.job_manager = Mock()
        app.job_manager.snapshot.return_value = snapshot

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            app._surface_completed_jobs()
            app._surface_completed_jobs()

        self.assertEqual(
            output.getvalue().count("background finished"),
            1,
        )

    def test_work_command_remains_optional_control_entry_point(self):
        app = self.make_app()
        app._last_job_id = "research-1"
        snapshot = SimpleNamespace(
            job_id="research-1",
            kind="research",
            goal="local ai",
            state=JobState.RUNNING,
            result=None,
            error="",
        )
        app._active_work_screen = Mock(return_value=snapshot)
        app._render_job_result = Mock(
            return_value="Job research is still running in the background."
        )

        with patch.object(
            app,
            "_input_line",
            side_effect=["/work", "/back"],
        ):
            app.ask()

        app._active_work_screen.assert_called_once_with("research-1")


if __name__ == "__main__":
    unittest.main()
