#!/usr/bin/env python3
"""One check for everything the flow-life storage rules require.

    check_repo.py [--fix-modes] [--staged]

Run before every commit (the pre-commit hook does). Exit 1 on any problem.
`--fix-modes` first makes the identifiers file and the email archives owner-only.
Works in a git repository (tracked and untracked-but-not-ignored files) or in a
plain folder (every file, skipping .git/ and tmp/).

`--staged` judges the index (what is being committed) in a copy under the git
directory; the pre-commit hook uses it. Without it, the working tree is checked.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from contextlib import contextmanager
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


def check_all(cfg, modes=True):
    files = repo_files(cfg.root)
    problems = []
    register = _read(cfg, cfg.register, problems)
    log = _read(cfg, cfg.email_log, problems)
    details = cfg.root / cfg.identifiers
    ids = load_identifiers(details.read_text(), cfg.identifier_heading) if details.exists() else None
    return (problems
            + check_register(cfg, files, register)
            + check_email_log(cfg, files, log)
            + (check_modes(cfg, files) if modes else [])
            + check_identifiers(cfg, files, ids)
            + check_status(cfg)
            + [f"links: {p}" for p in pathmap.check(cfg)])


STAGED_PREFIX = "flow-life-staged-"


def _git(root, *args, **kw):
    """git in the folder's root, with the inherited environment: during a commit git sets
    GIT_INDEX_FILE (relative to the root) to the index being committed."""
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True, **kw)


def _intent_to_add(root):
    """Paths, relative to root, of intent-to-add entries (`git add -N`), whether or not
    the file is still on disk: status shows them with no staged change (X is '.') though
    HEAD does not have them. Read with --no-optional-locks, so the index is not rewritten."""
    out = _git(root, "--no-optional-locks", "status", "--porcelain=v2", "-z",
               "--untracked-files=no").stdout.decode()
    candidates = {rec.split(" ", 8)[8] for rec in out.split("\0") if rec.startswith("1 .")}
    if not candidates:
        return set()
    born = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"], cwd=root,
                          capture_output=True).returncode == 0
    in_head = (set(_git(root, "ls-tree", "-r", "--full-tree", "--name-only", "-z", "HEAD")
                   .stdout.decode().split("\0")) if born else set())
    prefix = _git(root, "rev-parse", "--show-prefix", text=True).stdout.strip()
    return {p[len(prefix):] for p in candidates - in_head if p.startswith(prefix)}


def staged_files(cfg):
    """{path: mode} of what the commit will contain, read from the index without writing
    to it. Submodules and intent-to-add entries are left out."""
    entries = {}
    for rec in _git(cfg.root, "ls-files", "-s", "-z").stdout.decode().split("\0"):
        if not rec:
            continue
        meta, path = rec.split("\t", 1)
        mode = meta.split()[0]
        if mode != "160000":
            entries[path] = mode
    for path in _intent_to_add(cfg.root):
        entries.pop(path, None)
    return entries


@contextmanager
def staged_copy(cfg, entries=None, redirected=None):
    """A copy of the index under the git directory, removed afterwards. Text files the
    checks read keep their content; every other file is an empty stand-in, since the
    register and link checks only need it to exist. A link out of the folder is pointed
    where it points on disk; `redirected`, when given, gets {path: (new target, committed
    target)} for each."""
    git_dir = Path(_git(cfg.root, "rev-parse", "--absolute-git-dir", text=True).stdout.strip())
    for old in git_dir.glob(STAGED_PREFIX + "*"):
        shutil.rmtree(old, ignore_errors=True)
    dest = Path(tempfile.mkdtemp(prefix=STAGED_PREFIX, dir=git_dir))
    try:
        entries = staged_files(cfg) if entries is None else entries
        suffixes = {s.lower() for s in cfg.link_text_suffixes | cfg.id_text_suffixes}
        named = {cfg.register, cfg.email_log, cfg.identifiers, cfg.path_map, cfg.dashboard,
                 flowconfig.PROFILE}
        real = [p for p, mode in entries.items()
                if mode == "120000" or p in named or Path(p).suffix.lower() in suffixes]
        if real:
            _git(cfg.root, "checkout-index", "-z", "--stdin", f"--prefix={dest}/",
                 input="\0".join(real).encode())
        for p in set(entries) - set(real):
            stand_in = dest / p
            stand_in.parent.mkdir(parents=True, exist_ok=True)
            stand_in.touch()
        # A link out of the folder would resolve inside the git directory from the copy:
        # point it where it points on disk.
        for p in (p for p, mode in entries.items() if mode == "120000" and (dest / p).is_symlink()):
            target = os.path.normpath(os.path.join(cfg.root, os.path.dirname(p), os.readlink(dest / p)))
            if os.path.commonpath([target, str(cfg.root)]) != str(cfg.root):
                committed = os.readlink(dest / p)
                (dest / p).unlink()
                os.symlink(target, dest / p)
                if redirected is not None:
                    redirected[p] = (target, committed)
        yield dest
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def check_staged(cfg, fix_modes=False):
    """Problems in what is being committed. Modes are checked on the real files: git
    does not keep them, so the copy's say nothing."""
    entries = staged_files(cfg)
    files = sorted(entries)
    if fix_modes:
        for f in private_files(cfg, files):
            if (cfg.root / f).is_file():
                os.chmod(cfg.root / f, 0o600)
    redirected = {}
    with staged_copy(cfg, entries, redirected) as copy:
        staged_profile = copy / flowconfig.PROFILE
        if staged_profile.is_file():
            path, shown = staged_profile, f"{flowconfig.PROFILE} (staged)"
        else:
            path = shown = cfg.profile_path
        try:
            ccfg = flowconfig.Config(copy, tomllib.loads(Path(path).read_text()), shown)
        except tomllib.TOMLDecodeError as e:
            print(f"flow-life: {shown}: {e}", file=sys.stderr)
            sys.exit(2)
        except flowconfig.ProfileError as e:
            print(f"flow-life: {e}", file=sys.stderr)
            sys.exit(2)
        problems = check_all(ccfg, modes=False)
    # A redirected link is reported with the target it was committed with.
    for p, (target, committed) in redirected.items():
        problems = [f"links: symlink {p} -> {committed}: broken"
                    if prob == f"links: symlink {p} -> {target}: broken" else prob
                    for prob in problems]
    return problems + check_modes(cfg, [f for f in files if (cfg.root / f).is_file()])


if __name__ == "__main__":
    cfg = flowconfig.load_or_exit()
    if "--staged" in sys.argv:
        if not is_git(cfg.root):
            print("check_repo.py: --staged needs a git repository", file=sys.stderr)
            sys.exit(2)
        problems = check_staged(cfg, fix_modes="--fix-modes" in sys.argv)
    else:
        if "--fix-modes" in sys.argv:
            for f in private_files(cfg, repo_files(cfg.root)):
                os.chmod(cfg.root / f, 0o600)
        problems = check_all(cfg)
    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s)", file=sys.stderr)
    sys.exit(1 if problems else 0)
