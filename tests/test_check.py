import io
import unittest
from unittest import mock

from ansitest.check import evaluate, expected_chars
from ansitest.decode.irc import irc_state
from ansitest.divergences import Divergence
from ansitest.model import RESET, State, build_case
from ansitest.project import project
from ansitest.report import escape, report

BOLD = State(bold=True)


def make_case(key="hw/x"):
    case = build_case("hw", key, "desc", [(b"\x1b[1m", BOLD), (b"\x1b[m", RESET)])
    case.id = "T00001"
    return case


def chars(path, *runs):
    return [(char, project(state, path)) for text, state in runs for char in text]


class CheckTest(unittest.TestCase):
    def test_pass(self):
        result = evaluate(make_case(), "gui", chars("gui", ("a1", BOLD), ("a2", RESET)))
        self.assertEqual(result.status, "pass")

    def test_fail_state(self):
        result = evaluate(make_case(), "gui", chars("gui", ("a1", RESET), ("a2", RESET)))
        self.assertEqual(result.status, "fail")
        self.assertIn("bold expected True got False", result.detail)

    def test_fail_text(self):
        result = evaluate(make_case(), "irc", chars("irc", ("a1[1;2", BOLD), ("a2", RESET)))
        self.assertEqual(result.status, "fail")
        self.assertIn("text differs", result.detail)

    def test_missing(self):
        self.assertEqual(evaluate(make_case(), "gui", None).detail, "line not received")

    def test_skip(self):
        case = make_case()
        case.payload += b"\n"
        self.assertEqual(evaluate(case, "irc", None).status, "skip")

    def test_none_state_not_checked(self):
        case = make_case()
        case.expect = [("a1a2", None)]
        result = evaluate(case, "gui", chars("gui", ("a1a2", State(fg=3))))
        self.assertEqual(result.status, "pass")

    def test_divergence(self):
        divergence = Divergence(("gui",), "because", (("a1", RESET), ("a2", RESET)))
        with mock.patch.dict("ansitest.check.DIVERGENCES", {"hw/*": divergence}, clear=True):
            got = chars("gui", ("a1", RESET), ("a2", RESET))
            self.assertEqual(evaluate(make_case(), "gui", got).status, "diverge")
            self.assertEqual(evaluate(make_case(), "irc", chars("irc", ("a1a2", RESET))).status,
                             "fail")
            stale = evaluate(make_case(), "gui", chars("gui", ("a1", BOLD), ("a2", RESET)))
            self.assertEqual(stale.status, "fail")
            self.assertIn("no longer needed", stale.detail)
            other = evaluate(make_case(), "gui", chars("gui", ("a1", State(fg=1)), ("a2", RESET)))
            self.assertEqual(other.status, "fail")
            self.assertIn("because", other.detail)

    def test_divergence_transform(self):
        case = build_case("ti", "ti/x/sgr/1", "dim bold", [(b"\x1b[2;1m", State(dim=True, bold=True))])
        case.id = "T00002"
        divergence = Divergence(("irc",), "why", transform=lambda state: state.set(dim=False))
        with mock.patch.dict("ansitest.check.DIVERGENCES", {"ti/*/sgr/*": divergence}, clear=True):
            bold = evaluate(case, "irc", chars("irc", ("a1", BOLD)))
            self.assertEqual(bold.status, "diverge")
            other = evaluate(case, "irc", chars("irc", ("a1", State(italic=True))))
            self.assertEqual(other.status, "fail")

    def test_irc_expect_replaces_expect_on_irc_path(self):
        case = make_case()
        irc_bold = irc_state(bold=True)
        case.irc_expect = [("a1a2", irc_bold)]
        all_bold = [(char, irc_bold) for char in "a1a2"]
        self.assertEqual(evaluate(case, "irc", all_bold).status, "pass")
        self.assertEqual(evaluate(case, "gui", chars("gui", ("a1", BOLD), ("a2", RESET))).status,
                         "pass")
        self.assertEqual(evaluate(case, "irc", chars("irc", ("a1", BOLD), ("a2", RESET))).status,
                         "fail")

    def test_divergence_irc_expect_only_does_not_apply_to_gui(self):
        divergence = Divergence(("gui", "irc"), "irc only", irc_expect=(("a1a2", irc_state()),))
        with mock.patch.dict("ansitest.check.DIVERGENCES", {"hw/*": divergence}, clear=True):
            wrong_gui = evaluate(make_case(), "gui", chars("gui", ("a1a2", RESET)))
            self.assertEqual(wrong_gui.status, "fail")
            self.assertEqual(evaluate(make_case(), "irc", chars("irc", ("a1a2", RESET))).status,
                             "diverge")

    def test_transform_does_not_apply_to_irc_expect(self):
        case = make_case()
        case.irc_expect = [("a1a2", irc_state(bold=True))]
        divergence = Divergence(("irc",), "why", transform=lambda state: state.set(bold=False))
        with mock.patch.dict("ansitest.check.DIVERGENCES", {"hw/*": divergence}, clear=True):
            result = evaluate(case, "irc", chars("irc", ("a1a2", RESET)))
            self.assertEqual(result.status, "fail")
            self.assertNotIn("divergence", result.detail)

    def test_expected_chars(self):
        self.assertEqual(expected_chars([("ab", None), ("c", BOLD)], "gui"),
                         [("a", None), ("b", None), ("c", project(BOLD, "gui"))])


class BytePathTest(unittest.TestCase):
    def test_keep(self):
        case = make_case()
        self.assertEqual(evaluate(case, "gui-keep", case.payload + b"\x1b[0m").status, "pass")
        result = evaluate(case, "irc-keep", b"\x02a1a2")
        self.assertEqual(result.status, "fail")
        self.assertIn("bytes differ", result.detail)

    def test_keep_gui_replaces_invalid_utf8(self):
        case = make_case()
        case.payload = b"A\x1b]0;t\xe9tle\x07B"
        self.assertEqual(evaluate(case, "gui-keep", b"A\x1b]0;t?tle\x07B\x1b[0m").status, "pass")
        self.assertEqual(evaluate(case, "irc-keep", b"A\x1b]0;t\xe9tle\x07B\x1b[0m").status,
                         "pass")

    def test_strip(self):
        case = make_case()
        self.assertEqual(evaluate(case, "gui-strip", b"a1a2").status, "pass")
        self.assertIn("text differs", evaluate(case, "gui-strip", b"a1").detail)
        self.assertIn("ESC", evaluate(case, "irc-strip", b"a1\x1ba2").detail)
        self.assertIn("WeeChat code", evaluate(case, "gui-strip", b"a1\x1a\x01a2").detail)
        self.assertIn("IRC", evaluate(case, "irc-strip", b"\x02a1a2").detail)

    def test_strip_keeps_si_from_input(self):
        case = make_case()
        case.payload = b"\x1b[0;1m\x0fa1\x1b[m\x0fa2"
        self.assertEqual(evaluate(case, "irc-strip", b"\x0fa1\x0fa2").status, "pass")
        self.assertEqual(evaluate(case, "irc-strip", b"\x0fa1\x0f\x0fa2").status, "fail")

    def test_missing_and_skip(self):
        case = make_case()
        self.assertEqual(evaluate(case, "gui-keep", None).detail, "line not received")
        case.payload += b"x" * 400
        self.assertEqual(evaluate(case, "irc-keep", None).status, "skip")


class ReportTest(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(escape(b"\x1b[1ma\x07\xff"), "\\e[1ma\\x07\\xff")

    def test_report(self):
        case = make_case()
        results = [evaluate(case, "gui", chars("gui", ("a1", BOLD), ("a2", RESET))),
                   evaluate(case, "irc", None)]
        out = io.StringIO()
        failures = report(results, out)
        text = out.getvalue()
        self.assertEqual(failures, 1)
        self.assertIn("FAIL T00001 [irc] hw/x", text)
        self.assertIn("input:    \\e[1ma1\\e[ma2", text)
        self.assertIn("1 failure(s)", text)


if __name__ == "__main__":
    unittest.main()
