import unittest

from ansitest.decode.weechat import decode_raw_line, decode_weechat, decode_weechat_chars
from ansitest.model import State
from ansitest.project import project


def gui(**changes):
    return project(State(**changes), "gui")


class WeechatDecodeTest(unittest.TestCase):
    def states(self, message):
        return [state for _, state in decode_weechat_chars(message)]

    def test_attributes(self):
        self.assertEqual(self.states("\x1a\x01\x1a\x06a\x1b\x01b\x1b\x06c"),
                         [gui(bold=True, dim=True), gui(dim=True), gui()])

    def test_reset(self):
        self.assertEqual(self.states("\x1a\x02\x19F|03a\x1cb"),
                         [gui(reverse=True, fg=1), gui()])

    def test_basic_colors(self):
        # WeeChat colors: 03 red (ANSI 1), 16 white (15), 00 default.
        self.assertEqual(self.states("\x19F|03a\x19F|16b\x19B05c\x19F|00\x19B00d"),
                         [gui(fg=1), gui(fg=15), gui(fg=15, bg=2), gui()])

    def test_extended_colors(self):
        self.assertEqual(self.states("\x19F@|00196\x19B@00021a"), [gui(fg=196, bg=21)])

    def test_color_without_keep_flag_resets_attributes(self):
        self.assertEqual(self.states("\x1a\x01\x1a\x03\x19F|03a\x19F00b"),
                         [gui(bold=True, italic=True, fg=1), gui()])
        self.assertEqual(self.states("\x1a\x01\x19F@00009a\x19F@*|00009b"),
                         [gui(fg=9), gui(fg=9, bold=True)])

    def test_color_flags(self):
        self.assertEqual(self.states("\x19F*_03a\x19F@/%|00001b"),
                         [gui(fg=1, bold=True, underline=True),
                          gui(fg=1, bold=True, underline=True, italic=True, blink=True)])

    def text(self, message):
        return "".join(char for char, _ in decode_weechat_chars(message))

    def test_codes_not_written_by_the_ansi_decoder_are_unexpected(self):
        # Review findings 1, 3, 5: fg+bg, pair, emphasis, bar codes, option
        # colors, reset color and basic colors above 16 are not emulated.
        for code in ("\x19*03~05", "\x19*03", "\x19@00001", "\x19E", "\x19bF",
                     "\x1905", "\x19\x1c", "\x19F99", "\x19B17"):
            with self.subTest(code=code):
                self.assertIn("<unexpected \\x19", self.text("a" + code + "b"))

    def test_stray_esc_is_unexpected(self):
        # A bare \x1b before a valid code: WeeChat's display copes, but the
        # line holds a byte that collides with its "remove attribute" code.
        self.assertIn("<unexpected \\x1b\\x1a\\x01", self.text("a\x1b\x1a\x01b"))

    def test_bytes_not_characters(self):
        # Review finding 4: a multibyte character after a code is text.
        chars = decode_weechat_chars("\x19F|03\u00e9a")
        self.assertEqual(chars, [("\u00e9", gui(fg=1)), ("a", gui(fg=1))])
        self.assertEqual(decode_weechat_chars(b"\x19F|03\xc3\xa9"), [("\u00e9", gui(fg=1))])

    def test_ascii_digits_only(self):
        # Review finding 2: non-ASCII digits are not a color (and no crash).
        self.assertIn("<unexpected", self.text("\x19F\u00b2\u00b3a"))
        self.assertIn("<unexpected", self.text("\x19F 3a"))

    def test_decode_with_id(self):
        case_id, chars = decode_weechat("T00001 \x1a\x01a1")
        self.assertEqual(case_id, "T00001")
        self.assertEqual(chars, [("a", gui(bold=True)), ("1", gui(bold=True))])
        self.assertIsNone(decode_weechat("no id"))

    def test_raw_line(self):
        hex_text = "T00001 \x1a\x01a1".encode().hex()
        line = f"\t\t\x1b[0mANSITEST-RAW {hex_text}"
        case_id, chars = decode_raw_line(line)
        self.assertEqual(case_id, "T00001")
        self.assertEqual(len(chars), 2)
        self.assertIsNone(decode_raw_line("\t\tsomething else"))


if __name__ == "__main__":
    unittest.main()
