import unittest

from ansitest.model import RESET, State
from ansitest.sgr import apply_sgr, plain, runs, tokens

S = RESET.set

APPLY_CASES = [
    # (params, start state, expected state)
    ("", S(bold=True), RESET),
    ("0", S(bold=True, fg=1), RESET),
    (";1", RESET, S(bold=True)),
    ("1;;4", S(italic=True), S(underline=True)),
    ("1;2", RESET, S(bold=True, dim=True)),
    ("22", S(bold=True, dim=True, fg=1), S(fg=1)),
    ("21", S(bold=True), S(bold=True, underline=True)),
    ("4:0", S(underline=True), RESET),
    ("4:00", S(underline=True), RESET),
    ("4:", S(underline=True), RESET),
    ("4:3", RESET, S(underline=True)),
    ("5", RESET, S(blink=True)),
    ("6", RESET, S(blink=True)),
    ("1;3;4;5;7;9", RESET, S(bold=True, italic=True, underline=True, blink=True,
                             reverse=True, strike=True)),
    ("23;24;25;27;29", S(italic=True, underline=True, blink=True, reverse=True,
                         strike=True, bold=True), S(bold=True)),
    ("8;28", RESET, RESET),
    ("31;42", RESET, S(fg=1, bg=2)),
    ("91;102", RESET, S(fg=9, bg=10)),
    ("39;49", S(fg=1, bg=2, bold=True), S(bold=True)),
    ("38;5;196", RESET, S(fg=196)),
    ("38:5:196", RESET, S(fg=196)),
    ("48;5;21", RESET, S(bg=21)),
    ("38;2;255;136;0", RESET, S(fg="#ff8800")),
    ("38:2:255:136:0", RESET, S(fg="#ff8800")),
    ("38:2::255:136:0", RESET, S(fg="#ff8800")),
    ("38:2:0:255:136:0", RESET, S(fg="#ff8800")),
    ("48;2;300;0;999", RESET, S(bg="#ff00ff")),
    ("38:2::256:65535:70000", RESET, S(fg="#ffffff")),
    ("38;5;256;1", S(fg=1), S(fg=1, bold=True)),
    ("38:5:256", S(fg=1), S(fg=1)),
    ("38;5", S(fg=1), S(fg=1)),
    ("1;38;2;1;2", RESET, S(bold=True)),
    ("38;7;1", RESET, RESET),
    ("38:2:1:2", S(fg=1), S(fg=1)),
    ("38;5;196;1;4", RESET, S(fg=196, bold=True, underline=True)),
    ("4;58;2;255;0;0;1", RESET, S(underline=True, bold=True)),
    ("58;5;196;3", RESET, S(italic=True)),
    ("58:2::255:0:0;3", RESET, S(italic=True)),
    ("99999999999999999999;1", RESET, S(bold=True)),
    ("70000;1", RESET, S(bold=True)),
    ("01;031", RESET, S(bold=True, fg=1)),
    ("1:2", RESET, S(bold=True)),
    ("0;4", S(bold=True, fg=1), S(underline=True)),
]


class TokensTest(unittest.TestCase):
    def test_csi(self):
        self.assertEqual(tokens("a\x1b[1;2mb"),
                         [("text", "a"), ("csi", "1;2", "", "m"), ("text", "b")])
        self.assertEqual(tokens("\x1b[2 q"), [("csi", "2", " ", "q")])
        self.assertEqual(tokens("\x1b[?25l"), [("csi", "?25", "", "l")])

    def test_strings(self):
        self.assertEqual(tokens("\x1b]0;t\x07x"), [("string", "\x1b]0;t\x07"), ("text", "x")])
        self.assertEqual(tokens("\x1b]0;t\x1b\\x"), [("string", "\x1b]0;t\x1b\\"), ("text", "x")])
        self.assertEqual(tokens("\x1b]0;t\x1b[1m"),
                         [("string", "\x1b]0;t"), ("csi", "1", "", "m")])
        self.assertEqual(tokens("\x1bPq#0\x1b\\"), [("string", "\x1bPq#0\x1b\\")])
        self.assertEqual(tokens("a\x1b]0;title"), [("text", "a"), ("string", "\x1b]0;title")])

    def test_escapes(self):
        self.assertEqual(tokens("\x1b(0x\x1b7"),
                         [("escape", "\x1b(0"), ("text", "x"), ("escape", "\x1b7")])
        self.assertEqual(tokens("\x1b#8"), [("escape", "\x1b#8")])

    def test_incomplete_csi(self):
        self.assertEqual(tokens("a\x1b[1;2"), [("text", "a"), ("incomplete", "\x1b[1;2")])
        self.assertEqual(tokens("\x1b[1\x1b[3m"),
                         [("incomplete", "\x1b[1"), ("csi", "3", "", "m")])

    def test_lone_esc(self):
        self.assertEqual(tokens("a\x1b"), [("text", "a"), ("escape", "\x1b")])
        self.assertEqual(tokens("a\x1b\x1b[1m"),
                         [("text", "a"), ("escape", "\x1b"), ("csi", "1", "", "m")])

    def test_escape_without_final_byte_keeps_next_char(self):
        self.assertEqual(tokens("\x1b(\u00e9"), [("escape", "\x1b("), ("text", "\u00e9")])

    def test_del_ignored_after_esc(self):
        self.assertEqual(tokens("\x1b\x7f[1m"), [("csi", "1", "", "m")])

    def test_del_ignored_after_intermediate(self):
        self.assertEqual(tokens("\x1b(\x7fBx"), [("escape", "\x1b(B"), ("text", "x")])

    def test_del_ignored_in_csi(self):
        self.assertEqual(tokens("\x1b[1\x7fm"), [("csi", "1", "", "m")])
        self.assertEqual(tokens("\x1b[12\x7f3m"), [("csi", "123", "", "m")])


class ApplyTest(unittest.TestCase):
    def test_apply(self):
        for params, start, expected in APPLY_CASES:
            with self.subTest(params=params):
                self.assertEqual(apply_sgr(start, params), expected)


class RunsTest(unittest.TestCase):
    def test_runs(self):
        result, state = runs("a\x1b[1mb\x1b[>1mc\x1b[?4md\x1b[1 me\x1b[0mf")
        self.assertEqual(result, [("a", RESET), ("bcde", S(bold=True)), ("f", RESET)])
        self.assertEqual(state, RESET)

    def test_runs_start_state(self):
        result, state = runs("x\x1b[22my", S(bold=True))
        self.assertEqual(result, [("x", S(bold=True)), ("y", RESET)])

    def test_plain(self):
        self.assertEqual(plain("\x1b[0mPlugins \x1b[1mloaded\x0f: x"), "Plugins loaded: x")


if __name__ == "__main__":
    unittest.main()
