#!/usr/bin/env python3
"""List every process under <area>/processes/{active,closed}/ with its status block.

    status.py            table of every process; exit 1 if any block is invalid (marked !!)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import flowconfig  # noqa: E402

_LINE = re.compile(r"^(?:-\s*)?\**(Status|Opened|Closed|Outcome|Next):?\**:?\s*(.*)$")
VALID = {"active", "waiting", "closed"}


def read_status(text):
    out = {}
    for line in text.splitlines():
        m = _LINE.match(line.strip())
        if m and m.group(1).lower() not in out:
            out[m.group(1).lower()] = m.group(2).strip()
    return out


def scan(root, areas=()):
    rows = []
    for folder in ("active", "closed"):
        for d in sorted(Path(root).glob(f"*/processes/{folder}/*")):
            if not d.is_dir() or (areas and d.parts[-4] not in areas):
                continue
            row = {"area": d.parts[-4], "folder": folder, "name": d.name,
                   "status": None, "next": None, "problem": None}
            readme = d / "README.md"
            if not readme.exists():
                row["problem"] = "no README.md"
            else:
                s = read_status(readme.read_text())
                row["status"], row["next"] = s.get("status"), s.get("next")
                if row["status"] not in VALID:
                    row["problem"] = f"Status missing or invalid: {row['status']!r}"
                elif folder == "active" and row["status"] == "closed":
                    row["problem"] = "Status closed but folder is active/ — move it to closed/"
                elif folder == "closed" and row["status"] != "closed":
                    row["problem"] = f"Status {row['status']} but folder is closed/"
            rows.append(row)
    return rows


if __name__ == "__main__":
    cfg = flowconfig.load_or_exit()
    rows = scan(cfg.root, cfg.areas)
    for r in rows:
        flag = f"  !! {r['problem']}" if r["problem"] else ""
        print(f"{r['area']:16} {r['folder']:7} {r['name']:36} {r['status'] or '-':8} {r['next'] or ''}{flag}")
    sys.exit(1 if any(r["problem"] for r in rows) else 0)
