+++
profile = 1
independence = "product-owner"

[tracker]
kind = "github-project"
issues_repo = "Vorski-Imagineering/flow-life"
code_repo = "Vorski-Imagineering/flow-life"
public = true
ready_marker = "dev ready"
tool = "shared"
project_owner = "Vorski-Imagineering"
project_number = 7
queue = "Dev Ready"
columns = { in_progress = "In progress", needs_human = "Human!Help!" }

[hard_stops]
source = "CLAUDE.md § Hard Stops: ask before changing"
form = "categories"
items = [
  "What a script writes to an adopting folder, or what a hook refuses.",
  "The profile format.",
  "Anything that would put files, identifiers or text from an adopting folder on a network.",
]

[design]
placement_rule = "CLAUDE.md § What a change here does"

[[lanes]]
name = "unit"
run = "python3 -m unittest discover -s tests"
focused = "python3 -m unittest discover -s tests -p '<test_file>.py'"
tests = ["tests/*"]
ci = true

[[lanes]]
name = "live"
env = "local"

# The plugin's "production" is its main branch: every adopting folder installs it.
# Merging to main is the release; there is no pre-production step.
[[environments]]
name = "local"
roles = ["pre-merge"]
serves = "this working tree, loaded with --plugin-dir <clone>/plugins/flow-life in a scratch folder"
writes = "only in a scratch folder made for the check; never in a folder holding someone's paperwork"

[[environments]]
name = "main"
roles = ["production"]
url = "https://github.com/Vorski-Imagineering/flow-life"
reached_by = "a merge to main; adopting folders pick it up on their next plugin update"
writes = "through a PR"

[[stages]]
code_is = "merged to main"
environment = "main"
column = "Released"
moved_by = "the loop or /gogogo:dev, after the merge is verified"

[verify]
agent = ["local"]
human = "main"
rungs = ["seen-failing", "unit", "live"]

[state]
forbidden = [
  "reading or writing a real adopting folder (one holding someone's paperwork)",
  "committing .personal-words, or any word from it",
  "a script that sends, pays, deletes a document, or touches a network",
]

[gates]
always = ["python3 -m unittest discover -s tests, with .personal-words present so the personal-word test runs"]

[integration]
strategy = "pr-squash"
base = "main"
ci_before_merge = true
workspace = "checkout"

[handback]
reporter = "none"

# deploy-<build> tags and <major>.0.<build> versions (references/versioning.md of the
# gogogo plugin), cut by .github/workflows/release.yml after `tests` passes on each push
# to main, with the scripts copied to tools/gogogo/.
[release]
major = 1
+++

## Recon traps

| Trap | How it bites | Check |
|---|---|---|
| **A personal word in a committed file** | The repo is public and every adopting folder installs `main`; a name, place, body or case number published here cannot be taken back | `tests/test_no_personal_data.py` with `.personal-words` present (it skips without it); the local pre-push hook refuses a push containing one |
| **The personal-word test skipped, read as passed** | With no `.personal-words` and no `FLOW_LIFE_PERSONAL_WORDS`, the test is skipped and the suite still exits 0 | Read the run's `skipped` line; a fresh clone recreates `.personal-words` and the pre-push hook before pushing |
| **Two profiles named "profile"** | `.agents/dev-process.md` is gogogo's process profile for this repo; `.agents/flow-life.toml` and `plugins/flow-life/references/profile-schema.md` are flow-life's own profile for adopting folders. "The profile format" Hard Stop is flow-life's | Say which one a change touches |
| **A path written into a script** | Every path in an adopting folder comes from flow-life's profile (`scripts/flowconfig.py`, `DEFAULTS`) | A new setting has a default and a row in `references/profile-schema.md` (a test checks) |
| **A hook that speaks outside a flow-life folder** | A user-scope install changes every other folder on the machine | Hooks stay silent with no `.agents/flow-life.toml` above the working folder |
| **The installed copy is not the tree you edited** | An adopting folder loads the installed plugin, not this working tree, so a live check tests the old text | Start the scratch session with `--plugin-dir <clone>/plugins/flow-life` and check its plugin path |
| **A `SKILL.md` over 500 lines** | A test fails | Keep detail in the skill's references |

## Lane constraints

- **unit**: `python3 -m unittest discover -s tests`. `tests/` is not a package, so
  one file runs with `-p '<test_file>.py'`. Each new test is seen failing first
  (break the thing it names, run, confirm red, restore). Fixtures use made-up
  areas (`visa`, `licence`, `tax`). CI runs it with the word list from the
  `FLOW_LIFE_PERSONAL_WORDS` secret; pull requests from forks skip that test.
- **live**: a real run of the changed skill or hook in a scratch folder made for
  the check (`/flow-life:setup` in an empty folder lays one out), with the plugin
  loaded from this tree. Never in a folder holding someone's paperwork. Say
  what was run and what was seen.
- **this checkout is live**: a session that loads flow-life with `--plugin-dir`
  pointed at this folder runs whatever branch is checked out here. Don't run such
  a session against a real adopting folder while an issue's branch is checked out.

## superpowers boundary

Design exploration may use `superpowers:brainstorming`. Its output goes into
an issue through `/gogogo:spec`, not into `docs/superpowers/`. Decisions and
plans stay in the issues.
