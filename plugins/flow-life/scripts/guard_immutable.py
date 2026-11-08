#!/usr/bin/env python3
"""Claude Code PreToolUse hook: refuse edits to existing immutable records.

Creating a new file in an immutable folder (profile `immutable_dirs`) is allowed.
Files outside a flow-life folder are never touched by this hook.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import flowconfig  # noqa: E402


def decide(file_path):
    """Reason to deny, or None to allow."""
    path = Path(file_path)
    if not file_path or not path.exists():
        return None
    try:
        cfg = flowconfig.load(path.parent)
    except Exception:  # broken profile: still protect the defaults, rooted at its folder
        profile = flowconfig.find_profile(path.parent)
        if profile is None:
            return None
        cfg = flowconfig.Config(profile.parent.parent)
    if cfg is None:
        return None
    try:
        rel = path.resolve().relative_to(cfg.root)
    except ValueError:
        return None
    if cfg.immutable_dirs & set(rel.parts[:-1]):
        return (f"{path.name} is an immutable record (flow-life rules: records are never "
                "edited). Write a new file instead.")
    return None


if __name__ == "__main__":
    data = json.load(sys.stdin)
    reason = decide((data.get("tool_input") or {}).get("file_path") or "")
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}))
