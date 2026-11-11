"""Integration tests: set ANSITEST_WEECHAT_BUILD to a WeeChat build directory."""

import os
import re
import unittest

from ansitest.capture.run import run_gui, run_irc
from ansitest.capture.weechat import MIN_VERSION, WeeChat, binary_for_build, features, version
from ansitest.check import evaluate
from ansitest.project import set_profile
from ansitest.model import GUI_PATHS, RESET, State, build_case
from ansitest.sgr import plain
from ansitest.tables import TERM256, rgb_to_term

BUILD = os.environ.get("ANSITEST_WEECHAT_BUILD")


def sample_cases():
    cases = [
        build_case("hw", "hw/t1", "bold", [(b"\x1b[1m", State(bold=True)), (b"\x1b[m", RESET)]),
        build_case("hw", "hw/t2", "256", [(b"\x1b[38;5;196m", State(fg=196))]),
        build_case("hw", "hw/t3", "osc", [(b"", RESET), (b"\x1b]0;x\x07", RESET)]),
    ]
    for number, case in enumerate(cases, 1):
        case.id = f"T{number:05d}"
    return cases


@unittest.skipUnless(BUILD, "set ANSITEST_WEECHAT_BUILD to a WeeChat build directory")
class WeeChatTest(unittest.TestCase):
    def setUp(self):
        self.binary, self.libdir = binary_for_build(BUILD)
        self.version = version(self.binary)[1]
        if self.version < MIN_VERSION:
            self.skipTest(f"WeeChat {self.version} is older than {MIN_VERSION}")
        # Expected results for the features of this WeeChat, like ansicheck.
        with WeeChat(self.binary, self.libdir) as weechat:
            found = features(weechat)
        set_profile(rgb=found["rgb"], irc_colors=found["irc_colors"] or "basic")
        self.addCleanup(set_profile)

    def test_features(self):
        with WeeChat(self.binary, self.libdir) as weechat:
            found = features(weechat)
        self.assertIsInstance(found["rgb"], bool)
        self.assertIn(found["irc_colors"], (None, "basic", "extended", "rgb"))

    def test_gui(self):
        cases = sample_cases()
        with WeeChat(self.binary, self.libdir) as weechat:
            raw = "trigger" in weechat.plugins
            got = run_gui(weechat, cases, raw=raw)
        for path in GUI_PATHS if raw else ("gui-ansi",):
            for case in cases:
                with self.subTest(path=path, key=case.key):
                    self.assertEqual(evaluate(case, path, got[path].get(case.id)).status, "pass")

    def test_irc(self):
        cases = sample_cases()
        with WeeChat(self.binary, self.libdir) as weechat:
            got = run_irc(weechat, cases, self.version)["irc"]
        for case in cases:
            with self.subTest(key=case.key):
                self.assertEqual(evaluate(case, "irc", got.get(case.id)).status, "pass")

    def test_strip_and_keep(self):
        cases = sample_cases()
        for target, color, path in (("gui", "strip", "gui-strip"), ("gui", "ansi", "gui-keep"),
                                    ("irc", "strip", "irc-strip"), ("irc", "ansi", "irc-keep")):
            with WeeChat(self.binary, self.libdir) as weechat:
                if target == "gui":
                    got = run_gui(weechat, cases, color=color)["bytes"]
                else:
                    got = run_irc(weechat, cases, self.version, color=color)["bytes"]
            for case in cases:
                with self.subTest(path=path, key=case.key):
                    self.assertEqual(evaluate(case, path, got.get(case.id)).status, "pass")

    def test_tables_match_weechat(self):
        values = [0xff8800, 0x123456, 0x7f7f7f, 0x000008, 0xfffffe]
        with WeeChat(self.binary, self.libdir) as weechat:
            for index in range(256):
                weechat.send(f"/eval /print TBL t2r {index} ${{info:color_term2rgb,{index}}}")
            for rgb in values:
                for limit in (256, 16):
                    weechat.send(f"/eval /print TBL r2t {rgb}/{limit} "
                                 f"${{info:color_rgb2term,{rgb},{limit}}}")
            lines = weechat.wait_log(
                lambda lines: sum("TBL " in line for line in lines) >= 256 + 2 * len(values), 60)
        found = {}
        for line in lines:
            match = re.search(r"TBL (\w+) (\S+) (-?\d+)", plain(line))
            if match:
                found[(match.group(1), match.group(2))] = int(match.group(3))
        for index in range(256):
            self.assertEqual(found[("t2r", str(index))], TERM256[index], index)
        for rgb in values:
            for limit in (256, 16):
                self.assertEqual(found[("r2t", f"{rgb}/{limit}")], rgb_to_term(rgb, limit))


if __name__ == "__main__":
    unittest.main()
