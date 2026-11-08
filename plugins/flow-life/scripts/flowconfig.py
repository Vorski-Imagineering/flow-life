"""Find the folder a flow-life command acts on, and read its profile.

The folder is the nearest one, at or above the start folder, that holds
`.agents/flow-life.toml`. Every setting has a default (DEFAULTS); the profile
only names what differs. An unknown setting is an error, so a typo does not
silently fall back to a default.

The folder does not have to be a git repository, and a git repository does not
need a remote: nothing here talks to a network.
"""
import os
import sys
import tomllib
from pathlib import Path

PROFILE = ".agents/flow-life.toml"
PROFILE_VERSION = 1

DEFAULTS = {
    "profile": PROFILE_VERSION,
    # Areas are the top-level folders holding processes/{active,closed}/.
    # Empty means: every top-level folder that has a processes/ folder.
    "areas": [],
    "documents_dir": "documents",
    "register": "documents/register.md",
    "email_log": "shared/correspondence/email-log.md",
    "identifiers": "personal-details.md",
    "identifier_heading": "## Identifiers checked",
    "path_map": "docs/path-map.md",
    "dashboard": "README.md",
    "deadlines_heading": "Next deadlines",
    "expiring_heading": "Expiring or stale documents",
    "report_title": "Status",
    "immutable_dirs": ["sent-emails", "received-emails", "portal-responses"],
    "email_dirs": ["sent-emails", "received-emails"],
    # Identifiers may also appear in these (besides the identifiers file, the email
    # log, the path map, process folders and evidence in documents_dir).
    "id_allowed_files": [],
    "id_allowed_prefixes": ["tmp/"],
    "id_text_suffixes": [".md", ".html", ".py", ".json", ".txt", ".csv"],
    # Not scanned for path references.
    "link_excluded_files": [],
    "link_excluded_prefixes": [".git/", "tmp/"],
    # Folder names the link check skips at any depth (not append-only).
    "link_excluded_dirs": [],
    "link_text_suffixes": [".md", ".html", ".py"],
    # Regular expressions for old folder names that must not reappear.
    "stale_patterns": [],
}
_SETS = {"immutable_dirs", "email_dirs", "id_allowed_files", "id_text_suffixes",
         "link_excluded_files", "link_excluded_dirs", "link_text_suffixes"}
_TUPLES = {"areas", "id_allowed_prefixes", "link_excluded_prefixes", "stale_patterns"}


class ProfileError(Exception):
    pass


class Config:
    """Settings for one folder. Attribute access: cfg.register, cfg.root, ..."""

    def __init__(self, root, settings=None, profile_path=None):
        self.root = Path(root).resolve()
        self.profile_path = profile_path
        merged = dict(DEFAULTS)
        unknown = set(settings or {}) - set(DEFAULTS)
        if unknown:
            raise ProfileError(f"{profile_path or 'profile'}: unknown setting(s): "
                               + ", ".join(sorted(unknown)))
        merged.update(settings or {})
        if merged["profile"] != PROFILE_VERSION:
            raise ProfileError(f"{profile_path}: profile = {merged['profile']}, "
                               f"this plugin reads profile = {PROFILE_VERSION}")
        # folder names; "sources/" or "/sources" means "sources"
        merged["link_excluded_dirs"] = [d.strip("/") if isinstance(d, str) else d
                                        for d in merged["link_excluded_dirs"]]
        for k, v in merged.items():
            if k in _SETS:
                v = frozenset(v)
            elif k in _TUPLES:
                v = tuple(v)
            setattr(self, k, v)

    @property
    def id_always_allowed(self):
        return {self.identifiers, self.email_log, self.path_map} | set(self.id_allowed_files)


def find_profile(start=None):
    """Nearest `.agents/flow-life.toml` at or above start (default: FLOW_LIFE_ROOT, then
    CLAUDE_PROJECT_DIR, then the current folder). None when there is none."""
    start = start or os.environ.get("FLOW_LIFE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    d = Path(start).resolve()
    for folder in (d, *d.parents):
        if (folder / PROFILE).is_file():
            return folder / PROFILE
    return None


def load(start=None):
    """Config for the folder that owns the nearest profile, or None if none is found."""
    path = find_profile(start)
    if path is None:
        return None
    try:
        settings = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ProfileError(f"{path}: {e}") from e
    return Config(path.parent.parent, settings, path)


def load_or_exit(start=None):
    """For command-line scripts: the config, or a one-line reason and exit 2."""
    try:
        cfg = load(start)
    except ProfileError as e:
        print(f"flow-life: {e}", file=sys.stderr)
        sys.exit(2)
    if cfg is None:
        print(f"flow-life: no {PROFILE} at or above {Path(start or os.getcwd()).resolve()}; "
              "run /flow-life:setup to adopt this folder", file=sys.stderr)
        sys.exit(2)
    return cfg
