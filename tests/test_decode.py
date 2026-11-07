import unittest

from ansitest.decode.gui import decode_gui, decode_print, message
from ansitest.decode.irc import decode_irc, irc_state
from ansitest.model import State
from ansitest.project import project


class GuiDecodeTest(unittest.TestCase):
    def test_message(self):
        self.assertEqual(message("\t\tabc"), "abc")
        self.assertEqual(message("2026-01-01\tprefix\tabc\tdef"), "abc\tdef")

    def test_decode(self):
        line = "\t\t\x1b[0mT00001 \x1b[1ma1\x1b[0m\x1b[38;5;196ma2\x1b[0m"
        case_id, chars = decode_gui(line)
        self.assertEqual(case_id, "T00001")
        self.assertEqual("".join(char for char, _ in chars), "a1a2")
        self.assertEqual(chars[0][1], project(State(bold=True), "gui"))
        self.assertEqual(chars[3][1], project(State(fg=196), "gui"))

    def test_c0_removed(self):
        _, chars = decode_gui("\t\t\x1b[0mT00002 a\x0fb")
        self.assertEqual("".join(char for char, _ in chars), "ab")

    def test_weechat_22_then_dim(self):
        _, chars = decode_gui("\t\t\x1b[0mT00003 \x1b[1m\x1b[2ma1\x1b[22m\x1b[2ma2")
        self.assertEqual(chars[0][1], project(State(bold=True, dim=True), "gui"))
        self.assertEqual(chars[2][1], project(State(dim=True), "gui"))

    def test_no_id(self):
        self.assertIsNone(decode_gui("\t\tOption changed: x"))


class PrintDecodeTest(unittest.TestCase):
    def test_displayed_color(self):
        line = "\t\t\x1b[0mP00001 \x1b[1m\x1b[38;5;1ma\x1b[22mb\x1b[38;5;9mc\x1b[91md"
        case_id, chars = decode_print(line)
        self.assertEqual(case_id, "P00001")
        self.assertEqual([state["fg"] for _, state in chars], [9, 1, 9, 9])
        self.assertIsNone(decode_print("\t\tT00001 a"))


class IrcDecodeTest(unittest.TestCase):
    def chars(self, message):
        case_id, chars = decode_irc("T00001 " + message)
        self.assertEqual(case_id, "T00001")
        return chars

    def test_toggles(self):
        chars = self.chars("\x02a\x02b\x1d\x1f\x16\x1ec")
        self.assertEqual(chars[0][1], irc_state(bold=True))
        self.assertEqual(chars[1][1], irc_state())
        self.assertEqual(chars[2][1], irc_state(italic=True, underline=True, reverse=True,
                                                strike=True))

    def test_colors(self):
        chars = self.chars("\x0304,02a\x0305b\x03c\x0399,04d")
        self.assertEqual([state for _, state in chars],
                         [irc_state(fg=4, bg=2), irc_state(fg=5, bg=2), irc_state(),
                          irc_state(bg=4)])

    def test_comma_without_digits_is_text(self):
        chars = self.chars("\x0304,a1")
        self.assertEqual("".join(char for char, _ in chars), ",a1")
        self.assertEqual(chars[0][1], irc_state(fg=4))

    def test_reset_and_hex(self):
        chars = self.chars("\x02\x0304a\x0fb\x04ff8800c")
        self.assertEqual([state for _, state in chars],
                         [irc_state(fg=4, bold=True), irc_state(), irc_state(fg="#ff8800")])

    def test_no_id(self):
        self.assertIsNone(decode_irc("hello"))


if __name__ == "__main__":
    unittest.main()
