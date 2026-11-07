import unittest

from ansitest.capture.display import REAL_WHITE, compare_display, displayed, parse
from ansitest.model import State


def look(**changes):
    return displayed(State(**changes))


class DisplayTest(unittest.TestCase):
    def test_displayed_light_by_bold(self):
        self.assertEqual(look(fg=1, bold=True)["fg"], 9)
        self.assertEqual(look(fg=9)["fg"], 9)

    def test_parse_screen_line(self):
        case_id, chars = parse("\x1b[39m00:01 \x1b[0mD00001 \x1b[1m\x1b[31ma1\x1b[0m   ")
        self.assertEqual(case_id, "D00001")
        self.assertEqual([(char, state["fg"]) for char, state in chars], [("a", 9), ("1", 9)])

    def test_bold_not_compared_on_light_color(self):
        screen = [("a", look(fg=1, bold=True))]
        self.assertIsNone(compare_display(screen, [("a", look(fg=9))]))
        self.assertIn("fg", compare_display(screen, [("a", look(fg=1))]))

    def test_real_white(self):
        screen = [("a", look())]
        self.assertEqual(compare_display(screen, [("a", look(fg=15))], real_white=False), REAL_WHITE)
        self.assertIn("fg", compare_display(screen, [("a", look(fg=15))], real_white=True))
        # With force_bold, white is shown with the bold of light colors.
        screen_bold = [("a", look(bold=True))]
        self.assertEqual(compare_display(screen_bold, [("a", look(fg=15))], real_white=False,
                                         force_bold=True), REAL_WHITE)
        without_force_bold = compare_display(screen_bold, [("a", look(fg=15))],
                                             real_white=False, force_bold=False)
        self.assertIsNotNone(without_force_bold)
        self.assertNotEqual(without_force_bold, REAL_WHITE)


if __name__ == "__main__":
    unittest.main()
