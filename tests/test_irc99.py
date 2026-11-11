import unittest

from ansitest.irc99 import IRC99, irc99_from_term, nearest_irc99


class Irc99Test(unittest.TestCase):
    def test_table(self):
        self.assertEqual([number for number, _, _ in IRC99], list(range(16, 99)))
        terms = [term for _, _, term in IRC99]
        self.assertEqual(len(terms), len(set(terms)))

    def test_from_term(self):
        self.assertEqual(irc99_from_term(196), 52)
        self.assertEqual(irc99_from_term(16), 88)
        self.assertEqual(irc99_from_term(231), 98)
        self.assertIsNone(irc99_from_term(202))
        self.assertIsNone(irc99_from_term(1))

    def test_nearest(self):
        self.assertEqual(nearest_irc99(0xFF0000), 52)
        self.assertEqual(nearest_irc99(0xFF8C00), 53)
        self.assertEqual(nearest_irc99(0xFF8800), 53)
        self.assertEqual(nearest_irc99(0x000000), 88)
        self.assertEqual(nearest_irc99(0xFFFFFF), 98)


if __name__ == "__main__":
    unittest.main()
