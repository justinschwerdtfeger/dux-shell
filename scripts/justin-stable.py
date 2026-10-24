#!/usr/bin/env python3
"""Prepare a candidate locally; publication is a separate, tested workflow step."""

import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.request import urlopen

UPSTREAM = "https://github.com/duxlabs-dev/dux-shell.git"
RELEASES = "https://api.github.com/repos/duxlabs-dev/dux-shell/releases"
RECORD = Path(".github/justin/upstream-stable.json")


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def version(tag):
    match = re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag or "")
    if not match:
        raise ValueError(f"Expected a stable vX.Y.Z release tag, got {tag!r}")
    return tuple(map(int, match.groups()))


def select_release(releases):
    stable = []
    for release in releases:
        if release["draft"] or release["prerelease"]:
            continue
        try:
            key = version(release["tag_name"])
        except ValueError:
            continue
        stable.append((key, release["tag_name"]))
    if not stable:
        raise ValueError("No published stable vX.Y.Z release found")
    return max(stable)[1]


def latest_stable():
    releases = []
    for page in range(1, 101):
        with urlopen(f"{RELEASES}?per_page=100&page={page}", timeout=60) as response:
            batch = json.load(response)
        releases.extend(batch)
        if len(batch) < 100:
            return select_release(releases)
    raise ValueError("Release pagination exceeded safety limit")


def validate_record(record):
    version(record["tag"])
    if not re.fullmatch(r"[0-9a-f]{40}", record["commit"] or ""):
        raise ValueError("Bootstrap the stable record with the upstream release commit first")
    git("merge-base", "--is-ancestor", record["commit"], "HEAD")


def integrate(record, tag, commit):
    if version(tag) < version(record["tag"]):
        raise ValueError("Refusing an upstream release rollback")
    if tag == record["tag"]:
        if commit != record["commit"]:
            raise ValueError("Recorded upstream release tag moved; manual review required")
        return
    git("merge-base", "--is-ancestor", record["commit"], commit)
    # Keep fork automation out of upstream merges, including workflow-only conflicts.
    try:
        git("merge", "--no-ff", "--no-commit", commit)
    except subprocess.CalledProcessError:
        conflicts = git("diff", "--name-only", "--diff-filter=U").splitlines()
        if not conflicts or any(not path.startswith(".github/") for path in conflicts):
            raise
    git("restore", "--source=HEAD", "--staged", "--worktree", "--", ".github")
    RECORD.write_text(json.dumps({"tag": tag, "commit": commit}, indent=2) + "\n")
    git("add", str(RECORD))
    git("commit", "-m", f"upstream: merge stable release {tag}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()
    record = json.loads(RECORD.read_text())
    validate_record(record)
    if not args.sync:
        return
    tag = latest_stable()
    # Fetch exactly one release tag, never master/stable branch heads or moving submodule refs.
    git("-c", "http.https://github.com/.extraheader=", "fetch", "--no-tags", UPSTREAM, f"refs/tags/{tag}")
    commit = git("rev-parse", "FETCH_HEAD^{commit}")
    integrate(record, tag, commit)


if __name__ == "__main__":
    main()
