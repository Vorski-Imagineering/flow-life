---
name: wrap-up
description: Use when the user is about to close a session on a flow-life folder, or asks whether it is safe to close, whether anything is outstanding, or what the session learned. Finds what would be left hanging, sorts what was learned into the right place, and gives one verdict. Reads only.
---

# wrap-up: is it safe to close this session?

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` (Sensitive data, Sending, paying, signing)
first. Only inside a flow-life folder (a `.agents/flow-life.toml` at or above it); anywhere
else say so and stop.

Closing a session with work hanging costs more than one extra exchange, so the default
verdict is **Not yet**. Do the checks; never answer from memory of the conversation.

## 1. Find what is hanging

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wrap_up.py"
```

It reads only and fetches nothing. Show **every** row, clean ones too: a silent check cannot
be told from a skipped one. `OPEN` is something left; `INFO` is named and never blocks.
"Unpushed" is relative to the last fetch. Exit 2 means this is not a flow-life folder.

**Separate this session's work from what was already there.** The opening status report
gave a count of uncommitted paths; no such line means the folder was clean. Anything
beyond that, and any file the conversation touched, is this session's. Earlier changes are named in one line and left alone.

## 2. Checks the script cannot make

Go through the conversation for each:

- a document added or replaced this session with no register row;
- a PDF read this session with no current summary (`pdf-summaries` row);
- an email drafted this session and not yet sent by the owner (you never send), or one
  they sent that is not yet filed and logged;
- a process whose outcome was reached this session but is still `active`;
- a next action, deadline or contact changed in the conversation but not in the process
  README or the dashboard;
- a promise in your own replies ("I'll", "next", "later") neither done nor written down.

## 3. What was learned: each thing to exactly one place

| It is | Goes to |
|---|---|
| A fact about the owner's case, or a correction to the folder's notes | **Propose** the exact text and where it goes (the folder's `CLAUDE.md`, an area README, or the `reference` skill). Write it only after a yes. |
| An identifier (a number, a date of birth) | Only the identifiers file. Never chat, memory or this report. |
| How the owner wants Claude to work | Claude's own memory: save it without asking, and name it in the report. |
| Only mattered to this session | Nowhere. Say so. |

## 4. The verdict

The first line is bold.

- **`**Not yet.**`** then a numbered list: what is open, what is lost if the session closes
  now, and the one action that closes it. Use it when an `OPEN` row is this session's, a
  check in §2 is open, a learning is neither saved nor proposed, or a check was not run.
- **`**Safe to close.**`** only when nothing blocks, then one line per check proving it.

Earlier uncommitted work and `INFO` rows are named in one line and do not block.

## Never

Never commit, push, stash, discard, move, send, pay, sign or delete as part of wrapping up.
Offer, and when the owner says to do it, run the script again; do not carry old results
forward.

**Closing anyway:** say once, in plain words, exactly what will be lost or left, and ask
for a yes to that list. Their explicit yes is the override; stop arguing after it.

The report names paths and counts only: no identifier value, no document contents. Keep it
short: a line per check, the learnings and where each went, the verdict.
