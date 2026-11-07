import fnmatch
import unittest

from ansitest.cases import handwritten
from ansitest.divergences import DIVERGENCES
from tests.helpers import model_mismatch


class HandwrittenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = handwritten.cases()

    def test_unique_keys(self):
        keys = [case.key for case in self.cases]
        self.assertEqual(len(keys), len(set(keys)))

    def test_all_keys_prefixed(self):
        self.assertTrue(all(case.key.startswith("hw/") for case in self.cases))

    def test_expected_states_match_model(self):
        for case in self.cases:
            with self.subTest(key=case.key):
                self.assertIsNone(model_mismatch(case))

    def test_some_cases(self):
        by_key = {case.key: case for case in self.cases}
        self.assertEqual(by_key["hw/empty-param-leading"].payload, b"\x1b[;1ma1")
        self.assertEqual(by_key["hw/osc-unterminated"].payload, b"a1\x1b]0;title")
        self.assertGreater(len(self.cases), 100)

    def test_hw_divergences_match_cases(self):
        keys = [case.key for case in self.cases]
        for pattern in DIVERGENCES:
            if pattern.startswith("hw/"):
                with self.subTest(pattern=pattern):
                    self.assertTrue(fnmatch.filter(keys, pattern))


if __name__ == "__main__":
    unittest.main()
