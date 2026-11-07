# flow-life

**Your paperwork as a folder an agent keeps in order.**

Residence permits, driving licences, tax returns, social security, a landlord dispute:
each one runs for months, every body asks for the same documents, letters have to be
quoted exactly later, and a missed date costs money. flow-life is a Claude Code plugin
that keeps all of it in one folder, the same way every time, so you (or Claude) can pick
up any thread cold:

- **Areas and processes.** Long-lived areas (residence, tax, ...) hold bounded processes
  (an application, a complaint), each with a status block: `active` (you owe the next
  move), `waiting` (they do) or `closed`, and one line saying what happens next.
- **A document register.** One file says which copy of each document is current, when it
  expires, what it replaced and where it was sent.
- **Correspondence as a record.** Emails are kept exactly, logged, filed under the
  counterparty they concern, and never edited (a hook refuses).
- **Identifiers stay put.** Passport, tax and case numbers live in one owner-only file; a
  check fails if one turns up in a README, a reference note or a file name.
- **A status report every session**: open processes, deadlines with days left or overdue,
  expiring documents, and whether the folder passes its check.
- **Safe reorganising.** Every move is recorded; references and symlinks are rewritten.

The rules are in [`plugins/flow-life/references/rules.md`](plugins/flow-life/references/rules.md).

## Where your files live

Wherever you choose. flow-life needs only a folder on your own disk:

- **A git repository with no remote** (recommended): history, and a pre-commit check;
  nothing leaves your machine.
- **A git repository with a private remote**, if you want a backup on that host.
- **A plain folder**: works, without history or the commit check.

One thing to know: files Claude reads (a scan, an email) are sent to the model provider
to be processed, wherever the folder lives.

## Start

Install it for one folder (from inside that folder):

```bash
claude plugin marketplace add Vorski-Imagineering/flow-life --scope project
claude plugin install flow-life@flow-life --scope project
```

Then in Claude Code:

1. **`/flow-life:setup`**: checks the folder and sets up what is missing. In an empty
   folder it asks for your areas and where files should live, then lays everything out.
   In a folder that already holds paperwork it proposes where each file goes and moves
   nothing without your approval.
2. **`/flow-life:new-process`** for the first piece of real work.
3. **`/flow-life:status`** whenever you want to know where things stand. (The same
   report opens every session.)

To use it in every folder instead, install with `--scope user`; it stays silent in any
folder without a `.agents/flow-life.toml`.

## Skills

| Skill | Does |
|---|---|
| `setup` | start a folder, adopt an existing one, or re-check one |
| `status` | where everything stands (reads only) |
| `new-process` | open a process with its status block and todo |
| `close-process` | record the outcome and move it to `closed/` |
| `file-email` | keep an email exactly, in the right process, logged |
| `register-document` | add or replace a document; record expiry and use |
| `move` | move files and keep every reference working |
| `reference` | keep what was learned, sourced and dated |

The agent drafts; you send, pay, sign and submit. No skill does those for you.

## Your folder's profile

`.agents/flow-life.toml` holds what your folder does differently: area names, file
locations, the report title. Every setting has a default:
[`references/profile-schema.md`](plugins/flow-life/references/profile-schema.md).

## Developing

```bash
python3 -m unittest discover -s tests
```

To try a working copy in a folder without installing: `claude --plugin-dir /path/to/flow-life/plugins/flow-life`.

MIT licence.
