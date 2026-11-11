import unittest

from ansitest.model import RESET, State
from ansitest.project import PROFILE, project, set_profile
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


class ProfileTest(unittest.TestCase):
    """Projection for a WeeChat with RGB colors and the 99 IRC colors."""

    def tearDown(self):
        set_profile()

    def irc(self, color, irc_colors):
        set_profile(irc_colors=irc_colors)
        return project(State(fg=color), "irc")["fg"]

    def test_default_profile(self):
        self.assertFalse(PROFILE.rgb)
        self.assertEqual(PROFILE.irc_colors, "basic")

    def test_unknown_irc_colors(self):
        with self.assertRaises(ValueError):
            set_profile(irc_colors="other")

    def test_gui_rgb_kept(self):
        set_profile(rgb=True)
        self.assertEqual(project(State(fg="#ff8800", bg=21), "gui")["fg"], "#ff8800")
        self.assertEqual(project(State(fg="#ff8800", bg=21), "gui")["bg"], 21)

    def test_irc_basic_colors_always_0_15(self):
        for irc_colors in ("basic", "extended", "rgb"):
            self.assertEqual(self.irc(9, irc_colors), term_to_irc(9))
            self.assertEqual(self.irc(1, irc_colors), TERM2IRC[1])

    def test_irc_extended(self):
        self.assertEqual(self.irc(196, "extended"), 52)
        self.assertEqual(self.irc(208, "extended"), 53)
        self.assertEqual(self.irc("#ff8800", "extended"), 53)
        # 232 (#080808): nearest is 88 (#000000); 236 (#303030): 91 (#363636).
        self.assertEqual(self.irc(232, "extended"), 88)
        self.assertEqual(self.irc(236, "extended"), 91)

    def test_irc_rgb(self):
        self.assertEqual(self.irc(196, "rgb"), 52)
        self.assertEqual(self.irc(202, "rgb"), "#ff5f00")
        self.assertEqual(self.irc("#ff8800", "rgb"), "#ff8800")

    def test_irc_basic(self):
        self.assertEqual(self.irc(196, "basic"), term_to_irc(196))
        self.assertEqual(self.irc("#ff8800", "basic"), rgb_to_irc(0xff8800))


if __name__ == "__main__":
    unittest.main()
