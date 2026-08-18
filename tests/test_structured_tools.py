import tempfile
import unittest
from pathlib import Path

from thrilla.tools import build_default_tool_executor


class StructuredToolExecutorTests(unittest.TestCase):
    def make_executor(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        repo = root / "repo"
        state = root / "state"
        donors = root / "donors"
        for path in (repo, state, donors):
            path.mkdir()
        return root, repo, build_default_tool_executor(repo, state, donors)

    def test_default_executor_registers_stage2_tools(self):
        _, _, executor = self.make_executor()
        self.assertEqual(
            executor.registry.names,
            (
                "file.list",
                "file.read_text",
                "file.search_text",
                "process.run",
                "system.info",
            ),
        )

    def test_read_text_returns_structured_evidence(self):
        _, repo, executor = self.make_executor()
        note = repo / "note.txt"
        note.write_text("alpha beta gamma\n", encoding="utf-8")
        result = executor.execute("file.read_text", {"path": str(note)})
        self.assertTrue(result.ok)
        self.assertIn("alpha beta gamma", result.output["text"])
        self.assertEqual(result.evidence[0].source, str(note.resolve()))

    def test_outside_root_is_rejected_as_structured_failure(self):
        root, _, executor = self.make_executor()
        outside = root.parent / ("outside-stage2-" + root.name + ".txt")
        outside.write_text("outside", encoding="utf-8")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        result = executor.execute("file.read_text", {"path": str(outside)})
        self.assertFalse(result.ok)
        self.assertIn("outside Thrilla allowed roots", result.error)

    def test_text_search_reports_path_line_and_text(self):
        _, repo, executor = self.make_executor()
        note = repo / "code.py"
        note.write_text("first\nneedle here\nthird\n", encoding="utf-8")
        result = executor.execute(
            "file.search_text",
            {"path": str(repo), "query": "needle"},
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.output["matches"][0]["line"], 2)
        self.assertEqual(result.output["matches"][0]["path"], str(note.resolve()))

    def test_read_only_process_command_executes_without_shell(self):
        _, repo, executor = self.make_executor()
        result = executor.execute(
            "process.run",
            {"argv": ["pwd"], "cwd": str(repo)},
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.output["returncode"], 0)
        self.assertEqual(result.output["stdout"].strip(), str(repo.resolve()))

    def test_write_command_is_not_executed(self):
        _, repo, executor = self.make_executor()
        result = executor.execute(
            "process.run",
            {"argv": ["rm", "-rf", "."], "cwd": str(repo)},
        )
        self.assertFalse(result.ok)
        self.assertIn("not enabled in Stage 2", result.error)


if __name__ == "__main__":
    unittest.main()
