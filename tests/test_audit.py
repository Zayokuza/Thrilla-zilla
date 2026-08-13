import tempfile
import unittest
from pathlib import Path

from thrilla.audit import AuditLog


class AuditTests(unittest.TestCase):
    def test_tail_zero_does_not_disclose_all_events(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit = AuditLog(Path(temporary))
            audit.write("one")
            self.assertEqual([], audit.tail(0))
            self.assertEqual("one", audit.tail(1)[0]["event"])


if __name__ == "__main__":
    unittest.main()
