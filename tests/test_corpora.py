import unittest

from ansitest.cases import ansiregex, libvterm
from ansitest.divergences import KNOWN_LIBVTERM_DIFFS
from ansitest.model import RESET, State
from ansitest.registry import DEFAULT_CORPORA

PEN_TEST = r'''INIT
WANTSTATE

!Bold
PUSH "\e[1m"
  ?pen bold = on
PUSH "\e[22m"
  ?pen bold = off

!DECSTR
PUSH "\e[1;4m"
  ?pen bold = on
PUSH "\e[!p"
  ?pen bold = off
  ?pen underline = 0

!Colour
PUSH "\e[38:2:10:20:30m"
  ?pen foreground = rgb(10,20,30)
PUSH "\e[39m"
  ?pen foreground = rgb(240,240,240,is_default_fg)

!Screen
PUSH "x\e[74m0\e[m"
'''

PARSER_TEST = r'''INIT
WANTPARSER

!Basic text
PUSH "hello"
  text 0x68, 0x65, 0x6c, 0x6c, 0x6f

!C0
PUSH "\x03"
  control 3

!Split write
PUSH "\e[1"
PUSH "2m"
  csi 0x6d 12
PUSH "\x{18}AB\$"
  text 0x41, 0x42, 0x24

!C0
PUSH "\x1f"
  control 0x1f
'''

JS_FIXTURE = r"""// comment
export const vt52Codes = new Map([
	['A', ['Cursor up']],
	['[1m', ['Bold, it\'s']],
]);

export const urxvt = new Map([
	[']710;9x15bold\u{0007}', ['URxvt.keysym.font']],
	['A', ['duplicate']],
]);
"""


class LibvtermTest(unittest.TestCase):
    def test_unescape(self):
        self.assertEqual(libvterm.unescape(r"\e[1m\x{18}\x41\n\$\"\\"),
                         b"\x1b[1m\x18A\n$\"\\")

    def test_parse(self):
        [bold, decstr, colour, screen] = libvterm.parse(PEN_TEST)
        self.assertEqual(bold.name, "Bold")
        self.assertEqual(bold.items, [("push", b"\x1b[1m"), ("expect", "?pen bold = on"),
                                      ("push", b"\x1b[22m"), ("expect", "?pen bold = off")])

    def test_pen_cases(self):
        cases, diffs = libvterm.pen_cases_from_text(PEN_TEST, "t")
        by_key = {case.key: case for case in cases}
        bold = by_key["lvp/t/Bold"]
        self.assertEqual(bold.payload, b"\x1b[1ma1\x1b[22ma2")
        self.assertEqual(bold.expect, [("a1", State(bold=True)), ("a2", RESET)])
        decstr = by_key["lvp/t/DECSTR"]
        self.assertEqual(decstr.expect, [("a1", State(bold=True, underline=True)), ("a2", RESET)])
        colour = by_key["lvp/t/Colour"]
        self.assertEqual(colour.expect, [("a1", State(fg="#0a141e")), ("a2", RESET)])
        screen = by_key["lvp/t/Screen"]
        self.assertEqual(screen.expect, [("x0", RESET), ("a1", RESET)])
        self.assertEqual(diffs, [("lvp/t/DECSTR", 2, "bold"), ("lvp/t/DECSTR", 2, "underline")])

    def test_parser_cases(self):
        cases = libvterm.parser_cases_from_text(PARSER_TEST)
        by_key = {case.key: case for case in cases}
        self.assertEqual(by_key["lvx/Basic text"].expect, [("hello", None)])
        self.assertEqual(by_key["lvx/C0"].expect, [])
        self.assertIn("lvx/C0#2", by_key)
        split = by_key["lvx/Split write"]
        self.assertEqual(split.payload, b"\x1b[12m\x18AB$")
        self.assertEqual(split.expect, [("AB$", None)])

    @unittest.skipUnless(libvterm.available(DEFAULT_CORPORA), "run ./fetch-corpora.sh")
    def test_real_files(self):
        cases = libvterm.cases(DEFAULT_CORPORA)
        keys = [case.key for case in cases]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("lvp/30state_pen/Bold", keys)
        self.assertIn("lvx/CSI 1 arg 1 sub", keys)
        self.assertEqual(set(libvterm.pen_diffs(DEFAULT_CORPORA)), KNOWN_LIBVTERM_DIFFS)


class AnsiRegexTest(unittest.TestCase):
    def test_js_unescape(self):
        self.assertEqual(ansiregex.js_unescape(r"a\u{0007}\u0041\x42\'\\"), "a\x07AB'\\")

    def test_cases(self):
        cases = ansiregex.cases_from_text(JS_FIXTURE)
        by_key = {case.key: case for case in cases}
        self.assertEqual(sorted(by_key), ["ar/urxvt/A", "ar/urxvt/]710;9x15bold\\u{0007}",
                                          "ar/vt52Codes/A", "ar/vt52Codes/[1m"])
        self.assertEqual(by_key["ar/vt52Codes/A"].payload, b"a1\x1bAa2")
        self.assertEqual(by_key["ar/vt52Codes/A"].expect, [("a1", RESET), ("a2", RESET)])
        self.assertEqual(by_key["ar/vt52Codes/[1m"].expect[1], ("a2", State(bold=True)))
        self.assertEqual(by_key["ar/vt52Codes/[1m"].desc, "ansi-regex vt52Codes: Bold, it's")
        self.assertIn(b"\x1b]710;9x15bold\x07", by_key["ar/urxvt/]710;9x15bold\\u{0007}"].payload)

    @unittest.skipUnless(ansiregex.available(DEFAULT_CORPORA), "run ./fetch-corpora.sh")
    def test_real_file(self):
        cases = ansiregex.cases(DEFAULT_CORPORA)
        self.assertGreater(len(cases), 150)
        keys = [case.key for case in cases]
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == "__main__":
    unittest.main()
