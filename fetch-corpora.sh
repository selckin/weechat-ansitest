#!/bin/sh
# Fetch the test corpora into corpora/ at the commits in corpora.lock.
# The corpora are read as text by ansitest/cases/*.py, never executed.
set -eu
cd "$(dirname "$0")"
# Ignore URL rewrites (insteadOf) from the user's git configuration.
export GIT_CONFIG_GLOBAL=/dev/null
mkdir -p corpora
grep -v '^#' corpora.lock | while read -r name url commit; do
    [ -n "$name" ] || continue
    dir=corpora/$name
    if [ ! -d "$dir/.git" ]; then
        git init -q "$dir"
        git -C "$dir" remote add origin "$url"
    fi
    git -C "$dir" fetch -q --depth 1 origin "$commit"
    git -C "$dir" checkout -q --detach FETCH_HEAD
    echo "$name $(git -C "$dir" rev-parse HEAD)"
done
