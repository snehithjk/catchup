"""Turn git commits into small, inspectable logical changes."""

import re
from typing import Dict, Iterable, List, Sequence, Tuple

from .git import changed_paths, diff, numstat
from .models import Change, CommitRecord


_SIGNATURE = re.compile(
    r"^[+-]\s*(?:async\s+)?(?:def|class|function|export\s+(?:default\s+)?(?:function|class|const|let)|interface|type)\b"
)
_IMPORT = re.compile(
    r"^[+]\s*(?:import\s+.+?\s+from\s+|import\s+|from\s+|const\s+\w+\s*=\s*require\()([\w@./-]+)"
)


def _dependency_deltas(paths: Sequence[str], patch: str) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    dependency_file = any(
        name.endswith(("requirements.txt", "requirements-dev.txt", "package.json",
                       "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                       "pyproject.toml", "poetry.lock")) or "lock" in name
        for name in paths
    )
    added = set()
    removed = set()
    for line in patch.splitlines():
        if not line or line.startswith(("+++", "---")):
            continue
        if line.startswith("+"):
            match = _IMPORT.match(line)
            if match:
                added.add(match.group(1))
            elif dependency_file:
                value = line[1:].strip()
                if value and not value.startswith(("{", "[", "#")):
                    added.add(value[:100])
        elif line.startswith("-"):
            match = re.match(r"^[-]\s*(?:import\s+.+?\s+from\s+|import\s+|from\s+)([\w@./-]+)", line)
            if match:
                removed.add(match.group(1))
    return tuple(sorted(added)), tuple(sorted(removed))


def ingest(repo: str, records: Sequence[CommitRecord]) -> Tuple[Change, ...]:
    result = []
    for record in records:
        statuses = changed_paths(repo, record)
        patch = diff(repo, record)
        stats = {path: (added, removed) for path, added, removed in numstat(repo, record)}
        paths = tuple(sorted({path for _, path in statuses} | set(stats)))
        added_files = tuple(sorted(path for status, path in statuses if status.startswith("A")))
        deleted_files = tuple(sorted(path for status, path in statuses if status.startswith("D")))
        signature_paths = set()
        current_path = ""
        for line in patch.splitlines():
            if line.startswith("--- a/"):
                current_path = line[6:]
            elif line.startswith("+++ b/"):
                current_path = line[6:]
            elif line.startswith("@@"):
                continue
            elif current_path and _SIGNATURE.match(line):
                signature_paths.add(current_path)
        dependencies_added, dependencies_removed = _dependency_deltas(paths, patch)
        result.append(Change(
            commit=record.commit,
            authored_at=record.authored_at,
            subject=record.subject,
            paths=paths,
            stats=stats,
            diff=patch,
            added_files=added_files,
            deleted_files=deleted_files,
            dependencies_added=dependencies_added,
            dependencies_removed=dependencies_removed,
            signature_paths=tuple(sorted(signature_paths)),
            is_merge=record.is_merge,
        ))
    return tuple(result)
