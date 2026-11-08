#!/usr/bin/env python3
"""Say whether a PDF's Markdown summary exists and is current. Never writes.

    pdf_summary.py status <pdf>   exit 0 and the summary path when `<pdf minus .pdf>.md` exists
                                  and its first line carries the PDF's current SHA-256;
                                  exit 1 and `none` when there is no such file;
                                  exit 3 and `stale` when the file exists but the line is
                                  missing or the hash differs
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
    return hashlib.sha256(Path(pdf).read_bytes()).hexdigest()


def summary_path(pdf):
    return Path(pdf).with_suffix(".md")


def status(pdf):
    summary = summary_path(pdf)
    if not summary.is_file():
        return 1, "none"
    first = summary.read_text(errors="replace").split("\n", 1)[0]
    m = STAMP_RE.match(first)
    if not m or m.group(1) != digest(pdf):
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
