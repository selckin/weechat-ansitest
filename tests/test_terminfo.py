import unittest

from ansitest.cases import terminfo
from ansitest.model import RESET, State
from tests.helpers import model_mismatch


class TerminfoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {case.key: case for case in terminfo.cases(terminfo.DEFAULT_TERMS)}

    def test_setaf_256(self):
        case = self.cases["ti/xterm-256color/setaf/196"]
        self.assertEqual(case.payload, b"\x1b[38;5;196ma1\x1b[39;49ma2")
        self.assertEqual(case.expect, [("a1", State(fg=196)), ("a2", RESET)])

    def test_setaf_bright(self):
        case = self.cases["ti/xterm-256color/setaf/9"]
        self.assertTrue(case.payload.startswith(b"\x1b[91m"))
        self.assertEqual(case.expect[0][1], State(fg=9))

    def test_direct(self):
        case = self.cases[f"ti/xterm-direct/setaf/{0xff8800}"]
        self.assertTrue(case.payload.startswith(b"\x1b[38:2::255:136:0m"))
        self.assertEqual(case.expect[0][1], State(fg="#ff8800"))
        case = self.cases["ti/xterm-direct/setaf/1"]
        self.assertTrue(case.payload.startswith(b"\x1b[31m"))
        self.assertEqual(case.expect[0][1], State(fg=1))

    def test_sgr_standout(self):
        case = self.cases["ti/xterm-256color/sgr/100001000"]
        self.assertIsNone(case.skip)
        self.assertEqual(case.expect[0][1], State(bold=True, reverse=True))
        self.assertIn("smso", self.cases["ti/screen/sgr/100000000"].skip)

    def test_sgr_attribute_without_capability(self):
        # rxvt-unicode has no dim capability, and its sgr ignores dim.
        case = self.cases["ti/rxvt-unicode-256color/sgr/000011000"]
        self.assertEqual(case.expect[0][1], State(bold=True))

    def test_counts(self):
        self.assertEqual(len([k for k in self.cases if k.startswith("ti/xterm-256color/sgr/")]), 512)
        self.assertEqual(len([k for k in self.cases if k.startswith("ti/xterm-256color/setaf/")]), 256)

    def test_non_sgr(self):
        case = self.cases["ti/xterm-256color/param/cup/9999-9999"]
        self.assertEqual(case.payload, b"a1\x1b[10000;10000Ha2")
        self.assertEqual(case.expect, [("a1", RESET), ("a2", RESET)])
        self.assertNotIn(b"$<", self.cases["ti/xterm-256color/str/flash"].payload)

    def test_missing_term(self):
        [case] = terminfo.cases(("no-such-term-ansitest",))
        self.assertIn("not found", case.skip)

    def test_expected_states_match_model(self):
        for case in self.cases.values():
            if case.skip:
                continue
            with self.subTest(key=case.key):
                self.assertIsNone(model_mismatch(case))


if __name__ == "__main__":
    unittest.main()
