#!/usr/bin/env python3
"""What a session would leave hanging in a flow-life folder. Reads only.

    wrap_up.py       one row per check: PASS, OPEN or INFO; exit 1 if any row is OPEN

Nothing is changed and nothing is fetched: "unpushed" is relative to the last fetch.
Rows name paths and counts, never identifier values or file contents.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_repo  # noqa: E402
import flowconfig  # noqa: E402
import pdf_summary  # noqa: E402
import session_report  # noqa: E402
import status  # noqa: E402

CAP = 10
PDF_STATE = {1: "none", 3: "stale", 4: "foreign"}


def git(root, *args):
    return subprocess.run(["git", "--no-optional-locks", *args], cwd=root,
                          capture_output=True, text=True)


def row(tag, name, text, items=()):
    out = [f"{tag} {name}: {text}"]
    out += [f"    {i}" for i in list(items)[:CAP]]
    if len(items) > CAP:
        out.append(f"    ... and {len(items) - CAP} more")
    return out


def count_row(name, items, noun, open_tag="OPEN"):
    if not items:
        return row("PASS", name, f"0 {noun}")
    return row(open_tag, name, f"{len(items)} {noun}", items)


def git_rows(cfg):
    root = cfg.root
    if not check_repo.is_git(root):
        return [r for n in ("uncommitted", "unpushed", "stash")
                for r in row("INFO", n, "not a git folder")]
    rows = count_row("uncommitted", git(root, "status", "--porcelain").stdout.splitlines(), "path(s)")
    if git(root, "rev-parse", "--abbrev-ref", "@{u}").returncode != 0:
        rows += row("INFO", "unpushed", "no upstream, nothing to compare")
    else:
        n = int(git(root, "rev-list", "--count", "@{u}..HEAD").stdout.strip() or 0)
        rows += (row("OPEN", "unpushed", f"{n} commit(s) ahead of the last fetch") if n
                 else row("PASS", "unpushed", "0 commit(s) ahead of the last fetch"))
    return rows + count_row("stash", git(root, "stash", "list").stdout.splitlines(), "stash(es)")


def pdf_rows(cfg):
    skip = set(cfg.immutable_dirs) | set(cfg.email_dirs)
    pdfs = [f for f in check_repo.repo_files(cfg.root)
            if f.lower().endswith(".pdf") and not check_repo.in_dirs(f, skip)]
    lacking = []
    for f in pdfs:
        code, _ = pdf_summary.status(cfg.root / f)
        if code:
            lacking.append(f"{f} ({PDF_STATE.get(code, 'unknown')})")
    if not lacking:
        return row("PASS", "pdf-summaries", f"all {len(pdfs)} PDF(s) have a current summary")
    return row("INFO", "pdf-summaries",
               f"{len(lacking)} of {len(pdfs)} PDF(s) have no current summary", lacking)


def deadline_rows(cfg):
    dash = cfg.root / cfg.dashboard
    lines = session_report.deadlines(dash.read_text(), cfg.deadlines_heading) if dash.exists() else []
    near = [l.strip() for l in lines
            if "OVERDUE" in l or ((m := re.search(r"\bin (\d+)d\b", l)) and int(m.group(1)) <= 7)]
    if not near:
        return row("PASS", "deadlines", "none overdue or within 7 days")
    return row("INFO", "deadlines", f"{len(near)} overdue or within 7 days", near)


def build(cfg):
    problems = check_repo.check_all(cfg)
    bad = [f"{r['area']}/{r['name']}: {r['problem']}"
           for r in status.scan(cfg.root, cfg.areas) if r["problem"]]
    rows = (count_row("repo-check", problems, "problem(s)")
            + count_row("processes", bad, "invalid status block(s)")
            + git_rows(cfg) + pdf_rows(cfg) + deadline_rows(cfg))
    n = sum(1 for r in rows if r.startswith("OPEN "))
    return rows + [f"wrap-up: {n} open"], n


if __name__ == "__main__":
    lines, opened = build(flowconfig.load_or_exit())
    print("\n".join(lines))
    sys.exit(1 if opened else 0)
