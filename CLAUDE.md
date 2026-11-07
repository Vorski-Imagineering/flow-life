# flow-life

The flow-life Claude Code plugin (`plugins/flow-life/`), shipped from the `flow-life`
marketplace (`.claude-plugin/marketplace.json`) in this repo, `Vorski-Imagineering/flow-life`.
The repo is public.

## What a change here does

`main` is what every adopting folder installs, and adopting folders hold people's
identity documents and correspondence. So:

- **The repo names no person, place, body or case**, in the plugin, tests or docs.
  Anything particular belongs in an adopting folder's `CLAUDE.md` or profile.
  `tests/test_no_personal_data.py` fails on the words in `.personal-words` (git-ignored,
  one regex per line) or `FLOW_LIFE_PERSONAL_WORDS`; add a word there when a new one turns
  up. Never commit the word list: it is personal itself. Test fixtures use made-up areas
  (`visa`, `licence`, `tax`).
- **Every path comes from the profile** (`scripts/flowconfig.py`, `DEFAULTS`). A new
  setting ships with a default and a row in `references/profile-schema.md` (a test checks).
  A change with no safe default bumps `profile`.
- **Scripts never send, pay, delete a document, or touch a network.** Skills draft; the
  owner acts.
- **Hooks stay silent outside a flow-life folder** (no profile above the working folder),
  so a user-scope install changes nothing elsewhere.
- **A `SKILL.md` has 500 lines or fewer** (a test checks).

## Hard Stops: ask before changing

- What a script writes to an adopting folder, or what a hook refuses.
- The profile format.
- Anything that would put files, identifiers or text from an adopting folder on a network.

## Tests

```bash
python3 -m unittest discover -s tests
```

A new test is not finished until it has been seen failing: break the thing it names, run
it, confirm red, restore.
