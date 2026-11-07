import unittest

from ansitest.cases import programs
from ansitest.decode.irc import irc_state
from ansitest.model import RESET, State
from tests.helpers import model_mismatch


class ProgramsTest(unittest.TestCase):
    def test_from_records(self):
        records = [{"name": "jq", "fixes": [6], "command": "jq -C .", "version": "jq-1.8",
                    "lines": [b"\x1b[1;39m{\x1b[0m".hex(), b"plain".hex()]}]
        first, second = programs.cases_from_records(records)
        self.assertEqual(first.key, "prog/jq/1")
        self.assertEqual(first.expect, [("{", State(bold=True))])
        self.assertIn("fix 6", first.desc)
        self.assertEqual(second.expect, [("plain", RESET)])

    def test_irc_format(self):
        # Expected IRC states written by hand (not by the decoder under test).
        records = [{"name": "irc", "fixes": [], "command": "toilet --irc", "version": "0.3",
                    "format": "irc",
                    "lines": [b"\x0304re\x02d\x0f \x0312,05x\x03 y".hex()]}]
        [case] = programs.cases_from_records(records)
        self.assertEqual(case.irc_expect, [
            ("re", irc_state(fg=4)), ("d", irc_state(fg=4, bold=True)), (" ", irc_state()),
            ("x", irc_state(fg=12, bg=5)), (" y", irc_state())])
        # Elsewhere, what a terminal shows: invisible codes, color digits as text.
        self.assertEqual(case.expected_text(), "04red 12,05x y")

    def test_recorded_file(self):
        cases = programs.cases()
        keys = [case.key for case in cases]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("prog/node-styletext/1", keys)
        for case in cases:
            with self.subTest(key=case.key):
                self.assertIsNone(model_mismatch(case))


if __name__ == "__main__":
    unittest.main()
