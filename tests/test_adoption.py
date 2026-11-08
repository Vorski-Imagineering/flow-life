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

    def profile(self, text, root=None):
        root = root or self.root
        (root / ".agents").mkdir(parents=True, exist_ok=True)
        (root / flowconfig.PROFILE).write_text("profile = 1\n" + text)

    def files(self, root=None):
        root = root or self.root
        return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())

    def test_init_follows_existing_profile_register(self):
        self.profile('register = "INDEX.md"\n')
        (self.root / "INDEX.md").write_text("# Index\n")
        out = io.StringIO()
        with redirect_stdout(out):
            scaffold.main(["init", "--dir", str(self.root), "--areas", "visa"])
        self.assertFalse((self.root / "documents/register.md").exists())
        self.assertEqual((self.root / "INDEX.md").read_text(), "# Index\n")
        self.assertIn("kept     INDEX.md", out.getvalue().splitlines())
        readme = (self.root / "README.md").read_text()
        self.assertIn("`INDEX.md`", readme)
        self.assertNotIn("documents/register.md", readme)
        self.assertIn("`INDEX.md`", (self.root / "CLAUDE.md").read_text())
        self.assertEqual(check_repo.check_all(flowconfig.load(self.root)), [])

    def test_init_creates_files_at_profile_paths(self):
        self.profile('register = "papers/index.md"\nemail_log = "papers/mail-log.md"\n'
                     'path_map = "papers/moves.md"\nidentifiers = "private/ids.md"\n'
                     'dashboard = "HOME.md"\n')
        quiet(scaffold.main, ["init", "--dir", str(self.root), "--areas", "visa"])
        for rel in ("papers/index.md", "papers/mail-log.md", "papers/moves.md",
                    "private/ids.md", "HOME.md"):
            self.assertTrue((self.root / rel).is_file(), rel)
        for rel in ("documents/register.md", "shared/correspondence/email-log.md",
                    "docs/path-map.md", "personal-details.md", "README.md"):
            self.assertFalse((self.root / rel).exists(), rel)
        self.assertEqual(os.stat(self.root / "private/ids.md").st_mode & 0o777, 0o600)
        self.assertIn("`papers/index.md`", (self.root / "HOME.md").read_text())
        self.assertEqual(check_repo.check_all(flowconfig.load(self.root)), [])

    def test_init_with_bad_profile_writes_nothing(self):
        self.profile('registr = "x.md"\n')
        with self.assertRaisesRegex(SystemExit, "registr"):
            quiet(scaffold.main, ["init", "--dir", str(self.root), "--git"])
        self.assertEqual(self.files(), [flowconfig.PROFILE])
        self.assertFalse((self.root / ".git").exists())

    def test_init_refuses_path_outside_folder(self):
        folder = self.root / "folder"
        for value in ("../outside.md", "/x.md"):
            self.profile(f'register = "{value}"\n', folder)
            with self.assertRaisesRegex(SystemExit, "register"):
                quiet(scaffold.main, ["init", "--dir", str(folder)])
            self.assertEqual(self.files(folder), [flowconfig.PROFILE])
        self.assertEqual(self.files(), [f"folder/{flowconfig.PROFILE}"])

    def test_init_refuses_unusable_path_settings(self):
        folder = self.root / "folder"
        for line, says in (('register = ["INDEX.md"]', "register"), ('identifiers = ""', "identifiers"),
                           ('dashboard = "."', "dashboard"), ("documents_dir = 5", "documents_dir"),
                           ("register = [", "flow-life.toml")):
            self.profile(line + "\n", folder)
            with self.assertRaisesRegex(SystemExit, says):
                quiet(scaffold.main, ["init", "--dir", str(folder)])
            self.assertEqual(self.files(folder), [flowconfig.PROFILE])

    def test_init_accepts_a_name_starting_with_two_dots(self):
        self.profile('register = "..index.md"\n')
        quiet(scaffold.main, ["init", "--dir", str(self.root)])
        self.assertTrue((self.root / "..index.md").is_file())

    def test_init_ignores_parent_profile(self):
        self.profile('register = "INDEX.md"\n')
        (self.root / "INDEX.md").write_text("# Index\n")
        quiet(scaffold.main, ["init", "--dir", str(self.root / "sub")])
        self.assertTrue((self.root / "sub" / flowconfig.PROFILE).is_file())
        self.assertTrue((self.root / "sub/documents/register.md").is_file())
        self.assertEqual((self.root / "INDEX.md").read_text(), "# Index\n")

    def test_init_without_profile_fills_defaults(self):
        self.init()
        self.assertIn("`documents/register.md`", (self.root / "README.md").read_text())
        for rel in self.files():
            text = (self.root / rel).read_text(errors="ignore")
            for placeholder in ("{register}", "{identifiers}", "{documents_dir}"):
                self.assertNotIn(placeholder, text, rel)

    def test_templates_name_no_default_paths(self):
        for rel in ("README.md", "CLAUDE.md", "documents/register.md"):
            text = (PLUGIN / "templates" / rel).read_text()
            for default in ("documents/register.md", "shared/correspondence/email-log.md",
                            "docs/path-map.md", "personal-details.md"):
                self.assertNotIn(default, text, rel)


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

    def test_missing_outside_target_is_broken_and_named_as_committed(self):
        self.root = self.root / "folder"  # its parent is this test's own, with no config file
        self.root.mkdir()
        self.base()
        os.symlink("../../config", self.root / "visa/cfg.md")
        self.git("add", "visa/cfg.md")
        code, out = self.commit()
        self.assertNotEqual(code, 0)
        self.assertIn("symlink visa/cfg.md -> ../../config: broken", out)

    def test_skip_worktree_entry_does_not_break_the_check(self):
        self.base()
        self.git("update-index", "--skip-worktree", "CLAUDE.md")
        self.touch_readme()
        code, out = self.commit()
        self.assertEqual(code, 0, out)

    def test_intent_to_add_shown_as_rename_is_not_in_the_commit(self):
        self.base()
        self.write("visa/old.md", "Old.\n")
        self.git("add", "visa/old.md")
        self.assertEqual(self.commit()[0], 0)
        (self.root / "visa/old.md").rename(self.root / "visa/new.md")
        self.git("add", "-N", "visa/new.md")
        self.write("visa/notes.md", "See `visa/new.md`.\n")
        self.git("add", "visa/notes.md")
        code, out = self.commit()
        self.assertNotEqual(code, 0)
        self.assertIn("unresolved visa/new.md", out)

    def test_process_readme_keeps_its_content(self):
        self.base()
        prof = self.root / flowconfig.PROFILE
        prof.write_text(prof.read_text() + 'link_text_suffixes = [".html"]\nid_text_suffixes = [".html"]\n')
        self.write("visa/processes/active/2026-x/README.md",
                   "- Status: active\n- Opened: 2026-01-01\n- Closed: —\n- Outcome: —\n- Next: wait\n")
        self.git("add", "-A")
        code, out = self.commit()
        self.assertEqual(code, 0, out)

    def test_no_attribute_filter_runs(self):
        self.base()
        marker = self.root.parent / f"{self.root.name}-smudged"
        self.addCleanup(lambda: marker.exists() and marker.unlink())
        self.git("config", "filter.probe.smudge", f"touch {marker}; cat")
        self.write(".gitattributes", "*.md filter=probe\n")
        self.write("visa/notes.md", "Fine.\n")
        self.git("add", "-A")
        code, out = self.commit()
        self.assertEqual(code, 0, out)
        self.assertFalse(marker.exists())

    def test_staged_copy_in_a_subfolder_repo(self):
        outer = tempfile.TemporaryDirectory()
        self.addCleanup(outer.cleanup)
        top = Path(outer.name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(top)], check=True)
        folder = top / "papers"
        quiet(scaffold.main, ["init", "--dir", str(folder), "--areas", "visa"])
        subprocess.run(["git", "add", "-A"], cwd=folder, check=True)
        r = subprocess.run([sys.executable, str(PLUGIN / "scripts/check_repo.py"), "--staged"],
                           cwd=folder, capture_output=True, text=True,
                           env=dict(os.environ, FLOW_LIFE_ROOT=str(folder)))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_link_out_to_a_directory_can_be_linked_through(self):
        self.root = self.root / "folder"
        self.root.mkdir()
        (self.root.parent / "shared").mkdir()
        (self.root.parent / "shared/form.md").write_text("x")
        self.base()
        os.symlink("../../shared", self.root / "visa/shared")
        self.write("visa/notes.md", "See `visa/shared/form.md`.\n")
        self.git("add", "-A")
        code, out = self.commit()
        self.assertEqual(code, 0, out)

    def test_broken_link_under_tmp_is_not_judged(self):
        self.base()
        (self.root / "tmp").mkdir()
        os.symlink("../../gone", self.root / "tmp/ref")
        self.git("add", "-f", "tmp/ref")
        code, out = self.commit()
        self.assertEqual(code, 0, out)

    def test_missing_blob_is_not_a_traceback(self):
        self.base()
        self.git("update-index", "--add", "--info-only", "--cacheinfo",
                 "100644,1234567890123456789012345678901234567890,visa/ghost.md")
        r = self.run_check("--staged")
        self.assertNotIn("Traceback", r.stderr)

    def test_link_target_not_utf8_is_not_a_traceback(self):
        self.base()
        os.symlink(b"caf\xe9.md", bytes(self.root / "visa/odd.md"))
        self.git("add", "visa/odd.md")
        code, out = self.commit()
        self.assertNotIn("Traceback", out)

    def test_absolute_link_into_folder_needs_its_target_staged(self):
        self.base()
        self.write("visa/draft.md", "Not added yet.\n")
        os.symlink(str(self.root / "visa/draft.md"), self.root / "visa/abs.md")
        self.git("add", "visa/abs.md")
        code, out = self.commit()
        self.assertNotEqual(code, 0)
        self.assertNotIn("flow-life-staged", out)

    def test_absolute_link_through_another_path_to_the_folder(self):
        alias = self.root.parent / f"{self.root.name}-alias"
        os.symlink(self.root, alias)
        self.addCleanup(alias.unlink)
        self.base()
        self.write("visa/draft.md", "Not added yet.\n")
        os.symlink(str(alias / "visa/draft.md"), self.root / "visa/abs.md")
        self.git("add", "visa/abs.md")
        self.assertNotEqual(self.commit()[0], 0)

    def test_missing_link_blob_is_not_a_traceback(self):
        self.base()
        self.git("update-index", "--add", "--info-only", "--cacheinfo",
                 "120000,1234567890123456789012345678901234567890,visa/ghost")
        self.assertNotIn("Traceback", self.run_check("--staged").stderr)

    def test_missing_register_blob_stops_with_a_reason(self):
        self.base()
        self.git("update-index", "--cacheinfo",
                 "100644,1234567890123456789012345678901234567890,documents/register.md")
        r = self.run_check("--staged")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("documents/register.md", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_skip_worktree_register_keeps_its_content(self):
        self.base()
        self.write("documents/tax/a.pdf", "x")
        reg = self.root / "documents/register.md"
        reg.write_text(reg.read_text() + "| a | b | `documents/tax/a.pdf` | | | | | |\n")
        self.git("add", "-A")
        self.assertEqual(self.commit()[0], 0)
        self.git("update-index", "--skip-worktree", "documents/register.md")
        self.touch_readme()
        code, out = self.commit()
        self.assertEqual(code, 0, out)

    def test_link_through_an_untracked_symlink_is_not_judged_by_disk(self):
        elsewhere = tempfile.TemporaryDirectory()
        self.addCleanup(elsewhere.cleanup)
        (Path(elsewhere.name) / "x.md").write_text("x")
        self.base()
        os.symlink(elsewhere.name, self.root / "nas")
        os.symlink("../nas/x.md", self.root / "visa/ref.md")
        self.git("add", "visa/ref.md")
        self.assertNotEqual(self.commit()[0], 0)

    def test_prefix_not_utf8_is_not_a_traceback(self):
        outer = tempfile.TemporaryDirectory()
        self.addCleanup(outer.cleanup)
        top = Path(outer.name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(top)], check=True)
        try:
            folder = top / os.fsdecode(b"pap\xe9rs")
            folder.mkdir()
        except OSError:
            self.skipTest("the file system refuses names that are not UTF-8")
        quiet(scaffold.main, ["init", "--dir", str(folder), "--areas", "visa"])
        (folder / "visa/draft.md").write_text("Draft.\n")
        subprocess.run(["git", "add", "-N", "visa/draft.md"], cwd=folder, check=True)
        self.assertNotIn("visa/draft.md", check_repo.staged_files(flowconfig.load(folder)))

    def test_file_name_not_utf8_is_not_a_traceback(self):
        self.base()
        try:
            (self.root / os.fsdecode(b"visa/caf\xe9.md")).write_text("Fine.\n")
        except OSError:
            self.skipTest("the file system refuses names that are not UTF-8")
        self.git("add", "-A")
        code, out = self.commit()
        self.assertNotIn("Traceback", out)
        self.assertEqual(code, 0, out)

    def test_rename_record_origin_is_not_read_as_a_record(self):
        self.base()
        self.write("1 . old.md", "Old.\n")
        self.git("add", "1 . old.md")
        self.assertEqual(self.commit()[0], 0)
        (self.root / "1 . old.md").rename(self.root / "new.md")
        self.git("add", "-N", "new.md")
        self.touch_readme()
        code, out = self.commit()
        self.assertNotIn("Traceback", out)
        self.assertEqual(code, 0, out)

    def test_deleted_intent_to_add_file_does_not_block(self):
        self.base()
        self.write("documents/tax/draft.pdf", "x")
        self.git("add", "-N", "documents/tax/draft.pdf")
        (self.root / "documents/tax/draft.pdf").unlink()
        self.touch_readme()
        code, out = self.commit()
        self.assertEqual(code, 0, out)

    def test_deleted_staged_empty_file_still_counts(self):
        self.base()
        self.write("documents/tax/empty.pdf", "")
        self.git("add", "documents/tax/empty.pdf")
        (self.root / "documents/tax/empty.pdf").unlink()
        code, out = self.commit()
        self.assertNotEqual(code, 0)
        self.assertIn("empty.pdf is not listed", out)

    def test_intent_to_add_in_a_subfolder_repo(self):
        outer = tempfile.TemporaryDirectory()
        self.addCleanup(outer.cleanup)
        top = Path(outer.name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(top)], check=True)
        folder = top / "papers"
        quiet(scaffold.main, ["init", "--dir", str(folder), "--areas", "visa"])
        (folder / "visa/empty.md").write_text("")
        (folder / "visa/notes.md").write_text("See `visa/empty.md`.\n")
        subprocess.run(["git", "add", "-A"], cwd=folder, check=True)
        entries = check_repo.staged_files(flowconfig.load(folder))
        self.assertIn("visa/empty.md", entries)
        (folder / "visa/draft.md").write_text("Draft.\n")
        subprocess.run(["git", "add", "-N", "visa/draft.md"], cwd=folder, check=True)
        self.assertNotIn("visa/draft.md", check_repo.staged_files(flowconfig.load(folder)))

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
