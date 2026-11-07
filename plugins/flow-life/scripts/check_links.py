#!/usr/bin/env python3
"""Report unresolved path references, broken symlinks and dangling path-map targets."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import flowconfig  # noqa: E402
from pathmap import check  # noqa: E402

if __name__ == "__main__":
    problems = check(flowconfig.load_or_exit())
    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s)", file=sys.stderr)
    sys.exit(1 if problems else 0)
