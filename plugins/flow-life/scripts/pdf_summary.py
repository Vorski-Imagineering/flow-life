#!/usr/bin/env python3
"""Say whether a PDF's Markdown summary exists and is current. Never writes.

    pdf_summary.py status <pdf>   exit 0 and the summary path when `<pdf minus .pdf>.md` exists
                                  and its first line carries the PDF's current SHA-256;
                                  exit 1 and `none` when there is no such file;
                                  exit 3 and `stale` when the file is a summary of another
                                  version of the PDF (a stamp with a different hash);
                                  exit 4 and `foreign` when the file exists but is not a
                                  summary at all (no stamp): never to be overwritten
    pdf_summary.py stamp <pdf>    print that first line for the PDF

A missing PDF is exit 2 with a reason. The summary itself is written by the agent
(`/flow-life:read-pdf`); this script only keeps it honest.
"""
import hashlib
import re
import sys
from pathlib import Path

STAMP = "<!-- flow-life:pdf-summary sha256={} -->"
STAMP_RE = re.compile(r"^<!-- flow-life:pdf-summary sha256=([0-9a-f]{64}) -->\s*$")


def digest(pdf):
    with open(pdf, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def summary_path(pdf):
    return Path(pdf).with_suffix(".md")


def status(pdf):
    summary = summary_path(pdf)
    if not summary.is_file():
        return 1, "none"
    with open(summary, errors="replace") as f:
        first = f.readline()
    m = STAMP_RE.match(first)
    if not m:
        # a mangled stamp is still ours: stale, so the summary is refreshed, not kept forever
        return (3, "stale") if first.startswith("<!-- flow-life:pdf-summary") else (4, "foreign")
    if m.group(1) != digest(pdf):
        return 3, "stale"
    return 0, str(summary)


def main(argv):
    if len(argv) != 3 or argv[1] not in ("status", "stamp"):
        print(__doc__, file=sys.stderr)
        return 2
    if not Path(argv[2]).is_file():
        print(f"pdf_summary.py: no such file: {argv[2]}", file=sys.stderr)
        return 2
    if argv[1] == "stamp":
        print(STAMP.format(digest(argv[2])))
        return 0
    code, text = status(argv[2])
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
