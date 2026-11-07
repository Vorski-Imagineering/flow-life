import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/flow-life/scripts"))
import status  # noqa: E402

README = "# X\n\n- Status: waiting\n- **Opened:** 2026-01-15\n- Next: wait for the licence office\n\nBody\n"


class ReadStatus(unittest.TestCase):
    def test_parse(self):
        s = status.read_status(README)
        self.assertEqual(s["status"], "waiting")
        self.assertEqual(s["opened"], "2026-01-15")
        self.assertEqual(s["next"], "wait for the licence office")


class Scan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, rel, text):
        p = self.root / rel / "README.md"
        p.parent.mkdir(parents=True)
        p.write_text(text)

    def test_ok_and_mismatches(self):
        self.make("licence/processes/active/a", README)
        self.make("licence/processes/closed/b", "- Status: closed\n")
        self.make("visa/processes/active/c", "- Status: closed\n")
        self.make("visa/processes/closed/d", "- Status: active\n")
        self.make("tax/processes/active/e", "no block\n")
        rows = {r["name"]: r for r in status.scan(self.root)}
        self.assertIsNone(rows["a"]["problem"])
        self.assertIsNone(rows["b"]["problem"])
        self.assertIn("closed", rows["c"]["problem"])
        self.assertIn("closed/", rows["d"]["problem"])
        self.assertIn("Status", rows["e"]["problem"])

    def test_missing_readme(self):
        (self.root / "licence/processes/active/z").mkdir(parents=True)
        rows = status.scan(self.root)
        self.assertIn("README", rows[0]["problem"])


if __name__ == "__main__":
    unittest.main()
