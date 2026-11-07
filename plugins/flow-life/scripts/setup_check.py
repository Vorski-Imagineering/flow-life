#!/usr/bin/env python3
"""Check that a folder is set up for flow-life. Reads only.

    setup_check.py [--dir DIR]

Prints one line per check: PASS, FAIL (with the fix after ->), WARN or INFO.
Exit 0 when nothing failed.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_repo  # noqa: E402
import flowconfig  # noqa: E402

PLUGIN_KEY = "flow-life@flow-life"


def git(root, *args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def checks(start):
    out = []
    try:
        cfg = flowconfig.load(start)
    except flowconfig.ProfileError as e:
        return [("FAIL", f"profile: {e}", "fix the setting it names")]
    if cfg is None:
        return [("FAIL", f"profile: no {flowconfig.PROFILE} at or above {Path(start).resolve()}",
                 "scaffold.py init (the setup skill offers it)")]
    out.append(("PASS", f"profile: {cfg.profile_path}", None))
    root = cfg.root

    for rel, label in [(cfg.register, "register"), (cfg.email_log, "email log"),
                       (cfg.path_map, "path map"), (cfg.dashboard, "dashboard"),
                       (cfg.identifiers, "identifiers file")]:
        ok = (root / rel).is_file()
        out.append(("PASS" if ok else "FAIL", f"{label}: {rel}",
                    None if ok else "scaffold.py init creates it without touching other files"))
    details = root / cfg.identifiers
    if details.is_file():
        ids = check_repo.load_identifiers(details.read_text(), cfg.identifier_heading)
        if ids is None:
            out.append(("FAIL", f"identifiers table: no `{cfg.identifier_heading}` heading in "
                        f"{cfg.identifiers}", "add the heading and table, or set identifier_heading"))
        elif not ids:
            out.append(("WARN", "identifiers table: empty, so nothing is checked for leaks", None))
        else:
            out.append(("PASS", f"identifiers table: {len(ids)} value(s) checked", None))
        if os.stat(details).st_mode & 0o077:
            out.append(("FAIL", f"mode: {cfg.identifiers} is readable by others",
                        "check_repo.py --fix-modes"))

    areas = sorted({p.parts[-2] for p in root.glob("*/processes")})
    if cfg.areas:
        missing = [a for a in cfg.areas if a not in areas]
        out.append(("FAIL" if missing else "PASS", f"areas: {', '.join(cfg.areas)}"
                    + (f" (missing: {', '.join(missing)})" if missing else ""),
                    "scaffold.py area <name>" if missing else None))
    else:
        out.append(("INFO", f"areas: found {', '.join(areas) or 'none'}", None))

    if git(root, "rev-parse", "--is-inside-work-tree") != "true":
        out.append(("WARN", "git: not a repository; no history and no commit check",
                    "scaffold.py init --git (local only, no remote)"))
    else:
        remotes = git(root, "remote", "-v") or ""
        out.append(("INFO", "git: " + ("remote " + remotes.split()[1] if remotes
                                       else "no remote; nothing leaves this machine"), None))
        hooks_path = git(root, "config", "core.hooksPath")
        shim = root / ".githooks/pre-commit"
        if hooks_path == ".githooks" and shim.is_file():
            out.append(("PASS", "pre-commit: .githooks/pre-commit runs the repo check", None))
        else:
            out.append(("FAIL", f"pre-commit: core.hooksPath is {hooks_path or 'unset'}",
                        "scaffold.py init --hooks (copies the shim, sets core.hooksPath)"))

    settings = root / ".claude/settings.json"
    enabled = False
    if settings.is_file():
        try:
            enabled = json.loads(settings.read_text()).get("enabledPlugins", {}).get(PLUGIN_KEY)
        except json.JSONDecodeError:
            pass
    out.append(("PASS" if enabled else "WARN", f"plugin: {PLUGIN_KEY} "
                + ("enabled in .claude/settings.json" if enabled else "not enabled at project scope"),
                None if enabled else "claude plugin install flow-life@flow-life --scope project"))

    problems = check_repo.check_all(cfg)
    out.append(("PASS" if not problems else "FAIL", f"repo check: {len(problems)} problem(s)",
                "check_repo.py lists them" if problems else None))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    args = ap.parse_args(argv)
    start = args.dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    results = checks(start)
    for level, text, fix in results:
        print(f"{level:4}  {text}" + (f"  -> {fix}" if fix else ""))
    return 1 if any(level == "FAIL" for level, _, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())
