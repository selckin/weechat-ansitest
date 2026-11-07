import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ansigen(*args: str) -> bytes:
    return subprocess.run([sys.executable, str(ROOT / "ansigen"), "--term", "xterm-256color",
                           *args], capture_output=True, check=True).stdout


class AnsigenTest(unittest.TestCase):
    def test_raw_line(self):
        out = ansigen("--filter", "ti/xterm-256color/setaf/196 ")
        self.assertRegex(out, rb"^T\d{5} \x1b\[38;5;196ma1\x1b\[39;49ma2\x1b\[0m\n$")

    def test_eyeball(self):
        out = ansigen("--eyeball", "--filter", "hw/sgr21 ").decode()
        self.assertIn("# T", out)
        self.assertIn("hw/sgr21", out)
        self.assertIn("#   expect: a1 bold | a2 bold underline", out)

    def test_list_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "m.jsonl"
            out = ansigen("--list", "--manifest", str(manifest), "--filter", "hw/sgr2")
            lines = out.decode().splitlines()
            self.assertEqual(len(lines), 3)
            records = [json.loads(line) for line in manifest.read_text().splitlines()]
            self.assertEqual({r["key"] for r in records},
                             {"hw/sgr21", "hw/sgr22-bold-dim", "hw/sgr22-keeps-color"})


if __name__ == "__main__":
    unittest.main()
