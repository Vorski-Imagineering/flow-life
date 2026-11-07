---
name: close-process
description: Use when a process has reached its outcome (granted, refused, withdrawn, corrected, abandoned) and should be closed and moved to processes/closed/, with its area and the dashboard updated.
---

# close-process: close a finished process

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` (Process status, Moving files) first.

1. **Confirm the outcome with the person** unless the record already proves it (a
   decision letter in `received-emails/`, a card in the register). Closing is their call.
2. **Fill in the block**: `Status: closed`, `Closed: YYYY-MM-DD`, `Outcome:` one line
   (what was decided, and where the proof is), `Next: —`, or what recurs and when (a
   renewal goes in the area README's recurring obligations and, if dated, the dashboard).
3. **Move the folder**, in a git folder with `git mv`:
   `<area>/processes/active/<name>/` → `<area>/processes/closed/<name>/`.
4. Add the row `` | `<area>/processes/active/<name>/` | `<area>/processes/closed/<name>/` | ``
   to the path map, then:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_paths.py"
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_links.py"
   ```
5. **Update** the area README (process list, status) and the dashboard (area row; remove
   deadlines that no longer apply).
6. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py"` shows no `!!`, and
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_repo.py"` prints `0 problem(s)`. Commit.
