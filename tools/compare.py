#!/usr/bin/env python3
"""Compare two results of ansicheck --json (for example main and a branch).

Usage: tools/compare.py [--list] BEFORE.json AFTER.json

Prints, per source and path, the number of cases that fail before and
after, the cases fixed (fail before, pass or known divergence after) and
broken (the other way). With --list, also prints every fixed and broken
case. The exit code is 1 if a case is broken.
"""

import json
import sys
from collections import Counter

GOOD = ("pass", "diverge")


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as results:
        return {(r["source"], r["path"], r["key"]): r["status"] for r in json.load(results)}


def main() -> int:
    args = [arg for arg in sys.argv[1:] if arg != "--list"]
    if len(args) != 2:
        sys.exit(__doc__.strip())
    before, after = load(args[0]), load(args[1])
    keys = sorted(set(before) | set(after))
    fixed = [key for key in keys if before.get(key) == "fail" and after.get(key) in GOOD]
    broken = [key for key in keys if before.get(key) in GOOD and after.get(key) == "fail"]
    fails_before = Counter(key[:2] for key in keys if before.get(key) == "fail")
    fails_after = Counter(key[:2] for key in keys if after.get(key) == "fail")
    count_fixed = Counter(key[:2] for key in fixed)
    count_broken = Counter(key[:2] for key in broken)
    print(f"{'source':8} {'path':16} {'before':>7} {'after':>7} {'fixed':>7} {'broken':>7}")
    for group in sorted({key[:2] for key in keys}):
        print(f"{group[0]:8} {group[1]:16} {fails_before[group]:7} {fails_after[group]:7} "
              f"{count_fixed[group]:7} {count_broken[group]:7}")
    print(f"\n{sum(fails_before.values())} failure(s) before, {sum(fails_after.values())} after: "
          f"{len(fixed)} fixed, {len(broken)} broken")
    if "--list" in sys.argv:
        for title, items in (("Fixed", fixed), ("Broken", broken)):
            if items:
                print(f"\n{title}:")
                for source, path, key in items:
                    print(f"  [{path}] {key}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
