import unittest

from ansitest.tables import TERM256, TERM2IRC, rgb_to_irc, rgb_to_term, term_to_irc


class TablesTest(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(len(TERM256), 256)
        self.assertEqual(len(TERM2IRC), 16)

    def test_palette(self):
        self.assertEqual(TERM256[9], 0xff0000)
        self.assertEqual(TERM256[196], 0xff0000)
        self.assertEqual(TERM256[231], 0xffffff)
        self.assertEqual(TERM256[232], 0x080808)

    def test_exact_match_returns_first_index(self):
        for index, rgb in enumerate(TERM256):
            with self.subTest(index=index):
                self.assertEqual(rgb_to_term(rgb), TERM256.index(rgb))

    def test_limit(self):
        self.assertLess(rgb_to_term(0xff8800, 16), 16)
        self.assertEqual(rgb_to_term(0x123456, 0), 0)
        self.assertEqual(rgb_to_term(0x123456, 1000), rgb_to_term(0x123456, 256))

    def test_irc(self):
        # The projection relies on these being equal: SGR 30-37 use TERM2IRC
        # directly, SGR 38;5;N uses irc_color_convert_term2irc.
        for index in range(16):
            with self.subTest(index=index):
                self.assertEqual(term_to_irc(index), TERM2IRC[index])
        self.assertEqual(rgb_to_irc(0xff0000), TERM2IRC[9])


if __name__ == "__main__":
    unittest.main()
