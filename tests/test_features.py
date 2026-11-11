import unittest

from ansitest.capture.weechat import parse_features


class FeaturesTest(unittest.TestCase):
    def test_main(self):
        lines = ["\t\t\x1b[0m=!= Error: failed to set option \"weechat.color.chat_nick_self\"",
                 "\t\tansitest-irc-colors=",
                 "\t\tansitest-features"]
        self.assertEqual(parse_features(lines), {"rgb": False, "irc_colors": None})

    def test_rgb_colors(self):
        lines = ["\t\t\x1b[0mOption changed: weechat.color.chat_nick_self\x1b[0m = "
                 "\x1b[38;5;6m#ff8800\x1b[0m  (default: white)",
                 "\t\tansitest-irc-colors="]
        self.assertEqual(parse_features(lines), {"rgb": True, "irc_colors": None})

    def test_irc_colors(self):
        lines = ["\t\tOption changed: weechat.color.chat_nick_self = #ff8800",
                 "\t\tansitest-irc-colors=extended"]
        self.assertEqual(parse_features(lines), {"rgb": True, "irc_colors": "extended"})


if __name__ == "__main__":
    unittest.main()
