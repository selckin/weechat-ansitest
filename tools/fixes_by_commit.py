#!/usr/bin/env python3
"""Find which cases each commit of a WeeChat branch fixes.

Usage: tools/fixes_by_commit.py WORKTREE BUILD_DIR BASE BRANCH OUTPUT_DIR

WORKTREE is a git worktree of WeeChat (its checkout is restored at the
end, and the build directory is built again for it), BUILD_DIR a
configured build directory of that worktree. Each commit of BASE..BRANCH,
and BASE itself, is checked out, built and run with ansicheck --json; the
results go to OUTPUT_DIR/NN-<hash>.json. Then OUTPUT_DIR/summary.json lists,
for each commit, the (path, key) results that changed from fail to pass or
diverge ("fixed") and the ones that changed the other way ("broken").
"""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOOD = ("pass", "diverge")


def git(worktree: str, *args: str) -> str:
    return subprocess.run(["git", "-C", worktree, *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def main() -> None:
    if len(sys.argv) != 6:
        sys.exit(__doc__.strip())
    worktree, build, base, branch, output = sys.argv[1:]
    out = pathlib.Path(output)
    out.mkdir(parents=True, exist_ok=True)
    commits = [git(worktree, "rev-parse", base)]
    commits += git(worktree, "rev-list", "--reverse", f"{base}..{branch}").split()
    original = git(worktree, "rev-parse", "HEAD")
    summary: list[dict] = []
    try:
        run_commits(worktree, build, out, commits, summary)
    finally:
        git(worktree, "checkout", "-q", "--detach", original)
        # So that the build matches the checkout again.
        build_commit(build, original)
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")


def build_commit(build: str, commit: str) -> None:
    build_log = subprocess.run(["cmake", "--build", build, "-j12"], capture_output=True, text=True)
    if build_log.returncode != 0:
        sys.exit(f"{commit[:12]}: build failed\n{build_log.stdout[-2000:]}")


def run_commits(worktree: str, build: str, out: pathlib.Path, commits: list[str],
                summary: list[dict]) -> None:
    previous = None
    for number, commit in enumerate(commits):
        subject = git(worktree, "log", "-1", "--format=%s", commit)
        result = out / f"{number:02d}-{commit[:12]}.json"
        if not result.exists():
            git(worktree, "checkout", "-q", "--detach", commit)
            build_commit(build, commit)
            subprocess.run([str(ROOT / "ansicheck"), "--build", build, "--json", str(result)],
                           stdout=subprocess.DEVNULL, check=False)
        status = {(r["path"], r["key"]): r["status"] for r in json.loads(result.read_text())}
        fails = sum(1 for value in status.values() if value == "fail")
        entry = {"number": number, "commit": commit[:12], "subject": subject, "failures": fails}
        if previous is not None:
            entry["fixed"] = sorted(f"{path} {key}" for (path, key), value in status.items()
                                    if value in GOOD and previous.get((path, key)) == "fail")
            entry["broken"] = sorted(f"{path} {key}" for (path, key), value in status.items()
                                     if value == "fail" and previous.get((path, key)) in GOOD)
        print(f"{number:2} {commit[:12]} {fails:5} failures  "
              f"+{len(entry.get('fixed', []))} -{len(entry.get('broken', []))}  {subject}",
              flush=True)
        summary.append(entry)
        previous = status


if __name__ == "__main__":
    main()
