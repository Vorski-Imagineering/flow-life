#!/usr/bin/env python3
"""Create flow-life files from the plugin's templates. Never overwrites a file.

    scaffold.py init [--title T] [--areas a,b,c] [--git] [--hooks] [--dir DIR]
    scaffold.py area <name> [--dir DIR]
    scaffold.py process <area> <yyyy-slug> [--next TEXT] [--opened YYYY-MM-DD] [--dir DIR]

`init` lays out a folder (profile, dashboard, CLAUDE.md, personal-details.md, register,
email log, path map, shared reference, one folder per area). When the folder already has
a profile, each file goes where it says. `--git` runs `git init` first if the folder is
not a repository (no remote is added). `--hooks` copies the pre-commit shim to .githooks/
and sets core.hooksPath. Prints one line per file created and one per file left as it was.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import flowconfig  # noqa: E402

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PROCESS = re.compile(r"^\d{4}-[a-z0-9][a-z0-9-]*$")


def _title(slug):
    return slug.replace("-", " ").capitalize()


def write(root, rel, template, values, out):
    dest = Path(root) / rel
    if dest.exists():
        out.append(f"kept     {rel}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = (TEMPLATES / template).read_text()
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    dest.write_text(text)
    out.append(f"created  {rel}")


def area(root, name, out):
    if not SLUG.match(name):
        raise SystemExit(f"area name must be lower-case letters, digits and hyphens: {name!r}")
    v = {"area_title": _title(name)}
    write(root, f"{name}/README.md", "area/README.md", v, out)
    write(root, f"{name}/reference.md", "area/reference.md", v, out)
    for folder in ("active", "closed"):
        keep = Path(root) / name / "processes" / folder / ".gitkeep"
        if not keep.parent.exists():
            keep.parent.mkdir(parents=True)
            keep.touch()
            out.append(f"created  {name}/processes/{folder}/")


def process(root, area_name, name, next_step, opened, out):
    if not (Path(root) / area_name / "processes").is_dir():
        raise SystemExit(f"no area {area_name!r} (create it with: scaffold.py area {area_name})")
    if not PROCESS.match(name):
        raise SystemExit(f"process folder must be <yyyy>-<slug>, lower case: {name!r}")
    base = f"{area_name}/processes/active/{name}"
    if (Path(root) / area_name / "processes/closed" / name).exists():
        raise SystemExit(f"{area_name}/processes/closed/{name} already exists")
    v = {"opened": opened, "next": next_step, "process_title": _title(name[5:])}
    write(root, f"{base}/README.md", "process/README.md", v, out)
    write(root, f"{base}/todo.md", "process/todo.md", v, out)


PATH_SETTINGS = ("register", "email_log", "path_map", "identifiers", "dashboard")


def folder_config(root):
    """Settings for the folder being laid out: its own profile only, never a parent's.
    Stops, having written nothing, on a profile that does not load or that names a path
    outside the folder."""
    prof = Path(root) / flowconfig.PROFILE
    try:
        settings = tomllib.loads(prof.read_text()) if prof.is_file() else {}
        cfg = flowconfig.Config(root, settings, prof if prof.is_file() else None)
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"flow-life: {prof}: {e}")
    except flowconfig.ProfileError as e:
        raise SystemExit(f"flow-life: {e}")
    for name in (*PATH_SETTINGS, "documents_dir"):
        value = getattr(cfg, name)
        if not isinstance(value, str) or os.path.normpath(value) == ".":
            raise SystemExit(f"flow-life: {name} = {value!r} is not a file path")
        if os.path.isabs(value) or os.path.normpath(value).split(os.sep)[0] == "..":
            raise SystemExit(f"flow-life: {name} = {value} is outside this folder")
    return cfg


def init(root, title, areas, use_git, hooks, out):
    root = Path(root)
    cfg = folder_config(root)
    if use_git and subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root,
                                  capture_output=True).returncode != 0:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        out.append("created  .git/ (git init, no remote)")
    v = {"title": title, "today": date.today().isoformat(), "documents_dir": cfg.documents_dir,
         **{name: getattr(cfg, name) for name in PATH_SETTINGS}}
    write(root, flowconfig.PROFILE, "flow-life.toml", v, out)
    if areas:
        prof = root / flowconfig.PROFILE
        text = prof.read_text()
        if "areas = []" in text:
            prof.write_text(text.replace("areas = []", "areas = [" + ", ".join(f'"{a}"' for a in areas) + "]"))
    for rel, tpl in [(cfg.dashboard, "README.md"), ("CLAUDE.md", "CLAUDE.md"),
                     (cfg.identifiers, "personal-details.md"),
                     (cfg.register, "documents/register.md"),
                     (cfg.email_log, "shared/correspondence/email-log.md"),
                     ("shared/reference.md", "shared/reference.md"),
                     (cfg.path_map, "docs/path-map.md"), (".gitignore", "gitignore")]:
        write(root, rel, tpl, v, out)
    os.chmod(root / cfg.identifiers, 0o600)
    for a in areas:
        area(root, a, out)
    if hooks:
        install_hooks(root, out)


def install_hooks(root, out):
    dest = Path(root) / ".githooks/pre-commit"
    if dest.exists():
        out.append("kept     .githooks/pre-commit")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(TEMPLATES / "githooks/pre-commit", dest)
        dest.chmod(0o755)
        out.append("created  .githooks/pre-commit")
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=root, check=True)
    out.append("set      git config core.hooksPath .githooks")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--title", default="Paperwork")
    i.add_argument("--areas", default="")
    i.add_argument("--git", action="store_true")
    i.add_argument("--hooks", action="store_true")
    i.add_argument("--dir", default=argparse.SUPPRESS)
    a = sub.add_parser("area")
    a.add_argument("name")
    a.add_argument("--dir", default=argparse.SUPPRESS)
    p = sub.add_parser("process")
    p.add_argument("area")
    p.add_argument("name")
    p.add_argument("--next", default="…")
    p.add_argument("--opened", default=date.today().isoformat())
    p.add_argument("--dir", default=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    out = []
    if args.cmd == "init":
        root = Path(args.dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        init(root, args.title, [x for x in args.areas.split(",") if x], args.git, args.hooks, out)
    else:
        cfg = flowconfig.load_or_exit(args.dir)
        if args.cmd == "area":
            area(cfg.root, args.name, out)
        else:
            process(cfg.root, args.area, args.name, args.next, args.opened, out)
    print("\n".join(out))


if __name__ == "__main__":
    main()
