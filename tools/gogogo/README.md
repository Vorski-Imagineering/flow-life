# gogogo release scripts

Four scripts copied from the gogogo plugin (gogogo commit `d38ac81eb3a0`), unchanged except for three comment lines in `tracker.py`, reworded because they used a word this public repo's personal-word check refuses: `release.py`,
`profile_check.py`, `stage_sync.py` and `tracker.py`. They run only in CI
(`.github/workflows/release.yml`), where `release.py tag` cuts the `deploy-<build>` tag for
each push to `main` whose tests pass. `release.py` imports the other three from its own
folder, so update all four together, from one gogogo commit.
