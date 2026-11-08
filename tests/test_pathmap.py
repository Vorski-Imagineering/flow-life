import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/flow-life/scripts"))
import flowconfig  # noqa: E402
import pathmap  # noqa: E402

TOP = {"documents", "licence", "visa", "shared", "docs", "todo.md"}
STALE = [r"documents/\d{2}-", "Documents/Old Paperwork", "working-notes/",
         "output/pdf", r"document-index\.md"]


def cfg(root="/nonexistent", **settings):
    return flowconfig.Config(root, settings)

MAP_MD = """# Path map

| Old | New |
|---|---|
| `documents/01-identity/` | `documents/identity/` |
| `documents/05-correspondence/sent-emails/a.md` | `visa/processes/active/x/sent-emails/a.md` |
| `documents/05-correspondence/` | `shared/correspondence/` |
| `visa/processes/active/x/` | `visa/processes/closed/x/` |
"""


class LoadAndMap(unittest.TestCase):
    def setUp(self):
        self.rows = pathmap.load_path_map(MAP_MD)

    def test_load(self):
        self.assertEqual(len(self.rows), 4)
        self.assertEqual(self.rows[0], ("documents/01-identity/", "documents/identity/"))

    def test_prefix(self):
        self.assertEqual(
            pathmap.map_forward("documents/01-identity/passport.pdf", self.rows),
            "documents/identity/passport.pdf")

    def test_longest_match_wins(self):
        self.assertEqual(
            pathmap.map_forward("documents/05-correspondence/sent-emails/a.md", self.rows),
            "visa/processes/closed/x/sent-emails/a.md")  # also chains through the close row

    def test_chain_through_later_close(self):
        self.assertEqual(
            pathmap.map_forward("visa/processes/active/x/README.md", self.rows),
            "visa/processes/closed/x/README.md")

    def test_prefix_needs_boundary(self):
        # "documents/01-identity-old/" must not match the "documents/01-identity/" prefix
        self.assertEqual(
            pathmap.map_forward("documents/01-identity-old/p.pdf", self.rows),
            "documents/01-identity-old/p.pdf")

    def test_unmapped_unchanged(self):
        self.assertEqual(pathmap.map_forward("README.md", self.rows), "README.md")

    def test_reverse(self):
        self.assertEqual(
            pathmap.map_reverse("documents/identity/passport.pdf", self.rows),
            "documents/01-identity/passport.pdf")
        self.assertEqual(
            pathmap.map_reverse("visa/processes/closed/x/sent-emails/a.md", self.rows),
            "documents/05-correspondence/sent-emails/a.md")


class Tokens(unittest.TestCase):
    def paths(self, text, suffix=".md"):
        return [(t.path, t.suffix) for t in pathmap.extract_tokens(text, suffix)]

    def test_backtick_and_link(self):
        text = "see `documents/03-residence/x.pdf` and [y](../08-licence/y.md#top)"
        self.assertEqual(self.paths(text),
                         [("documents/03-residence/x.pdf", ""), ("../08-licence/y.md", "#top")])

    def test_line_suffix(self):
        self.assertEqual(self.paths("`reference.md:120` `a/b.md:12`"), [("a/b.md", ":12")])

    def test_rejects_non_paths(self):
        text = "`git mv a b` `https://x.pt/a` `mailto:a@b` `/abs/p` `~/x` `*.pdf` `a/<b>` `plain`"
        self.assertEqual(self.paths(text), [])

    def test_rejects_identifiers_dates_urls_without_file_extension(self):
        text = ("`123456/2026` `12/08/2026` `AM/B/f/k/q` `192.0.2.120/30` `Invoice/Receipt` "
                "`example.org/check-licence` `.../Portal/Forms/List.aspx`")
        self.assertEqual(self.paths(text), [])

    def test_rejects_bare_relative_prefix(self):
        self.assertEqual(self.paths("`../` `./` `../../`"), [])

    def test_accepts_dirs_and_files(self):
        self.assertEqual(self.paths("`a/b/` `a/b.md`"), [("a/b/", ""), ("a/b.md", "")])

    def test_html(self):
        text = '<code>documents/03-residence/</code> <a href="../x/y.pdf">'
        self.assertEqual(self.paths(text, ".html"),
                         [("documents/03-residence/", ""), ("../x/y.pdf", "")])

    def test_py_strings(self):
        text = 'SOURCE = ROOT / "documents/03-residence/p.pdf"\nX = "a/b.txt"\n'
        toks = pathmap.extract_tokens(text, ".py")
        self.assertEqual([t.path for t in toks], ["documents/03-residence/p.pdf", "a/b.txt"])

    def test_offsets(self):
        text = "x `documents/a/b.pdf` y"
        t = pathmap.extract_tokens(text, ".md")[0]
        self.assertEqual(text[t.start:t.end], "documents/a/b.pdf")


class Resolve(unittest.TestCase):
    def test_relative(self):
        self.assertEqual(
            pathmap.resolve("../03-residence/x.jpg", "documents/05-correspondence/n.md", TOP),
            "documents/03-residence/x.jpg")

    def test_root_relative(self):
        self.assertEqual(pathmap.resolve("documents/x.pdf", "licence/processes/active/p/todo.md", TOP),
                         "documents/x.pdf")

    def test_bare_relative_dir(self):
        self.assertEqual(
            pathmap.resolve("sent-emails/a.md", "documents/05-correspondence/email-log.md", TOP),
            "documents/05-correspondence/sent-emails/a.md")

    def test_ignored(self):
        self.assertIsNone(pathmap.resolve("tmp/a.pdf", "todo.md", TOP))
        self.assertIsNone(pathmap.resolve("../../../outside", "a/b.md", TOP))

    def test_trailing_slash_kept(self):
        self.assertEqual(pathmap.resolve("../03-residence/", "documents/05-c/n.md", TOP),
                         "documents/03-residence/")


class Excluded(unittest.TestCase):
    def test_excluded(self):
        c = cfg(link_excluded_files=["AGENTS.md"],
                link_excluded_prefixes=[".git/", "tmp/", "docs/superpowers/", ".superpowers/", "tools/tests/"])
        for p in ["tmp/a.md", ".git/x", "docs/path-map.md", "docs/superpowers/specs/s.md", "AGENTS.md",
                  ".superpowers/sdd/x/progress.md", "tools/tests/t.py",
                  "licence/processes/active/x/sent-emails/a.md",
                  "documents/05-correspondence/received-emails/b.md",
                  "licence/processes/active/x/submissions/portal-responses/r.md"]:
            self.assertTrue(pathmap.is_excluded(p, c), p)

    def test_included(self):
        c = cfg()
        for p in ["todo.md", "shared/correspondence/README.md",
                  "documents/05-correspondence/sent-emails/README.md",
                  "licence/processes/active/x/drafts/d.md"]:
            self.assertFalse(pathmap.is_excluded(p, c), p)


class ExcludedDirs(unittest.TestCase):
    def test_excluded_dirs_any_depth(self):
        c = cfg(link_excluded_dirs=["sources"])
        for p in ["a/sources/p.html", "a/b/sources/x/y.md", "a/sources/README.md", "a/sources/"]:
            self.assertTrue(pathmap.is_excluded(p, c), p)
        for p in ["a/README.md", "sources.md", "a/sourcesx/p.html"]:
            self.assertFalse(pathmap.is_excluded(p, c), p)

    def test_excluded_dirs_default_skips_nothing(self):
        self.assertFalse(pathmap.is_excluded("a/sources/p.html", cfg()))

    def test_excluded_dirs_reporter_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "a/sources").mkdir(parents=True)
            (r / "a/sources/p.html").write_text('<a href="a/sources/gone.html">x</a>\n')
            (r / "a/README.md").write_text("See `a/sources/p.html`.\n")
            self.assertEqual(pathmap.check(cfg(r, link_excluded_dirs=["sources"])), [])
            problems = pathmap.check(cfg(r))
            self.assertTrue(any(p.startswith("a/sources/p.html:") and "unresolved" in p
                                for p in problems), problems)


class EndToEnd(unittest.TestCase):
    """Builds a tiny repo, moves things, runs rewrite + check."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        r = self.root
        (r / "documents/03-residence").mkdir(parents=True)
        (r / "documents/03-residence/card.jpg").write_text("x")
        (r / "documents/09-visit/print").mkdir(parents=True)
        os.symlink("../../03-residence/card.jpg", r / "documents/09-visit/print/01.jpg")
        (r / "documents/05-correspondence/sent-emails").mkdir(parents=True)
        (r / "documents/05-correspondence/sent-emails/e.md").write_text(
            "immutable `../../03-residence/card.jpg`\n")
        (r / "documents/05-correspondence/note.md").write_text(
            "attach `../03-residence/card.jpg` and `documents/03-residence/card.jpg:3`\n"
            "and `documents/03-residence/card.jpgx` stays\n")
        (r / "docs").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def move(self, src, dst):
        (self.root / dst).parent.mkdir(parents=True, exist_ok=True)
        os.rename(self.root / src, self.root / dst)

    def test_rewrite_and_check(self):
        r = self.root
        (r / "docs/path-map.md").write_text(
            "| Old | New |\n|---|---|\n"
            "| `documents/03-residence/` | `documents/residence/` |\n"
            "| `documents/09-visit/` | `visa/processes/active/p/visits/v/` |\n"
            "| `documents/05-correspondence/note.md` | `visa/processes/active/p/drafts/note.md` |\n"
            "| `documents/05-correspondence/sent-emails/` | `visa/processes/active/p/sent-emails/` |\n")
        self.move("documents/03-residence", "documents/residence")
        self.move("documents/09-visit", "visa/processes/active/p/visits/v")
        self.move("documents/05-correspondence/note.md", "visa/processes/active/p/drafts/note.md")
        self.move("documents/05-correspondence/sent-emails", "visa/processes/active/p/sent-emails")

        problems_before = pathmap.check(cfg(r, stale_patterns=STALE))
        self.assertTrue(any("01.jpg" in p for p in problems_before))  # broken symlink found

        pathmap.rewrite(cfg(r), dry_run=False)

        note = (r / "visa/processes/active/p/drafts/note.md").read_text()
        self.assertIn("`documents/residence/card.jpg`", note)
        self.assertIn("`documents/residence/card.jpg:3`", note)
        self.assertIn("`documents/03-residence/card.jpgx`", note)  # unresolvable: left alone
        link = os.readlink(r / "visa/processes/active/p/visits/v/print/01.jpg")
        self.assertEqual(link, "../../../../../../../documents/residence/card.jpg")
        self.assertTrue((r / "visa/processes/active/p/visits/v/print/01.jpg").exists())
        email = (r / "visa/processes/active/p/sent-emails/e.md").read_text()
        self.assertEqual(email, "immutable `../../03-residence/card.jpg`\n")  # untouched

        problems_after = pathmap.check(cfg(r, stale_patterns=STALE))
        links = [p for p in problems_after if "stale" not in p]  # note.md keeps old text on purpose
        self.assertEqual([p for p in links if "card.jpgx" not in p], [])
        self.assertEqual(len(links), 1)

    def test_symlink_survives_two_successive_moves(self):
        r = self.root
        rows = ("| Old | New |\n|---|---|\n"
                "| `documents/09-visit/` | `visa/processes/active/p/visits/v/` |\n")
        (r / "docs/path-map.md").write_text(rows)
        self.move("documents/09-visit", "visa/processes/active/p/visits/v")
        pathmap.rewrite(cfg(r), dry_run=False)
        # second step: the link target moves later
        (r / "docs/path-map.md").write_text(
            rows + "| `documents/03-residence/` | `documents/residence/` |\n")
        self.move("documents/03-residence", "documents/residence")
        pathmap.rewrite(cfg(r), dry_run=False)
        self.assertTrue((r / "visa/processes/active/p/visits/v/print/01.jpg").exists())
        pathmap.rewrite(cfg(r), dry_run=False)  # idempotent
        self.assertTrue((r / "visa/processes/active/p/visits/v/print/01.jpg").exists())

    def test_check_flags_stale_old_layout_text_even_in_fences_and_absolute_paths(self):
        r = self.root
        (r / "docs/path-map.md").write_text("| Old | New |\n|---|---|\n")
        (r / "README.md").write_text(
            "```\ncd documents/11-licence-office-visit\n```\n"
            "see /Users/x/Documents/Old Paperwork/documents/02-a/b.jpg\n"
            "also `document-index.md` and working-notes/x.md\n")
        problems = pathmap.check(cfg(r, stale_patterns=STALE))
        self.assertEqual(len([p for p in problems if "stale" in p and p.startswith("README.md")]), 3)

    def test_check_reports_dangling_map_target(self):
        r = self.root
        (r / "docs/path-map.md").write_text(
            "| Old | New |\n|---|---|\n| `a/x.md` | `b/x.md` |\n")
        self.assertTrue(any("b/x.md" in p for p in pathmap.check(cfg(r, stale_patterns=STALE))))


if __name__ == "__main__":
    unittest.main()
