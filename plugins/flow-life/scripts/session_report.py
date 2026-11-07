#!/usr/bin/env python3
"""Session-start report: open processes, upcoming deadlines, stale documents, repo check.

    session_report.py          hook JSON (systemMessage + additionalContext)
    session_report.py --text   the report as plain text

Run by the plugin's SessionStart hook. In a folder that has not adopted flow-life
(no profile above it) it prints nothing, so the plugin can be installed for all
projects without touching the others. It also records where this plugin is
installed in .git/flow-life-plugin-root, for the git pre-commit shim.
"""
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_repo  # noqa: E402
import flowconfig  # noqa: E402
import status  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def section(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def deadlines(readme, heading, today=None):
    today = today or date.today()
    out = []
    for line in section(readme, heading).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = re.match(r"(\d{4}-\d{2}-\d{2})", cells[0]) if len(cells) >= 3 else None
        if not m:
            continue
        days = (date.fromisoformat(m.group(1)) - today).days
        when = f"in {days}d" if days >= 0 else f"{-days}d OVERDUE"
        out.append(f"  {cells[0]:24} {when:12} {cells[1]}: {cells[2]}")
    return out


def build(cfg):
    dash = cfg.root / cfg.dashboard
    readme = dash.read_text() if dash.exists() else ""
    rows = [r for r in status.scan(cfg.root, cfg.areas) if r["folder"] == "active"]
    lines = [f"== {cfg.report_title}, {date.today()} ==", "", "Open processes:"]
    for r in rows:
        flag = f"  !! {r['problem']}" if r["problem"] else ""
        lines.append(f"  [{r['status'] or '?':7}] {r['area']}/{r['name']}")
        lines.append(f"            next: {r['next'] or '-'}{flag}")
    if not rows:
        lines.append("  none")
    lines += ["", "Deadlines:"] + (deadlines(readme, cfg.deadlines_heading) or ["  none"])
    lines += ["", "Expiring / stale documents:"]
    expiring = section(readme, cfg.expiring_heading).strip().splitlines()
    lines += [f" {l}" for l in expiring] or ["  none"]
    problems = check_repo.check_all(cfg)
    lines += ["", f"Repo check: {len(problems)} problem(s) (/flow-life:status, or check_repo.py)"]
    lines += [f"  !! {p}" for p in problems[:10]]
    if check_repo.is_git(cfg.root):
        dirty = subprocess.run(["git", "status", "--short"], cwd=cfg.root,
                               capture_output=True, text=True).stdout
        if dirty.strip():
            lines += ["", f"Uncommitted changes: {len(dirty.splitlines())} paths (git status)"]
    return "\n".join(lines)


def record_plugin_root(cfg):
    """Tell the pre-commit shim where this copy of the plugin lives (path changes on update)."""
    git_dir = subprocess.run(["git", "rev-parse", "--absolute-git-dir"], cwd=cfg.root,
                             capture_output=True, text=True).stdout.strip()
    if git_dir:
        try:
            Path(git_dir, "flow-life-plugin-root").write_text(str(PLUGIN_ROOT) + "\n")
        except OSError:
            pass


if __name__ == "__main__":
    try:
        cfg = flowconfig.load()
    except flowconfig.ProfileError as e:
        cfg, report = None, f"flow-life: {e}"
    else:
        report = None
    if cfg is None and report is None:
        sys.exit(0)  # not a flow-life folder
    if cfg is not None:
        if os.environ.get("CLAUDE_PLUGIN_ROOT"):
            record_plugin_root(cfg)
        report = build(cfg)
    if "--text" in sys.argv:
        print(report)
    else:
        print(json.dumps({
            "systemMessage": report,
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": report},
        }))
