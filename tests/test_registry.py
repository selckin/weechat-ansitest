import io
import unittest
from pathlib import Path

from ansitest import registry


class RegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.warnings = io.StringIO()
        cls.cases = registry.all_cases(terms=("xterm-256color",),
                                       corpora=Path("/nonexistent-ansitest"),
                                       warn=cls.warnings)

    def test_ids(self):
        self.assertEqual(self.cases[0].id, "T00001")
        ids = [case.id for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(len(i) == 6 and i[0] == "T" for i in ids))

    def test_unique_keys(self):
        keys = [case.key for case in self.cases]
        self.assertEqual(len(keys), len(set(keys)))

    def test_sources(self):
        self.assertEqual({case.source for case in self.cases}, {"ti", "hw", "prog"})

    def test_missing_corpora_warns(self):
        self.assertIn("libvterm", self.warnings.getvalue())
        self.assertIn("ansi-regex", self.warnings.getvalue())

    def test_select(self):
        selected = registry.select(self.cases, r"ti/xterm-256color/setaf/196 ")
        self.assertEqual([case.key for case in selected], ["ti/xterm-256color/setaf/196"])
        self.assertIs(registry.select(self.cases, None), self.cases)


if __name__ == "__main__":
    unittest.main()
