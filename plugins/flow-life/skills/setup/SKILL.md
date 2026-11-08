---
name: setup
description: Use when starting a paperwork folder with flow-life, adopting an existing folder of documents and letters onto it, or checking that a flow-life folder is still set up right (profile, register, email log, identifiers table, git and pre-commit hook, plugin install). Also when a flow-life script stopped because no profile was found.
---

# setup: start, adopt, or re-check a flow-life folder

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` first: it is what the folder is being set up to follow.

## 1. Check

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup_check.py"
```

It only reads. Each line is `PASS`, `FAIL` (fix after `->`), `WARN` or `INFO`. Show the
person the whole list, grouped: fine, broken, worth a look. Exit 0 means nothing failed.

Then decide which case this is:

- **No profile, folder (nearly) empty** → § 2 New folder.
- **No profile, folder already holds paperwork** → § 3 Adopt an existing folder.
- **Profile present** → work down the `FAIL` lines, then the `WARN` lines the person wants
  handled, re-running the check after each.

## 2. New folder

Ask, in one message:

1. **Areas**: the long-lived subjects (e.g. residence, driving-licence, tax, health,
   housing). Lower case, hyphens. More can be added later.
2. **Where the files live.** Explain the three choices and what each means:
   - *git, no remote* (recommended): history and the pre-commit check; nothing leaves the
     machine;
   - *git with a private remote*: as above, plus a backup on that host, so the files are
     on that host;
   - *plain folder*: no history, no commit check.
   Whatever they choose, say plainly: files Claude reads are sent to the model provider to
   be processed.
3. **A title** for the dashboard.

Then, with their answers (omit `--git --hooks` for a plain folder):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold.py" init --title "<title>" --areas <a,b,c> --git --hooks
```

It never overwrites a file. Show its output. Then help fill in `CLAUDE.md` (background,
one line per area) and the identifiers table in `personal-details.md`: ask what
identifiers they will be quoting (passport, tax number, case numbers) and add a row for
each. Never copy an identifier anywhere else.

Never add a remote or push unless the person asks for it by name.

## 3. Adopt an existing folder

The folder already holds scans, PDFs, letters and notes. Nothing is moved without approval.

### A folder that already has its own conventions

Read this before step 2 when the folder is a project with its own habits:

- **Its own index**: set `register = "<its path>"` in `.agents/flow-life.toml` before
  running `scaffold.py init`, which then keeps that file and creates no other register;
  `/flow-life:register-document` fills that table's own columns.
- **An existing meaning of "area"**: rename one side before laying out areas, and say which
  in the folder's `CLAUDE.md`.
- **Captured web pages** or other copies whose links point elsewhere: add their folder's
  name to `link_excluded_dirs` (`link_excluded_dirs = ["sources"]`): the link check skips
  them at any depth, and they can still be rewritten. Use `immutable_dirs` instead only
  for evidence that must never change; it also makes them append-only. A list setting
  replaces its default, so add to `immutable_dirs` and `link_excluded_prefixes` with
  their defaults written out (`references/profile-schema.md`).
- **Links**: root-relative by default; a path whose first segment is not a top-level name
  is read relative to the file that holds it.
- **The project's own commit checks**: in `.githooks/pre-commit` (a Python script), replace
  its last line with one that runs flow-life's check and then the project's own only when
  that passed, for example
  `code = subprocess.run(["sh", str(root / "scripts/pre-commit")]).returncode` then
  `sys.exit(code or subprocess.run(["sh", "-c", "<the project's check command>"]).returncode)`.
  Setup keeps an existing file and a plugin update does not touch it.
- **Documents in other systems**: register rows with their link; name each system, and the
  tool that reads it, under `## Other systems` in `CLAUDE.md`.

1. **Survey, read-only.** List the tree; open what you need to classify it. Do not open
   more personal documents than needed to know what each is.
2. **Propose a mapping** as a table: current path → new path, grouped as documents (by
   type), processes (by area, `<yyyy>-<slug>`, with a proposed status), correspondence,
   references, unknown. Ask about the unknowns.
3. **On approval**, if the folder is not already a git repository, offer `git init`
   first and commit the untouched state, so every later step can be undone. Then run
   `scaffold.py init` (it keeps existing files). If `.agents/flow-life.toml` already
   exists, `scaffold.py init` creates each file where it says. Move in batches with
   `/flow-life:move` (each batch: `git mv`, path-map rows, rewrite, link check, commit).
4. **Fill the indexes**: a register row for each document, a log row for each kept
   email, a status block for each process, the dashboard, the identifiers table.
5. Re-run the setup check until the repo check line passes.

## 4. Install the plugin for this folder

If the check says the plugin is not enabled at project scope and the person wants every
session here to load it:

```bash
claude plugin marketplace add Vorski-Imagineering/flow-life --scope project
claude plugin install flow-life@flow-life --scope project
```

That writes `.claude/settings.json`. In a git folder, commit it.

## 5. Finish

Re-run the check and show the final list. Then suggest `/flow-life:status` and, for the
first piece of real work, `/flow-life:new-process`.
