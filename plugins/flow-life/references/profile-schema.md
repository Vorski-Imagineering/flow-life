# flow-life profile

`.agents/flow-life.toml` in the folder's root. Every setting is optional;
a setting not named keeps the default below. An unknown setting is an error.

`profile` is the format version. A change to the format that has no safe default bumps it.

| Setting | Default |
|---|---|
| `profile` | `1` |
| `areas` | `[]` |
| `documents_dir` | `"documents"` |
| `register` | `"documents/register.md"` |
| `email_log` | `"shared/correspondence/email-log.md"` |
| `identifiers` | `"personal-details.md"` |
| `identifier_heading` | `"## Identifiers checked"` |
| `path_map` | `"docs/path-map.md"` |
| `dashboard` | `"README.md"` |
| `deadlines_heading` | `"Next deadlines"` |
| `expiring_heading` | `"Expiring or stale documents"` |
| `report_title` | `"Status"` |
| `immutable_dirs` | `["sent-emails", "received-emails", "portal-responses"]` |
| `email_dirs` | `["sent-emails", "received-emails"]` |
| `id_allowed_files` | `[]` |
| `id_allowed_prefixes` | `["tmp/"]` |
| `id_text_suffixes` | `[".md", ".html", ".py", ".json", ".txt", ".csv"]` |
| `link_excluded_files` | `[]` |
| `link_excluded_prefixes` | `[".git/", "tmp/"]` |
| `link_excluded_dirs` | `[]` |
| `link_text_suffixes` | `[".md", ".html", ".py"]` |
| `stale_patterns` | `[]` |

Meanings, briefly:

- `areas`: top-level folders holding `processes/`; empty finds them.
- `documents_dir`, `register`: evidence folder and the file that must list every file in it.
- `email_log`: must list every file in an `email_dirs` folder.
- `identifiers`, `identifier_heading`: owner-only file and the heading of its table of checked values.
- `path_map`: old -> new rows used by the rewrite and link check.
- `dashboard`, `deadlines_heading`, `expiring_heading`, `report_title`: what the session report reads and prints.
- `immutable_dirs`: append-only folders (edit guard and pre-commit).
- `id_allowed_files`, `id_allowed_prefixes`: extra places identifiers may appear.
- `link_excluded_files`, `link_excluded_prefixes`, `link_excluded_dirs`, `link_text_suffixes`: what the link check skips (by file, by prefix from the root, by folder name at any depth) and reads.
- `stale_patterns`: regular expressions for old names that must not reappear after a reorganisation.
