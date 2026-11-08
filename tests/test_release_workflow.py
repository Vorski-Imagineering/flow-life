"""Release tags: the workflow, the copied gogogo scripts, and that `release.py build` runs here."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools/gogogo"


class ReleaseWorkflow(unittest.TestCase):
    def test_workflow_runs_after_tests_on_main(self):
        text = (ROOT / ".github/workflows/release.yml").read_text()
        for needed in ("workflow_run", "workflows: [tests]", "branches: [main]", "fetch-depth: 0",
                       "contents: write", "conclusion == 'success'", "event == 'push'",
                       "tools/gogogo/release.py --profile .agents/dev-process.md tag --push origin"):
            self.assertIn(needed, text)

    def test_vendored_scripts_are_all_there(self):
        for name in ("release.py", "profile_check.py", "stage_sync.py", "tracker.py", "README.md"):
            self.assertTrue((TOOLS / name).is_file(), name)
        self.assertRegex((TOOLS / "README.md").read_text(), r"\b[0-9a-f]{12}\b")

    def test_release_build_runs_here(self):
        r = subprocess.run([sys.executable, str(TOOLS / "release.py"), "--profile",
                            ".agents/dev-process.md", "build"], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        count = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        self.assertEqual(r.stdout.strip(), count)

    def test_tests_workflow_checks_out_full_history(self):
        self.assertIn("fetch-depth: 0", (ROOT / ".github/workflows/tests.yml").read_text())


if __name__ == "__main__":
    unittest.main()
