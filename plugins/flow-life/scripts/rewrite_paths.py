#!/usr/bin/env python3
"""Rewrite path references and relative symlinks after moves recorded in the path map.

    rewrite_paths.py [--dry-run]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import flowconfig  # noqa: E402
from pathmap import rewrite  # noqa: E402

if __name__ == "__main__":
    for line in rewrite(flowconfig.load_or_exit(), dry_run="--dry-run" in sys.argv):
        print(line)
