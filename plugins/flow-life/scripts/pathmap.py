"""Path-map driven link maintenance.

The path map (profile `path_map`, default docs/path-map.md) records every move
(old -> new). rewrite() updates path references in mutable text files and
relative symlinks; check() reports anything that does not resolve.
"""
import os
import re
from collections import namedtuple
from pathlib import Path

Token = namedtuple("Token", "start end path suffix")

_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|")
_BACKTICK = re.compile(r"`([^`\n]+)`")
_MDLINK = re.compile(r"\]\(([^)\s]+)\)")
_HTML = [re.compile(r"<code>([^<]+)</code>"), re.compile(r'href="([^"]+)"'),
         re.compile(r'src="([^"]+)"')]
_PYSTR = re.compile(r'"([^"\n]+)"')
_SUFFIX = re.compile(r"(#[^/]*|:\d+)$")
_EXT = re.compile(r"\.[A-Za-z0-9]{1,5}$")
_BAD = set("*<>[]{}|")


def load_path_map(md_text):
    rows = []
    for line in md_text.splitlines():
        m = _ROW.match(line.strip())
        if m:
            rows.append((m.group(1), m.group(2)))
    return rows


def _apply(p, pairs):
    best = None
    for old, new in pairs:
        if old.endswith("/"):
            hit = p.startswith(old) or p + "/" == old
        else:
            hit = p == old
        if hit and (best is None or len(old) > len(best[0])):
            best = (old, new)
    if best is None:
        return None
    old, new = best
    if p + "/" == old:
        return new.rstrip("/")
    return new + p[len(old):] if old.endswith("/") else new


def map_forward(p, rows):
    for _ in range(20):
        nxt = _apply(p, rows)
        if nxt is None or nxt == p:
            return p
        p = nxt
    return p


def map_reverse(p, rows):
    pairs = [(new, old) for old, new in reversed(rows)]
    for _ in range(20):
        nxt = _apply(p, pairs)
        if nxt is None or nxt == p:
            return p
        p = nxt
    return p


def is_excluded(rel, cfg):
    if (rel in (cfg.path_map, ".git") or rel in cfg.link_excluded_files
            or rel.startswith(cfg.link_excluded_prefixes)):
        return True
    parts = rel.split("/")
    if any(d in {n.rstrip("/") for n in cfg.link_excluded_dirs} for d in parts[:-1]):
        return True
    return parts[-1] != "README.md" and any(d in cfg.immutable_dirs for d in parts[:-1])


def _rel(path, root):
    return path.relative_to(root).as_posix()


def iter_text_files(cfg):
    root = cfg.root
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        dirnames[:] = [n for n in dirnames
                       if not is_excluded(_rel(d / n, root) + "/", cfg) and not (d / n).is_symlink()]
        for n in filenames:
            p = d / n
            if (p.suffix in cfg.link_text_suffixes and not p.is_symlink()
                    and not is_excluded(_rel(p, root), cfg)):
                yield p


def iter_symlinks(root):
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        dirnames[:] = [n for n in dirnames if _rel(d / n, root) not in (".git", "tmp")]
        for n in filenames + dirnames:
            p = d / n
            if p.is_symlink():
                yield p


def _looks_like_path(s):
    return ("/" in s and not any(c.isspace() for c in s) and "://" not in s
            and not s.startswith(("mailto:", "/", "~")) and not (set(s) & _BAD))


def extract_tokens(text, suffix):
    found = []
    regexes = [_BACKTICK, _MDLINK]
    if suffix == ".html":
        regexes = _HTML
    elif suffix == ".py":
        regexes = [_PYSTR]
    for rx in regexes:
        for m in rx.finditer(text):
            raw = m.group(1)
            if not _looks_like_path(raw):
                continue
            sm = _SUFFIX.search(raw)
            sfx = sm.group(1) if sm else ""
            path = raw[: len(raw) - len(sfx)]
            if "/" not in path or path.startswith("...") or set(path) <= set("./"):
                continue
            if not (path.endswith("/") or _EXT.search(path.rsplit("/", 1)[-1])):
                continue
            found.append(Token(m.start(1), m.start(1) + len(raw), path, sfx))
    found.sort(key=lambda t: t.start)
    return found


def top_level_names(root, rows):
    names = {p.name for p in Path(root).iterdir()}
    names |= {old.split("/")[0] for old, _ in rows}
    names |= {new.split("/")[0] for _, new in rows}
    return names - {"tmp"}


def resolve(token_path, file_rel, top_level):
    """Root-relative path a reference points at; None for tmp/, .git/ or outside the root.

    A path whose first segment is a top-level name is root-relative; anything else is
    relative to the file that holds it."""
    trailing = token_path.endswith("/")
    first = token_path.split("/")[0]
    if token_path.startswith(("./", "../")) or first not in top_level:
        joined = os.path.join(os.path.dirname(file_rel), token_path)
    else:
        joined = token_path
    norm = os.path.normpath(joined).replace(os.sep, "/")
    if norm.startswith("..") or norm.split("/")[0] in ("tmp", ".git"):
        return None
    return norm + "/" if trailing and not norm.endswith("/") else norm


def rows_for(cfg):
    p = cfg.root / cfg.path_map
    return load_path_map(p.read_text()) if p.exists() else []


def _exists(root, rel):
    return os.path.lexists(Path(root) / rel.rstrip("/")) if rel else False


def rewrite(cfg, dry_run=False):
    root = cfg.root
    rows = rows_for(cfg)
    top = top_level_names(root, rows)
    changes = []
    for f in iter_text_files(cfg):
        new_rel = _rel(f, root)
        old_rel = map_reverse(new_rel, rows)
        text = f.read_text()
        out, last = [], 0
        for t in extract_tokens(text, f.suffix):
            if f.suffix == ".py" and t.path.split("/")[0] not in top:
                continue
            target_old = resolve(t.path, old_rel, top)
            if target_old is None:
                continue
            target_new = map_forward(target_old, rows)
            relative = t.path.startswith(("./", "../")) or t.path.split("/")[0] not in top
            if target_new == target_old and not (relative and old_rel != new_rel):
                continue
            if not _exists(root, target_new):
                continue
            if target_new != t.path:
                out.append(text[last:t.start] + target_new + t.suffix)
                last = t.end
                changes.append(f"{new_rel}: {t.path}{t.suffix} -> {target_new}{t.suffix}")
        if out and not dry_run:
            f.write_text("".join(out) + text[last:])
    for link in iter_symlinks(root):
        target = os.readlink(link)
        if os.path.isabs(target):
            continue
        new_rel = _rel(link, root)
        old_rel = map_reverse(new_rel, rows)
        # The link may still be relative to its old location, or to its current one
        # (already rewritten by an earlier move): take whichever candidate resolves.
        target_new = None
        for base in (old_rel, new_rel):
            cand = os.path.normpath(os.path.join(os.path.dirname(base), target))
            mapped = map_forward(cand, rows)
            if _exists(root, mapped):
                target_new = mapped
                break
        if target_new is None:
            continue
        new_link = os.path.relpath(target_new, os.path.dirname(new_rel) or ".")
        if new_link != target:
            changes.append(f"{new_rel}: symlink {target} -> {new_link}")
            if not dry_run:
                os.remove(link)
                os.symlink(new_link, link)
    return changes


def check(cfg):
    root = cfg.root
    rows = rows_for(cfg)
    top = top_level_names(root, rows)
    problems = []
    for f in iter_text_files(cfg):
        rel = _rel(f, root)
        text = f.read_text()
        for t in extract_tokens(text, f.suffix):
            if f.suffix == ".py" and t.path.split("/")[0] not in top:
                continue
            target = resolve(t.path, rel, top)
            if target is not None and not _exists(root, target):
                line = text.count("\n", 0, t.start) + 1
                problems.append(f"{rel}:{line}: unresolved {t.path}{t.suffix}")
    if cfg.stale_patterns:
        stale = re.compile("|".join(f"(?:{p})" for p in cfg.stale_patterns))
        for f in iter_text_files(cfg):
            rel = _rel(f, root)
            if rel == cfg.identifiers:
                continue
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if stale.search(line):
                    problems.append(f"{rel}:{n}: stale old-layout path")
    for link in iter_symlinks(root):
        if not link.exists():
            problems.append(f"symlink {_rel(link, root)} -> {os.readlink(link)}: broken")
    for _, new in rows:
        final = map_forward(new, rows)
        if not _exists(root, final):
            problems.append(f"path-map: {final} does not exist")
    return problems
