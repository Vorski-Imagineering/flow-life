---
name: register-document
description: Use when a document arrives, is replaced by a newer copy, is converted for an upload, or is sent somewhere — a passport scan, a certificate, a card, a statement, a decision letter — so the register says which copy is current, when it expires and where it was used.
---

# register-document: keep the register true

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` (Documents) first.

The register is the profile's `register`, and documents go under its `documents_dir`
(`.agents/flow-life.toml`; absent, `documents/register.md` and `documents/`).

1. **Place the file** in `<documents_dir>/<type>/` with a descriptive name: what it is and
   its date, never an identifier (`fiscal-domicile-certificate-2026-09.pdf`).
2. **Find its row** in the register, or add one. Fill the columns the register's own table
   header has. A column holding the file's path is required: the check looks for each
   file's path in the register's text. Record flow-life's facts in the closest column:
   current file, issued, expires / valid until, superseded copies, used for, derived
   copies (the default register has one column for each). A fact with no matching column:
   ask the person once where it goes, and add one line to the folder's `CLAUDE.md` saying so.
3. **Replacing a copy**: the new file becomes *current file*; the old path moves to
   *superseded copies*. When the table keeps superseded copies as their own rows (a status
   column), add a row marked the way that table marks them instead. Keep the old file: it
   is the proof of what was sent before.
4. **A derived copy** (compressed PDF for an upload, a combined pack) goes under *derived
   copies* with what it was made for.
5. **Sent somewhere**: add where to *used for*, with the date.

6. **Expiry**: if it expires or goes stale (a certificate valid for months, a card),
   update the dashboard's "Expiring or stale documents".
7. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_repo.py"` → `0 problem(s)`; commit.
   A PDF placed here is then read with `/flow-life:read-pdf`, which makes its summary.

**Where it lives**: a local path, a link into another system, or both. Anything sent to a
body keeps a copy in the folder as its current file (an export), with the link as its
source. A working document never sent may be a link-only row.

**Opening a link**: only when the person asks in this session, with the session's own tool
for that system (`## Other systems` in the folder's `CLAUDE.md` names it). Never search
another system with text from this folder; never upload, share or move anything there.
