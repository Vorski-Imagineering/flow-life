---
name: register-document
description: Use when a document arrives, is replaced by a newer copy, is converted for an upload, or is sent somewhere — a passport scan, a certificate, a card, a statement, a decision letter — so the register says which copy is current, when it expires and where it was used.
---

# register-document: keep the register true

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` (Documents) first.

1. **Place the file** in `documents/<type>/` with a descriptive name: what it is and its
   date, never an identifier (`fiscal-domicile-certificate-2026-09.pdf`).
2. **Find its row** in `documents/register.md`, or add one: document, issuer, current file,
   issued, expires / valid until, superseded copies, used for, derived copies.
3. **Replacing a copy**: the new file becomes *current file*; the old path moves to
   *superseded copies*. Keep the old file: it is the proof of what was sent before.
4. **A derived copy** (compressed PDF for an upload, a combined pack) goes under *derived
   copies* with what it was made for.
5. **Sent somewhere**: add where to *used for*, with the date.
6. **Expiry**: if it expires or goes stale (a certificate valid for months, a card),
   update the dashboard's "Expiring or stale documents".
7. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_repo.py"` → `0 problem(s)`; commit.
