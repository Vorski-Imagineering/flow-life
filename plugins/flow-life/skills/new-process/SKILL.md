---
name: new-process
description: Use when a new piece of paperwork starts — an application, a renewal, a complaint, a correction, a letter that needs an answer — and it should get its own process folder with a status block, a todo and a place for its correspondence.
---

# new-process: open a process

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` (Layout, Process status) first.

1. **Area.** Pick the area it belongs to from the folder (`<area>/processes/`). If none
   fits, propose a new one and, on approval:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" area <name>`.
2. **Check it is new.** Look through that area's `processes/active/` and `closed/`: a
   renewal or a follow-up to an open process belongs in that process, not a new one.
3. **Name** it `<yyyy>-<slug>`: the year it opened, a short lower-case slug that names
   the matter, never an identifier (`2026-residence-renewal`, not a case number).
4. **Create it:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" process <area> <yyyy-slug> --next "<next action>" [--opened YYYY-MM-DD]
   ```
5. **Fill it in.** README: what this is, key dates, which documents it uses (by register
   path). `todo.md`: the steps known so far. Set `Status: waiting` if someone else owes the
   next move. Identifiers the process must quote go in its files and, if new, as a row in
   `personal-details.md`'s identifiers table.
6. **Update the indexes**: a row in the area README's process list and status; a dashboard
   row if it changes the area's status; any deadline in the dashboard's "Next deadlines".
7. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_repo.py"`; commit when it prints
   `0 problem(s)`, in a git folder.
