---
name: move
description: Use when files or folders in a flow-life folder should be moved or renamed — reorganising, closing a process, adopting an existing folder — so that every path reference and symlink still resolves and the history is kept.
---

# move: move files without breaking references

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` (Moving files) first.

1. **Plan** the moves as a table (old → new) and show it. Never move a single file out of
   an append-only folder (`sent-emails/`, `received-emails/`, `portal-responses/`); a whole
   process folder may move.
2. **Move** with `git mv` in a git folder (keeps history), otherwise a plain move. A PDF's
   summary (`<name>.md` beside it, from `/flow-life:read-pdf`) moves with it, with its register
   row and path-map row.
3. **Record** each move in the path map: `` | `old` | `new` | ``. End a folder's paths
   with `/`.
4. **Rewrite and check:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_paths.py" --dry-run
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_paths.py"
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_links.py"
   ```
   Records are never rewritten: a reference inside a sent email keeps its old text, and
   the path map is what resolves it.
5. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_repo.py"` → `0 problem(s)`; commit the
   moves, path map and rewrites together.
