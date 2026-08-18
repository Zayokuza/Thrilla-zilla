import unittest
from pathlib import Path


class Stage3CommandSurfaceTests(unittest.TestCase):
    def test_about_and_repair_surface_are_current(self):
        source = Path(__file__).resolve().parent.parent / "thrilla" / "app.py"
        text = source.read_text(encoding="utf-8")

        self.assertNotIn(
            "Expert runtime orchestration is not yet implemented",
            text,
        )
        self.assertIn("/repair <goal>", text)
        self.assertIn("automatic rollback on failure", text)


if __name__ == "__main__":
    unittest.main()
