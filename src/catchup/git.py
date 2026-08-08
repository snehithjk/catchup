"""Minimal, checked wrappers around the local git executable."""

import os
import subprocess
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from .models import CommitRecord


class GitError(RuntimeError):
    pass


def run_git(repo: str, args: Sequence[str], check: bool = True) -> str:
    command = ["git", "-C", os.fspath(repo)] + list(args)
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if check and result.returncode:
        detail = result.stderr.strip() or "git command failed"
        raise GitError("{}: {}".format(" ".join(command), detail))
    return result.stdout


def repo_root(repo: str) -> str:
    return run_git(repo, ["rev-parse", "--show-toplevel"]).strip()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


def log(repo: str, since: Optional[str] = None,
        before: Optional[str] = None) -> List[CommitRecord]:
    args = ["log", "--all", "--date=iso-strict",
            "--format=%H%x00%aI%x00%ae%x00%cE%x00%P%x00%B%x1e"]
    if since:
        args.append("--since={}".format(since))
    if before:
        args.append("--before={}".format(before))
    raw = run_git(repo, args)
    records = []
    for chunk in raw.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        fields = chunk.split("\x00", 5)
        if len(fields) != 6:
            continue
        commit, authored_at, author_email, committer_email, parents, message = fields
        records.append(CommitRecord(
            commit=commit.strip(),
            authored_at=_parse_datetime(authored_at),
            author_email=author_email.strip().lower(),
            committer_email=committer_email.strip().lower(),
            parents=tuple(parents.split()),
            subject=message.strip().splitlines()[0] if message.strip() else "(no subject)",
            message=message.strip(),
        ))
    return records


def diff(repo: str, record: CommitRecord) -> str:
    if record.parents:
        return run_git(repo, ["diff", "--no-ext-diff", "--find-renames",
                              record.parents[0], record.commit, "--"])
    return run_git(repo, ["show", "--format=", "--no-ext-diff",
                          "--find-renames", "--root", record.commit, "--"])


def changed_paths(repo: str, record: CommitRecord) -> List[Tuple[str, str]]:
    if record.parents:
        raw = run_git(repo, ["diff", "--name-status", "--find-renames",
                             record.parents[0], record.commit, "--"])
    else:
        raw = run_git(repo, ["diff-tree", "--root", "--no-commit-id", "-r",
                             "--name-status", "--find-renames", record.commit])
    result = []
    for line in raw.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status = fields[0]
        path = fields[-1]
        result.append((status, path))
    return result


def numstat(repo: str, record: CommitRecord) -> List[Tuple[str, int, int]]:
    if record.parents:
        raw = run_git(repo, ["diff", "--numstat", "--find-renames",
                             record.parents[0], record.commit, "--"])
    else:
        raw = run_git(repo, ["show", "--format=", "--numstat", record.commit, "--"])
    result = []
    for line in raw.splitlines():
        fields = line.split("\t")
        if len(fields) != 3:
            continue
        added = int(fields[0]) if fields[0].isdigit() else 0
        removed = int(fields[1]) if fields[1].isdigit() else 0
        result.append((fields[2], added, removed))
    return result


def list_files(repo: str) -> List[str]:
    return [line for line in run_git(repo, ["ls-files"]).splitlines() if line]
