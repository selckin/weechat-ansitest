import unittest
from collections import Counter

from ansitest.model import (RESET, Case, State, build_case, describe, marker,
                            path_skip, unique_key, visible)


def make(payload: bytes) -> Case:
    case = Case("hw", "hw/test", "test", payload, [])
    case.id = "T00001"
    return case


class ModelTest(unittest.TestCase):
    def test_marker(self):
        self.assertEqual([marker(i) for i in (0, 8, 9, 17, 18)],
                         ["a1", "a9", "b1", "b9", "c1"])

    def test_build_case(self):
        case = build_case("hw", "hw/x", "desc",
                          [(b"\x1b[1m", RESET.set(bold=True)), (b"\x1b[m", RESET)])
        case.id = "T00001"
        self.assertEqual(case.payload, b"\x1b[1ma1\x1b[ma2")
        self.assertEqual(case.line(), b"T00001 \x1b[1ma1\x1b[ma2\x1b[0m")
        self.assertEqual(case.expected_text(), "a1a2")
        self.assertEqual(case.expect, [("a1", State(bold=True)), ("a2", RESET)])

    def test_json_roundtrip(self):
        case = build_case("hw", "hw/x", "desc",
                          [(b"\x1b[38;2;1;2;3m", RESET.set(fg="#010203"))], skip="why")
        case.id = "T00002"
        case.expect.append(("zz", None))
        self.assertEqual(Case.from_json(case.to_json()), case)

    def test_path_skip(self):
        self.assertIsNone(path_skip(make(b"\x1b[1mx"), "gui"))
        self.assertIn("NUL", path_skip(make(b"a\x00b"), "gui"))
        self.assertIn("LF", path_skip(make(b"a\nb"), "irc"))
        self.assertIn("LF", path_skip(make(b"a\rb"), "gui"))
        self.assertIn("TAB", path_skip(make(b"a\tb"), "gui"))
        self.assertIn("UTF-8", path_skip(make(b"\xa0"), "gui"))
        # Invalid UTF-8 inside a removed sequence (ISO-8859-1 window title).
        self.assertIsNone(path_skip(make(b"A\x1b]0;t\xe9tle\x07B"), "gui"))
        self.assertIsNone(path_skip(make(b"\x0f"), "gui"))
        # A bare C0 control is not skipped: in a terminal it changes no
        # attribute, so the irc path must not turn it into an IRC code.
        self.assertIsNone(path_skip(make(b"\x0f"), "irc"))
        self.assertIn("400", path_skip(make(b"x" * 400), "irc"))
        self.assertIsNone(path_skip(make(b"x" * 400), "gui"))
        case = make(b"x")
        case.skip = "reason"
        self.assertEqual(path_skip(case, "gui"), "reason")

    def test_visible(self):
        self.assertEqual(visible("a\x07b\x0fc\x7fd\x1be"), "abcde")

    def test_describe(self):
        self.assertEqual(describe(RESET), "(default)")
        self.assertEqual(describe(State(fg=0, bold=True)), "fg=0 bold")
        self.assertEqual(describe({"fg": None, "bg": 4, "bold": False}), "bg=4")
        self.assertEqual(describe(None), "(any)")

    def test_unique_key(self):
        seen = Counter()
        self.assertEqual([unique_key("k", seen) for _ in range(3)], ["k", "k#2", "k#3"])


if __name__ == "__main__":
    unittest.main()
