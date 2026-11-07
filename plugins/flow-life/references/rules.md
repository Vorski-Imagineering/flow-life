# flow-life rules

How a flow-life folder is kept. Every `/flow-life:` skill follows these; the folder's own
`CLAUDE.md` adds only what is particular to its owner. Paths below are the defaults; the
profile (`.agents/flow-life.toml`, see `profile-schema.md`) can rename any of them.

## The idea

Paperwork with public bodies, banks, landlords and suppliers is long-running, repetitive
and unforgiving. The same documents are asked for again and again and go stale; letters must
be quoted exactly months later; a deadline missed costs real money. The same holds for any
exchange that goes back and forth, with thinking and research between the steps: competing
quotes, choosing a contractor, a warranty repair, a refund to chase. A flow-life folder keeps
it in order so that a person, or an agent, can pick up any thread cold:

- **Areas** are long-lived subjects (residence, driving licence, tax, health, home). An area
  never closes: renewals and annual returns bring it back.
- **Processes** are bounded episodes inside an area, with correspondence and an outcome
  (an application, a complaint, a correction, a round of quotes). A process closes; its area
  does not. A process may have several counterparties: a round of quotes keeps each
  supplier's correspondence in the one process, and its README compares the offers.
- **Documents** are evidence shared by every area. One register says which copy is current.
- **Correspondence** is a record. It is never edited.
- **Identifiers** (passport, tax and case numbers) live in one owner-only file and in the
  places that must quote them, nowhere else.

## Layout

```
README.md                         dashboard: areas, next deadlines, expiring documents
CLAUDE.md                         who this is for; background; areas
personal-details.md               identifiers, mode 600
.agents/flow-life.toml            profile
documents/<type>/                 evidence; the register lists every file
<area>/README.md                  status, recurring obligations, process list
<area>/reference.md               sources: official first, dated, no identifiers
<area>/processes/active/<yyyy>-<slug>/
<area>/processes/closed/<yyyy>-<slug>/
shared/correspondence/email-log.md   every kept email, with its path
shared/reference.md               sources that serve more than one area
docs/path-map.md                  every move, old -> new
```

These are the defaults. The profile (`.agents/flow-life.toml`) can move the documents
folder, the register, the email log, the path map, the identifiers file and the dashboard;
wherever these rules name one of them, read the profile's path for it.

A process folder holds `README.md` (status block first), `todo.md`, and as needed
`drafts/`, `sent-emails/`, `received-emails/`, `submissions/` (with `portal-responses/`),
`visits/<date>-<slug>/`, `calls/`, `attachments/`.

Write paths root-relative (`documents/tax/certificate.pdf`) so they resolve from any file.
A path whose first segment is not a top-level name is read as relative to the file that
holds it.

## Process status

Every process `README.md` starts with:

```
- Status: active | waiting | closed
- Opened: YYYY-MM-DD
- Closed: —
- Outcome: —
- Next: one line: the next action and who owes it
```

`active`: the owner (or agent) owes the next move. `waiting`: someone else does.
When a process changes state, update its README, its area README and the dashboard.

To close one: fill in the block (`Closed`, `Outcome`), move the folder from
`processes/active/` to `processes/closed/` (see Moving files), update both READMEs.

## Documents

- Evidence goes in `documents/<type>/` (identity, residence, tax, ...), never inside an area
  or process: every body asks for the same papers.
- Every new, replaced or sent document updates the register: current file,
  issued, expiry, superseded copies (kept, not deleted), where it was used, derived copies.
- A document that goes stale (a certificate valid 3 months, an expiring card) also appears
  in the dashboard's "Expiring or stale documents" with its date.
- A document kept in another system is a register row with its link. Anything sent to a
  body also keeps a copy in the folder as its current file. A link is opened only when the
  owner asks, with the session's own tools; nothing from the folder is searched for or
  sent there.

## Correspondence

- An email goes in the process of the counterparty it concerns, even when it arrived via a
  third party (an adviser writing about a residence card belongs to the residence process).
- Keep an exact copy: `.md` with the full headers and body, or `.eml` with a
  `.metadata.json` sidecar (bulk imports: `scripts/gmail_archive.py`). Log the `.eml`.
- Log every kept email in `shared/correspondence/email-log.md` with its root-relative path.
- `sent-emails/`, `received-emails/` and `portal-responses/` are append-only: never edit or
  delete a file in them. Adding a new one, or moving a whole folder, is fine.

## Deadlines

The dashboard's "Next deadlines" table (`| YYYY-MM-DD | Area | What |`) feeds the session
report, which counts days left or overdue. Record the legal basis of a statutory deadline
in the area's `reference.md`, and the deadline itself in the table.

## Moving files

1. Move with `git mv` (or a plain move outside git).
2. Add `| \`old\` | \`new\` |` rows to `docs/path-map.md`; a trailing `/` maps a folder.
3. Run `scripts/rewrite_paths.py`, then `scripts/check_links.py`.

## Reference

Whenever something useful is learned, add it to the area's `reference.md` (or
`shared/reference.md`): source link or path, date checked, short summary, key quotes,
practical implication. Official sources first. For local providers: name, address,
phone/email, website. No identifiers.

## Sensitive data

`personal-details.md` (mode 600) holds identifiers: document numbers, tax and social
security numbers, case and request numbers, phone. Its `## Identifiers checked` table lists
every value the repo check looks for; add a row whenever a new identifier is recorded.

Identifiers may appear only in:

- `personal-details.md`
- a process folder: drafts, submissions, visits and correspondence must quote them
- the email log (exact subject lines) and the path map (old paths)
- the evidence files in `documents/`

Never in a `reference.md`, an area or root README, the register, a file or folder name,
or anything shared. Write "the tax case" or "the residence request" and let the reader
look the number up.

## Sending, paying, signing

The agent drafts; the owner decides. Never, without the owner's explicit go-ahead for that
specific item: send or reply to an email, submit a form or portal request, pay, sign, or
delete a document or record. A draft lives in the process's `drafts/` until it is sent;
the sent copy then goes in `sent-emails/` and the log.

## Where the files live

A flow-life folder can be a git repository with no remote, so nothing leaves the machine;
history and the pre-commit check still work. A plain folder works too, without history or
the commit check. A remote is the owner's choice. Whatever the agent reads (a scan, an
email) is sent to the model provider to be processed, wherever the folder lives.

## Before committing

`scripts/check_repo.py` must print `0 problem(s)`; the pre-commit hook runs it and refuses
edits or deletions of records. It fails when a document is not in the register, an email is
not in the log, the identifiers file or an email is readable by others (`--fix-modes`
repairs), an identifier appears where it must not, a status block is invalid, or a path
reference does not resolve. Fix the cause; never bypass with `--no-verify`.
