"""Minimal, checked wrappers around the local git executable."""

import os
import subprocess
import tarfile
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

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


def discover_email(repo: str) -> str:
    """Use local Git identity, falling back to the current branch author."""
    configured = run_git(repo, ["config", "--get", "user.email"], check=False).strip()
    if configured:
        return configured.lower()
    return run_git(repo, ["log", "-1", "--format=%ae"]).strip().lower()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


def log(repo: str, since: Optional[str] = None,
        before: Optional[str] = None, ref: str = "HEAD",
        first_parent: bool = False) -> List[CommitRecord]:
    args = ["log", "--date=iso-strict",
            "--format=%H%x00%aI%x00%ae%x00%cE%x00%P%x00%B%x1e"]
    if since:
        args.append("--since={}".format(since))
    if before:
        args.append("--before={}".format(before))
    if first_parent:
        args.append("--first-parent")
    # A ref already includes merged side-branch history. Do not add --all:
    # fetched-but-unmerged remote branches are not part of this checkout's program.
    args.append(ref)
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


def list_files_at_commit(repo: str, commit: str) -> List[str]:
    return [line for line in run_git(repo, ["ls-tree", "-r", "--name-only", commit]).splitlines()
            if line]


def paths_for_commits(repo: str, since: Optional[str] = None,
                      before: Optional[str] = None, ref: str = "HEAD",
                      first_parent: bool = False) -> Dict[str, List[str]]:
    """Collect commit-to-path metadata in one history walk."""
    args = ["log", "--name-only", "--format=commit:%H"]
    if since:
        args.append("--since={}".format(since))
    if before:
        args.append("--before={}".format(before))
    if first_parent:
        args.append("--first-parent")
    args.append(ref)
    result = {}
    current = None
    for line in run_git(repo, args).splitlines():
        if line.startswith("commit:"):
            current = line[7:].strip()
            result[current] = []
        elif current and line.strip():
            result[current].append(line.strip())
    return result


def file_at_commit(repo: str, commit: str, path: str) -> str:
    return run_git(repo, ["show", "{}:{}".format(commit, path)])


def source_files_at_commit(repo: str, commit: str) -> Dict[str, str]:
    """Read graph-relevant source files from one exact tree in one git stream."""
    command = ["git", "-C", os.fspath(repo), "archive", "--format=tar", commit]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = {}
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for member in archive:
                path = member.name
                if not member.isfile() or not path.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                try:
                    result[path] = extracted.read().decode("utf-8")
                except UnicodeDecodeError:
                    continue
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        return_code = process.wait()
    finally:
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
        if process.poll() is None:
            process.kill()
            process.wait()
    if return_code:
        raise GitError(stderr.strip() or "git archive failed")
    return result


def resolve_commit(repo: str, commit: str) -> str:
    """Resolve an abbreviated commit and fail with a useful git error."""
    return run_git(repo, ["rev-parse", "--verify", "{}^{{commit}}".format(commit)]).strip()


def diff_for_commit(repo: str, commit: str) -> str:
    """Read a commit diff without enumerating the repository's full history."""
    full_commit = resolve_commit(repo, commit)
    parents = run_git(repo, ["rev-list", "--parents", "-n", "1", full_commit]).split()[1:]
    if parents:
        return run_git(repo, ["diff", "--no-ext-diff", "--find-renames",
                              parents[0], full_commit, "--"])
    return run_git(repo, ["show", "--format=", "--no-ext-diff",
                          "--find-renames", "--root", full_commit, "--"])
