import unittest

from ansitest.model import RESET, State
from ansitest.project import project
from ansitest.tables import TERM2IRC, rgb_to_irc, rgb_to_term, term_to_irc


class ProjectTest(unittest.TestCase):
    def test_gui(self):
        state = State(fg=1, bg="#ff8800", bold=True, dim=True, italic=True, underline=True,
                      blink=True, reverse=True, strike=True)
        self.assertEqual(project(state, "gui"), {
            "fg": 1, "bg": rgb_to_term(0xff8800), "bold": True, "dim": True,
            "italic": True, "underline": True, "blink": True, "reverse": True})

    def test_irc(self):
        state = State(fg=196, bg=2, bold=True, italic=True, underline=True, blink=True,
                      reverse=True, strike=True)
        self.assertEqual(project(state, "irc"), {
            "fg": term_to_irc(196), "bg": TERM2IRC[2], "bold": True, "italic": True,
            "underline": True, "reverse": True, "strike": True})

    def test_irc_dim_removes_bold(self):
        self.assertFalse(project(State(bold=True, dim=True), "irc")["bold"])

    def test_irc_rgb(self):
        self.assertEqual(project(State(fg="#123456"), "irc")["fg"], rgb_to_irc(0x123456))

    def test_default(self):
        self.assertIsNone(project(RESET, "gui")["fg"])
        self.assertIsNone(project(RESET, "irc")["bg"])

    def test_unknown_path(self):
        with self.assertRaises(ValueError):
            project(RESET, "other")


if __name__ == "__main__":
    unittest.main()
