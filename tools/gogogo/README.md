# gogogo release scripts

`release.py`, `profile_check.py`, `stage_sync.py` and `tracker.py`, copied from the gogogo
plugin (gogogo commit `d38ac81eb3a0`). They run only in CI (`.github/workflows/release.yml`),
where `release.py tag` cuts the `deploy-<build>` tag for each push to `main` whose tests
pass. `release.py` imports the other three from its own folder, so update all four
together, from one gogogo commit.

The copies are unchanged except for three lines in `tracker.py` (983, 1105 and 1230: a
docstring line and two comments). They use a word this public repo's personal-word check
refuses, so they are reworded to a synonym. Do the same when copying again.
