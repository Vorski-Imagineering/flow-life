import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/flow-life/scripts"))
import check_repo  # noqa: E402
import flowconfig  # noqa: E402

CFG = flowconfig.Config("/nonexistent")


class RegisterTest(unittest.TestCase):
    def test_unlisted_document_is_reported(self):
        files = ["documents/tax/a.pdf", "documents/tax/b.pdf", "documents/register.md",
                 "documents/medical/.gitkeep", "licence/README.md"]
        problems = check_repo.check_register(CFG, files, "| `documents/tax/a.pdf` |")
        self.assertEqual(len(problems), 1)
        self.assertIn("documents/tax/b.pdf", problems[0])


class EmailLogTest(unittest.TestCase):
    def test_unlogged_email_is_reported(self):
        files = ["x/processes/active/p/sent-emails/a.md", "x/processes/active/p/received-emails/b.md"]
        problems = check_repo.check_email_log(CFG, files, "`x/processes/active/p/sent-emails/a.md`")
        self.assertEqual(len(problems), 1)
        self.assertIn("received-emails/b.md", problems[0])

    def test_sidecar_is_covered_by_its_eml(self):
        files = ["x/processes/active/p/received-emails/1a.eml",
                 "x/processes/active/p/received-emails/1a.metadata.json"]
        log = "`x/processes/active/p/received-emails/1a.eml`"
        self.assertEqual(check_repo.check_email_log(CFG, files, log), [])

    def test_files_outside_email_folders_are_ignored(self):
        self.assertEqual(check_repo.check_email_log(CFG, ["x/processes/active/p/drafts/a.md"], ""), [])


class IdentifierTest(unittest.TestCase):
    def test_loads_table_rows(self):
        text = ("# x\n\n| Tax ID | 111 |\n\n" + CFG.identifier_heading
                + "\n\n| Label | Value |\n|---|---|\n| Tax ID | `123 456 789` |\n")
        self.assertEqual(check_repo.load_identifiers(text, CFG.identifier_heading), [("Tax ID", "123 456 789")])

    def test_missing_table(self):
        self.assertIsNone(check_repo.load_identifiers("# x\n", CFG.identifier_heading))

    def test_allowed_locations(self):
        for ok in ("personal-details.md", "shared/correspondence/email-log.md",
                   "licence/processes/active/p/drafts/a.md", "docs/path-map.md"):
            self.assertTrue(check_repo.id_allowed(CFG, ok), ok)
        for bad in ("licence/reference.md", "README.md", "documents/register.md", "licence/README.md"):
            self.assertFalse(check_repo.id_allowed(CFG, bad), bad)


if __name__ == "__main__":
    unittest.main()
