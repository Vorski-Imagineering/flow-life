---
name: status
description: Use when asked where the paperwork stands — open processes and who owes the next move, upcoming and overdue deadlines, expiring or stale documents, and whether the folder passes its check. Reads only.
---

# status: where everything stands

It reads only: no file, register or log is changed.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_report.py" --text
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py"
```

The first is the same report the session opens with: open processes with their `Next`
line, deadlines with days left or overdue, expiring documents, the repo check, uncommitted
changes. The second lists every process, closed ones included; a `!!` marks an invalid
status block.

Report in this order, briefly:

1. **Overdue** deadlines and anything with a `!!`, first.
2. **Waiting on me**: `active` processes, with their next action.
3. **Waiting on them**: `waiting` processes, and how long since the last move where the
   process README or todo says.
4. **Coming up**: deadlines in the next 60 days; documents expiring.
5. **Repo check**: the count; if not 0, each problem with what fixes it
   (`${CLAUDE_PLUGIN_ROOT}/references/rules.md` says why each rule exists).

If a deadline is overdue but the process shows it was dealt with, say so and offer to
update the dashboard rather than reporting it as a problem.
