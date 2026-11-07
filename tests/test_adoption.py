"""Profile discovery, scaffolding, setup check, edit guard and the pre-commit shim, end to end."""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/flow-life"
sys.path.insert(0, str(PLUGIN / "scripts"))
import check_repo  # noqa: E402
import flowconfig  # noqa: E402
import guard_immutable  # noqa: E402
import scaffold  # noqa: E402
import session_report  # noqa: E402
import setup_check  # noqa: E402


def quiet(fn, *args):
    with redirect_stdout(io.StringIO()):
        return fn(*args)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self._env = {k: os.environ.pop(k, None) for k in ("FLOW_LIFE_ROOT", "CLAUDE_PROJECT_DIR")}

    def tearDown(self):
        self.tmp.cleanup()
        for k, v in self._env.items():
            if v is not None:
                os.environ[k] = v

    def init(self, *extra):
        quiet(scaffold.main, ["init", "--dir", str(self.root), "--areas", "visa,housing", *extra])
        return flowconfig.load(self.root)


class Profile(Tmp):
    def test_found_from_a_nested_folder(self):
        cfg = self.init()
        nested = self.root / "visa/processes/active"
        self.assertEqual(flowconfig.load(nested).root, self.root)
        self.assertEqual(cfg.areas, ("visa", "housing"))

    def test_none_without_profile(self):
        self.assertIsNone(flowconfig.load(self.root))

    def test_unknown_setting_is_an_error(self):
        (self.root / ".agents").mkdir()
        (self.root / flowconfig.PROFILE).write_text('profile = 1\nregistr = "x.md"\n')
        with self.assertRaisesRegex(flowconfig.ProfileError, "registr"):
            flowconfig.load(self.root)

    def test_wrong_version_is_an_error(self):
        (self.root / ".agents").mkdir()
        (self.root / flowconfig.PROFILE).write_text("profile = 9\n")
        with self.assertRaisesRegex(flowconfig.ProfileError, "profile = 9"):
            flowconfig.load(self.root)

    def test_settings_override_defaults(self):
        cfg = flowconfig.Config(self.root, {"register": "papers/index.md", "immutable_dirs": ["letters"]})
        self.assertEqual(cfg.register, "papers/index.md")
        self.assertEqual(cfg.immutable_dirs, {"letters"})
        self.assertEqual(cfg.email_log, flowconfig.DEFAULTS["email_log"])


class Scaffold(Tmp):
    def test_plain_folder_passes_its_own_check(self):
        cfg = self.init()
        quiet(scaffold.main, ["process", "visa", "2026-residence-permit", "--dir", str(self.root),
                              "--next", "Book the appointment"])
        self.assertEqual(check_repo.check_all(cfg), [])
        self.assertFalse((self.root / ".git").exists())
        self.assertEqual(os.stat(self.root / "personal-details.md").st_mode & 0o777, 0o600)

    def test_never_overwrites(self):
        (self.root / "README.md").write_text("mine\n")
        self.init()
        self.assertEqual((self.root / "README.md").read_text(), "mine\n")

    def test_rejects_bad_process_name(self):
        self.init()
        with self.assertRaises(SystemExit):
            quiet(scaffold.main, ["process", "visa", "Residence Permit", "--dir", str(self.root)])

    def test_unregistered_document_and_leaked_identifier_are_caught(self):
        cfg = self.init()
        details = self.root / "personal-details.md"
        details.write_text(details.read_text() + "| Passport | `XY1234567` |\n")
        (self.root / "documents/identity").mkdir()
        (self.root / "documents/identity/passport.pdf").write_text("x")
        (self.root / "visa/reference.md").write_text("passport XY 1234567\n")
        problems = check_repo.check_all(cfg)
        self.assertTrue(any("passport.pdf is not listed" in p for p in problems), problems)
        self.assertTrue(any("Passport appears in visa/reference.md" in p for p in problems), problems)


class SetupCheck(Tmp):
    def levels(self):
        return {text.split(":")[0]: level for level, text, _ in setup_check.checks(self.root)}

    def test_missing_profile_fails(self):
        self.assertEqual(self.levels(), {"profile": "FAIL"})

    def test_plain_folder_warns_about_git(self):
        self.init()
        lv = self.levels()
        self.assertEqual(lv["git"], "WARN")
        self.assertEqual(lv["repo check"], "PASS")

    def test_git_with_hooks_passes(self):
        self.init("--git", "--hooks")
        lv = self.levels()
        self.assertEqual(lv["pre-commit"], "PASS")
        self.assertEqual(lv["git"], "INFO")


class Guard(Tmp):
    def test_existing_record_denied_new_allowed_outside_ignored(self):
        self.init()
        sent = self.root / "visa/processes/active/2026-x/sent-emails"
        sent.mkdir(parents=True)
        (sent / "a.md").write_text("x")
        self.assertIsNotNone(guard_immutable.decide(str(sent / "a.md")))
        self.assertIsNone(guard_immutable.decide(str(sent / "new.md")))
        self.assertIsNone(guard_immutable.decide(str(self.root / "README.md")))
        other = Path(tempfile.mkdtemp()) / "sent-emails"
        other.mkdir()
        (other / "b.md").write_text("x")
        self.assertIsNone(guard_immutable.decide(str(other / "b.md")))


class PreCommit(Tmp):
    def git(self, *args):
        env = dict(os.environ, FLOW_LIFE_PLUGIN_ROOT=str(PLUGIN), GIT_AUTHOR_NAME="t",
                   GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        return subprocess.run(["git", *args], cwd=self.root, env=env, capture_output=True, text=True)

    def test_blocks_edited_record_and_failed_check(self):
        self.init("--git", "--hooks")
        sent = self.root / "visa/processes/active/2026-x/sent-emails"
        sent.mkdir(parents=True)
        (sent / "a.md").write_text("x")
        (self.root / "visa/processes/active/2026-x/README.md").write_text("- Status: active\n")
        log = self.root / "shared/correspondence/email-log.md"
        log.write_text(log.read_text() + "| d | sent | s | 0 | `visa/processes/active/2026-x/sent-emails/a.md` |\n")
        self.git("add", "-A")
        self.assertEqual(self.git("commit", "-qm", "init").returncode, 0)
        (sent / "a.md").write_text("changed")
        self.git("add", "-A")
        r = self.git("commit", "-qm", "edit")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("immutable records", r.stderr)
        self.git("checkout", "--", ".")
        self.git("reset", "-q")
        (sent / "a.md").write_text("x")
        (self.root / "documents/stray.pdf").write_text("x")
        self.git("add", "-A")
        r = self.git("commit", "-qm", "stray")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("stray.pdf", r.stdout + r.stderr)


class Report(Tmp):
    def test_deadlines(self):
        readme = ("## Next deadlines\n\n| Date | Area | What |\n|---|---|---|\n"
                  "| 2026-11-10 | Tax | pay |\n| 2026-11-01 | Visa | renew |\n")
        lines = session_report.deadlines(readme, "Next deadlines", date(2026, 11, 5))
        self.assertIn("in 5d", lines[0])
        self.assertIn("4d OVERDUE", lines[1])

    def test_silent_outside_flow_life(self):
        r = subprocess.run([sys.executable, str(PLUGIN / "scripts/session_report.py")],
                           cwd=self.root, capture_output=True, text=True,
                           env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"})
        self.assertEqual((r.returncode, r.stdout), (0, ""))


class Manifests(unittest.TestCase):
    def test_hook_scripts_exist(self):
        hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text())
        commands = [h["command"] for groups in hooks["hooks"].values() for g in groups for h in g["hooks"]]
        self.assertTrue(commands)
        for c in commands:
            script = re.search(r"scripts/(\S+?\.py)", c).group(1)
            self.assertTrue((PLUGIN / "scripts" / script).is_file(), c)

    def test_every_skill_has_frontmatter(self):
        skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
        self.assertTrue(skills)
        for s in skills:
            text = s.read_text()
            self.assertTrue(text.startswith(f"---\nname: {s.parent.name}\ndescription: "), s)
            self.assertLessEqual(len(text.splitlines()), 500, s)

    def test_scripts_named_in_skills_exist(self):
        for s in (PLUGIN / "skills").glob("*/SKILL.md"):
            for script in re.findall(r"scripts/([\w-]+\.py)", s.read_text()):
                self.assertTrue((PLUGIN / "scripts" / script).is_file(), f"{s}: {script}")

    def test_profile_schema_lists_every_default(self):
        schema = (PLUGIN / "references/profile-schema.md").read_text()
        for key in flowconfig.DEFAULTS:
            self.assertIn(f"| `{key}` |", schema, key)


if __name__ == "__main__":
    unittest.main()
