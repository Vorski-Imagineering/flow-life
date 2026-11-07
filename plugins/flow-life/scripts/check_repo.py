#!/usr/bin/env python3
"""One check for everything the flow-life storage rules require.

    check_repo.py [--fix-modes]

Run before every commit (the pre-commit hook does). Exit 1 on any problem.
`--fix-modes` first makes the identifiers file and the email archives owner-only.
Works in a git repository (tracked and untracked-but-not-ignored files) or in a
plain folder (every file, skipping .git/ and tmp/).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import flowconfig  # noqa: E402
import pathmap  # noqa: E402
import status  # noqa: E402

IGNORED_NAMES = {".DS_Store", ".gitkeep"}


def is_git(root):
    return subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root,
                          capture_output=True, text=True).stdout.strip() == "true"


def repo_files(root):
    """Root-relative files: git's view in a repository, a folder walk otherwise."""
    root = Path(root)
    if is_git(root):
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"],
                             cwd=root, capture_output=True, text=True).stdout
        return sorted(p for p in out.split("\0") if p and (root / p).is_file())
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [n for n in dirnames if n not in (".git", "tmp", "__pycache__")]
        files += [(Path(dirpath) / n).relative_to(root).as_posix() for n in filenames]
    return sorted(f for f in files if (root / f).is_file())


def in_dirs(path, names):
    return any(part in names for part in Path(path).parts[:-1])


def check_register(cfg, files, register_text):
    prefix = cfg.documents_dir.rstrip("/") + "/"
    return [f"register: {f} is not listed in {cfg.register}" for f in files
            if f.startswith(prefix) and f != cfg.register
            and Path(f).name not in IGNORED_NAMES and f not in register_text]


def check_email_log(cfg, files, log_text):
    problems = []
    for f in files:
        if not in_dirs(f, cfg.email_dirs) or Path(f).name in IGNORED_NAMES:
            continue
        # A .metadata.json sidecar is covered by the log row of its .eml.
        subject = f[:-len(".metadata.json")] + ".eml" if f.endswith(".metadata.json") else f
        if subject not in log_text:
            problems.append(f"email-log: {f} is not listed in {cfg.email_log}")
    return problems


def private_files(cfg, files):
    return [f for f in files if f == cfg.identifiers or in_dirs(f, cfg.email_dirs)]


def check_modes(cfg, files):
    return [f"mode: {f} is readable by group/others (run check_repo.py --fix-modes)"
            for f in private_files(cfg, files) if os.stat(cfg.root / f).st_mode & 0o077]


def load_identifiers(details_text, heading):
    """Rows of the identifiers table under `heading` -> [(label, value)]; None if no heading."""
    if heading not in details_text:
        return None
    ids = []
    for line in details_text.split(heading, 1)[1].splitlines():
        if line.startswith("## "):
            break
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0] not in ("Label", "") and not set(cells[1]) <= set("-: "):
            ids.append((cells[0], cells[1]))
    return ids


def _squash(s):
    return re.sub(r"\s+", "", s)


def id_allowed(cfg, path):
    return (path in cfg.id_always_allowed or path.startswith(cfg.id_allowed_prefixes)
            or "/processes/" in path)


def check_identifiers(cfg, files, ids):
    if ids is None:
        return [f"identifiers: {cfg.identifiers} has no `{cfg.identifier_heading}` table"]
    problems = [f"identifiers: `{label}` in {cfg.identifiers} is too short to check"
                for label, value in ids if len(_squash(value)) < 6]
    needles = [(label, _squash(value)) for label, value in ids if len(_squash(value)) >= 6]
    docs = cfg.documents_dir.rstrip("/") + "/"
    for f in files:
        if id_allowed(cfg, f):
            continue
        for label, needle in needles:
            if needle in _squash(f):
                problems.append(f"identifiers: {label} appears in the path {f}")
        # Evidence carries identifiers by nature; in the documents folder only the register is checked.
        if (Path(f).suffix.lower() not in cfg.id_text_suffixes
                or (f.startswith(docs) and f != cfg.register)):
            continue
        text = _squash((cfg.root / f).read_text(errors="ignore"))
        for label, needle in needles:
            if needle in text:
                problems.append(f"identifiers: {label} appears in {f}; keep it in "
                                f"{cfg.identifiers} or the process folder")
    return problems


def check_status(cfg):
    return [f"status: {r['area']}/processes/{r['folder']}/{r['name']}: {r['problem']}"
            for r in status.scan(cfg.root, cfg.areas) if r["problem"]]


def _read(cfg, rel, problems):
    p = cfg.root / rel
    if not p.exists():
        problems.append(f"missing: {rel} (profile setting points here)")
        return ""
    return p.read_text()


def check_all(cfg):
    files = repo_files(cfg.root)
    problems = []
    register = _read(cfg, cfg.register, problems)
    log = _read(cfg, cfg.email_log, problems)
    details = cfg.root / cfg.identifiers
    ids = load_identifiers(details.read_text(), cfg.identifier_heading) if details.exists() else None
    return (problems
            + check_register(cfg, files, register)
            + check_email_log(cfg, files, log)
            + check_modes(cfg, files)
            + check_identifiers(cfg, files, ids)
            + check_status(cfg)
            + [f"links: {p}" for p in pathmap.check(cfg)])


if __name__ == "__main__":
    cfg = flowconfig.load_or_exit()
    if "--fix-modes" in sys.argv:
        for f in private_files(cfg, repo_files(cfg.root)):
            os.chmod(cfg.root / f, 0o600)
    problems = check_all(cfg)
    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s)", file=sys.stderr)
    sys.exit(1 if problems else 0)
