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
    """The hook refuses edited records and a failed check, judged on what is being
    committed (#2), not other files on disk."""

    def base(self):
        self.init("--git", "--hooks")
        self.git("add", "-A")
        self.assertEqual(self.git("commit", "-qm", "base").returncode, 0)

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

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, *args):
        r = self.git("commit", "-qm", "c", *args)
        return r.returncode, r.stdout + r.stderr

    def touch_readme(self):
        self.write("README.md", (self.root / "README.md").read_text() + "\nA line.\n")
        self.git("add", "README.md")

    def run_check(self, *flags):
        return subprocess.run([sys.executable, str(PLUGIN / "scripts/check_repo.py"), *flags],
                              cwd=self.root, capture_output=True, text=True)

    def test_unfinished_untracked_note_does_not_block(self):
        self.base()
        self.write("visa/notes.md", "See `visa/missing.md`.\n")
        self.touch_readme()
        self.assertEqual(self.commit()[0], 0)

    def test_unstaged_edit_does_not_block(self):
        self.base()
        self.write("visa/notes.md", "Fine.\n")
        self.git("add", "visa/notes.md")
        self.assertEqual(self.commit()[0], 0)
        self.write("visa/notes.md", "See `visa/missing.md`.\n")
        self.touch_readme()
        self.assertEqual(self.commit()[0], 0)

    def test_staged_broken_link_blocks(self):
        self.base()
        self.write("visa/notes.md", "See `visa/missing.md`.\n")
        self.git("add", "visa/notes.md")
        code, out = self.commit()
        self.assertNotEqual(code, 0)
        self.assertIn("unresolved visa/missing.md", out)

    def test_partially_staged_judges_staged_version(self):
        self.base()
        self.write("visa/notes.md", "See `visa/missing.md`.\n")
        self.git("add", "visa/notes.md")
        self.write("visa/notes.md", "Fixed.\n")
        self.assertNotEqual(self.commit()[0], 0)
        self.git("add", "visa/notes.md")
        self.write("visa/notes.md", "See `visa/missing.md`.\n")
        self.assertEqual(self.commit()[0], 0)

    def test_staged_document_needs_staged_register_row(self):
        self.base()
        self.write("documents/tax/a.pdf", "x")
        self.git("add", "documents/tax/a.pdf")
        reg = self.root / "documents/register.md"
        reg.write_text(reg.read_text() + "| a | b | `documents/tax/a.pdf` | | | | | |\n")
        code, out = self.commit()
        self.assertNotEqual(code, 0)
        self.assertIn("a.pdf is not listed", out)

    def test_link_to_untracked_file_blocks(self):
        self.base()
        self.write("visa/draft.md", "Not added yet.\n")
        self.write("visa/notes.md", "See `visa/draft.md`.\n")
        self.git("add", "visa/notes.md")
        code, out = self.commit()
        self.assertNotEqual(code, 0)
        self.assertIn("unresolved visa/draft.md", out)

    def test_commit_of_named_paths_uses_git_index_file(self):
        self.base()
        self.write("visa/bad.md", "See `visa/missing.md`.\n")
        self.git("add", "visa/bad.md")
        self.write("README.md", (self.root / "README.md").read_text() + "\nA line.\n")
        self.assertEqual(self.commit("--", "README.md")[0], 0)
        self.assertEqual(self.git("diff", "--cached", "--name-only").stdout.strip(), "visa/bad.md")

    def test_staged_copy_is_private_and_removed(self):
        self.base()
        self.write("documents/tax/a.pdf", "x" * 1000)
        reg = self.root / "documents/register.md"
        reg.write_text(reg.read_text() + "| a | b | `documents/tax/a.pdf` | | | | | |\n")
        self.write("visa/notes.md", "Staged.\n")
        self.git("add", "-A")
        self.write("visa/notes.md", "On disk only.\n")
        git_dir = Path(self.git("rev-parse", "--absolute-git-dir").stdout.strip())
        (git_dir / "flow-life-staged-old").mkdir()
        cfg = flowconfig.load(self.root)
        with check_repo.staged_copy(cfg) as copy:
            self.assertEqual(copy.parent, git_dir)
            self.assertFalse((git_dir / "flow-life-staged-old").exists())
            self.assertEqual((copy / "visa/notes.md").read_text(), "Staged.\n")
            self.assertEqual((copy / "documents/tax/a.pdf").stat().st_size, 0)
        self.assertFalse(copy.exists())
        with self.assertRaises(RuntimeError):
            with check_repo.staged_copy(cfg) as copy:
                raise RuntimeError
        self.assertEqual(list(git_dir.glob("flow-life-staged-*")), [])

    def test_modes_checked_on_real_files(self):
        self.base()
        details = self.root / "personal-details.md"
        os.chmod(details, 0o644)
        self.assertIn("mode: personal-details.md", self.run_check("--staged").stdout)
        os.chmod(details, 0o600)
        self.assertNotIn("mode:", self.run_check("--staged").stdout)

    def test_no_message_names_the_copy(self):
        self.base()
        self.write("visa/notes.md", "See `visa/missing.md`.\n")
        self.git("add", "visa/notes.md")
        code, out = self.commit()
        self.assertNotEqual(code, 0)
        self.assertNotIn("flow-life-staged", out)

    def test_manual_run_still_reads_working_tree(self):
        self.base()
        self.write("visa/notes.md", "See `visa/missing.md`.\n")
        problems = check_repo.check_all(flowconfig.load(self.root))
        self.assertTrue(any("unresolved visa/missing.md" in p for p in problems), problems)

    def test_staged_outside_git_exits_2(self):
        with tempfile.TemporaryDirectory() as plain:
            quiet(scaffold.main, ["init", "--dir", plain])
            r = subprocess.run([sys.executable, str(PLUGIN / "scripts/check_repo.py"), "--staged"],
                               cwd=plain, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("needs a git repository", r.stderr)

    def test_symlink_outside_folder_passes(self):
        self.base()
        elsewhere = tempfile.TemporaryDirectory()
        self.addCleanup(elsewhere.cleanup)
        outside = Path(elsewhere.name) / "outside.md"
        outside.write_text("x")
        os.symlink(os.path.relpath(outside, self.root / "visa"), self.root / "visa/ext.md")
        self.git("add", "visa/ext.md")
        code, out = self.commit()
        self.assertEqual(code, 0, out)

    def test_symlink_without_symlink_support_is_checked(self):
        self.base()
        self.git("config", "core.symlinks", "false")
        os.symlink("../README.md", self.root / "visa/home.md")
        self.git("add", "visa/home.md")
        code, out = self.commit()
        self.assertNotIn("Traceback", out)
        self.assertEqual(code, 0, out)

    def test_symlink_back_into_folder_needs_its_target_staged(self):
        self.base()
        self.write("visa/draft.md", "Not added yet.\n")
        os.symlink(f"../../{self.root.name}/visa/draft.md", self.root / "visa/ext.md")
        self.git("add", "visa/ext.md")
        self.assertNotEqual(self.commit()[0], 0)

    def test_bad_staged_profile_names_the_profile_not_the_copy(self):
        self.base()
        prof = self.root / flowconfig.PROFILE
        good = prof.read_text()
        for bad, says in ((good + "bogus = 1\n", "bogus"), (good + "x = [\n", "Invalid value")):
            prof.write_text(bad)
            self.git("add", flowconfig.PROFILE)
            prof.write_text(good)
            code, out = self.commit()
            self.assertNotEqual(code, 0)
            self.assertIn(".agents/flow-life.toml (staged)", out)
            self.assertIn(says, out)
            self.assertNotIn("flow-life-staged", out)
            self.git("reset", "-q", flowconfig.PROFILE)

    def test_intent_to_add_file_is_not_in_the_commit(self):
        self.base()
        self.write("visa/draft.md", "Draft.\n")
        self.git("add", "-N", "visa/draft.md")
        self.write("visa/notes.md", "See `visa/draft.md`.\n")
        self.git("add", "visa/notes.md")
        code, out = self.commit()
        self.assertNotEqual(code, 0)
        self.assertIn("unresolved visa/draft.md", out)


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
