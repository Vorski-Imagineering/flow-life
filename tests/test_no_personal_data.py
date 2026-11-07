"""The repo is public and ships to everyone: it must name no person, place, body or case.

The words that would tie it to a particular folder are themselves personal, so they are
not kept here. They come from `.personal-words` at the repo root (git-ignored; one
regular expression per line, `#` for comments) and from the FLOW_LIFE_PERSONAL_WORDS
environment variable (one per line), matched case-insensitively against every file git
would commit. With neither, the test is skipped.
"""
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS_FILE = ROOT / ".personal-words"
SKIPPED = {"LICENSE"}  # standard licence text


def load_words():
    lines = os.environ.get("FLOW_LIFE_PERSONAL_WORDS", "").splitlines()
    if WORDS_FILE.is_file():
        lines += WORDS_FILE.read_text().splitlines()
    return [w.strip() for w in lines if w.strip() and not w.strip().startswith("#")]


def committable_files():
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT,
                         capture_output=True, text=True)
    if out.returncode == 0:
        files = [ROOT / p for p in out.stdout.split("\0") if p and (ROOT / p).is_file()]
    else:
        files = [p for p in ROOT.rglob("*")
                 if p.is_file() and not {".git", "__pycache__"} & set(p.parts) and p != WORDS_FILE]
    return sorted(f for f in files if f.relative_to(ROOT).as_posix() not in SKIPPED)


class NoPersonalData(unittest.TestCase):
    def test_repo_names_nothing_personal(self):
        words = load_words()
        if not words:
            self.skipTest(f"no {WORDS_FILE.name} and no FLOW_LIFE_PERSONAL_WORDS")
        forbidden = re.compile("|".join(f"(?:{w})" for w in words), re.I)
        hits = []
        for f in committable_files():
            for n, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if forbidden.search(line):
                    hits.append(f"{f.relative_to(ROOT)}:{n}: {line.strip()[:80]}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
