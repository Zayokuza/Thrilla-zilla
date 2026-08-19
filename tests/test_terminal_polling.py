"""Stage 5 terminal polling contract."""

import unittest
import thrilla.terminal as terminal


class TerminalPollingTests(unittest.TestCase):
    def test_nonblocking_key_reader_is_available(self):
        self.assertTrue(callable(getattr(terminal, "read_key_timeout", None)))


if __name__ == "__main__":
    unittest.main()
