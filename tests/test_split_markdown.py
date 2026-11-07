import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/flow-life/scripts"))
import split_markdown as sm  # noqa: E402

FENCE = "`" * 3
DOC = ("# T\n\nintro\n\n## A one\n\ntext\n### sub\n\n" + FENCE + "\n## not a heading\n" + FENCE
       + "\n\n## B two\n\nb\n")


class Split(unittest.TestCase):
    def test_split(self):
        pre, secs = sm.split_sections(DOC)
        self.assertEqual(pre, "# T\n\nintro\n\n")
        self.assertEqual([h for h, _ in secs], ["A one", "B two"])
        self.assertIn("## not a heading", secs[0][1])
        self.assertEqual(pre + "".join(s for _, s in secs), DOC)

    def test_assign(self):
        rules = [("A", "x"), ("B t", "y")]
        self.assertEqual(sm.assign("A one", rules), "x")
        self.assertEqual(sm.assign("B two", rules), "y")
        self.assertIsNone(sm.assign("C", rules))


if __name__ == "__main__":
    unittest.main()
