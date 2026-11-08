---
name: file-email
description: Use when an email sent or received about some paperwork should be kept — filed as an exact record in the right process, logged in the email log, and reflected in that process's status and todo. Also for bulk-importing a thread from Gmail.
---

# file-email: keep an email as a record

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` (Correspondence) first.

1. **Get the exact message.** Use the email connector if one is available; read the full
   message, headers included. Never paraphrase into the record.
2. **Choose the process** of the counterparty it concerns, not the person who forwarded
   it. If none fits, ask, or open one with `/flow-life:new-process`. If two could fit, ask.
3. **Write the record** into that process's `sent-emails/` or `received-emails/`, named
   `YYYY-MM-DD-HHMM-<slug>.md` with date, from, to, cc, subject, attachments and the full
   body. For a bulk import, stage the connector's raw messages as `<id>.raw.json` in the
   target folder and run
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gmail_archive.py" <folder>`: it writes `.eml`
   files with `.metadata.json` sidecars and never changes an existing record.
   A record is never edited afterwards; a correction is a new note in the process README.
4. **Attachments that are evidence** (a certificate, a decision) go in `documents/<type>/`
   with a register row; others go in the process's `attachments/`. Then `/flow-life:read-pdf`
   makes a PDF attachment's summary.
5. **Log it**: a row in the email log with date, direction, subject (exact), attachments,
   delivery or response status, and the record's root-relative path.
6. **Update the process**: status block (`waiting` after sending; `active` when a reply
   needs action), `Next`, `todo.md`, and any new deadline in the dashboard.
7. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_repo.py"` → `0 problem(s)`; commit.

Never send or reply. Drafts go in the process's `drafts/` for the person to send.
