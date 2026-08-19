"""Stage 5 Task 6 app control contract tests."""

import unittest

from thrilla.app import ThrillaApp
from thrilla.live_ui import ControlAction


class FakeJobs:
    def __init__(self):
        self.calls = []

    def hold(self, job_id):
        self.calls.append(("hold", job_id))

    def resume(self, job_id):
        self.calls.append(("resume", job_id))


class Stage5ControlTests(unittest.TestCase):
    def make_app(self):
        app = ThrillaApp.__new__(ThrillaApp)
        app.job_manager = FakeJobs()
        return app

    def test_hold_requests_safe_checkpoint_pause(self):
        app = self.make_app()
        result = app._handle_control("j1", ControlAction.HOLD)
        self.assertEqual(app.job_manager.calls, [("hold", "j1")])
        self.assertEqual(result, "hold")

    def test_continue_full_resumes_job(self):
        app = self.make_app()
        result = app._handle_control("j1", ControlAction.CONTINUE_FULL)
        self.assertEqual(app.job_manager.calls, [("resume", "j1")])
        self.assertEqual(result, "continue")

    def test_communicate_does_not_pause_or_resume_job(self):
        app = self.make_app()
        result = app._handle_control("j1", ControlAction.COMMUNICATE)
        self.assertEqual(app.job_manager.calls, [])
        self.assertEqual(result, "communicate")

    def test_back_does_not_mutate_job(self):
        app = self.make_app()
        result = app._handle_control("j1", ControlAction.BACK)
        self.assertEqual(app.job_manager.calls, [])
        self.assertEqual(result, "back")


if __name__ == "__main__":
    unittest.main()
