"""Split a markdown file into H2 sections and route them to destination files."""
from pathlib import Path

FENCE = "`" * 3


def split_sections(text):
    lines = text.splitlines(keepends=True)
    pre, secs, cur, head, fence = [], [], None, None, False
    for line in lines:
        if line.startswith(FENCE):
            fence = not fence
        if not fence and line.startswith("## "):
            if cur is not None:
                secs.append((head, "".join(cur)))
            head, cur = line[3:].strip(), [line]
        elif cur is None:
            pre.append(line)
        else:
            cur.append(line)
    if cur is not None:
        secs.append((head, "".join(cur)))
    return "".join(pre), secs


def assign(heading, rules):
    for prefix, dest in rules:
        if heading.startswith(prefix):
            return dest
    return None


def route(src, rules, headers, root):
    """Append each section of src to its destination; returns unassigned headings."""
    _, secs = split_sections(Path(src).read_text())
    out, missing = {}, []
    for head, body in secs:
        dest = assign(head, rules)
        if dest is None:
            missing.append(head)
            continue
        out.setdefault(dest, []).append(body.rstrip("\n") + "\n\n")
    if missing:
        return missing
    for dest, bodies in out.items():
        p = Path(root) / dest
        p.parent.mkdir(parents=True, exist_ok=True)
        existing = p.read_text() if p.exists() else headers.get(dest, "")
        p.write_text(existing.rstrip("\n") + "\n\n" + "".join(bodies).rstrip("\n") + "\n")
    return []
