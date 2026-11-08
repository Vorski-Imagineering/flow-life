# {title}

This folder runs on the flow-life plugin. The working rules (layout, status blocks,
documents, correspondence, sensitive data, moving files) are in the plugin's
rules (rules.md in its references folder); every `/flow-life:` skill loads them. This file holds only what
is particular to this person and this folder.

## Background

Who this is for, where they live, and what each area covers. Keep identifiers out:
they belong in `{identifiers}`.

## Areas

One line per area: what it covers and which bodies it deals with.

## Documents held

Short overview by `{documents_dir}/<type>/` folder; `{register}` is the detail.

## Other systems

Documents or records kept outside this folder (a Drive folder, a supplier portal), and
which tool in a Claude Code session reads each. A link is opened only when the owner asks;
nothing from this folder is searched for or sent there.
