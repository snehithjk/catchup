"""Deterministic personal exposure model."""

import math
from datetime import datetime, timezone
from typing import Dict, Iterable, Mapping, Sequence, Set

from .models import CommitRecord, ExposureEntry


def _is_trailer(message: str, label: str, email: str) -> bool:
    wanted = email.lower()
    for line in message.splitlines():
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        if name.strip().lower() == label.lower() and wanted in value.lower():
            return True
    return False


def _age_days(when: datetime, as_of: datetime) -> float:
    return max(0.0, (as_of - when).total_seconds() / 86400.0)


def build_knowledge_map(records: Sequence[CommitRecord], paths_by_commit: Mapping[str, Sequence[str]],
                        emails: Iterable[str], as_of: datetime,
                        half_life_days: float = 90.0,
                        authored_weight: float = 1.0,
                        reviewed_weight: float = 0.6) -> Dict[str, ExposureEntry]:
    identities: Set[str] = {email.strip().lower() for email in emails if email.strip()}
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    scores = {}  # type: Dict[str, float]
    seen = {}  # type: Dict[str, datetime]
    seen_commit = {}  # type: Dict[str, str]
    bases = {}  # type: Dict[str, Set[str]]
    for record in records:
        authored = record.author_email in identities
        reviewed = (
            record.is_merge and record.committer_email in identities
        ) or any(_is_trailer(record.message, label, email)
                 for email in identities for label in ("Co-authored-by", "Reviewed-by"))
        if not authored and not reviewed:
            continue
        weight = max(authored_weight if authored else 0.0,
                     reviewed_weight if reviewed else 0.0)
        decay = math.pow(0.5, _age_days(record.authored_at, as_of) / half_life_days)
        contribution = weight * decay
        for path in paths_by_commit.get(record.commit, ()):
            scores[path] = scores.get(path, 0.0) + contribution
            if path not in seen or record.authored_at > seen[path]:
                seen[path] = record.authored_at
                seen_commit[path] = record.commit
            bases.setdefault(path, set())
            if authored:
                bases[path].add("authored")
            if reviewed:
                bases[path].add("reviewed")
    result = {}
    for path in sorted(scores):
        result[path] = ExposureEntry(
            path=path,
            score=scores[path],
            last_seen=seen[path].astimezone(timezone.utc).isoformat(),
            basis=tuple(sorted(bases[path])),
            last_commit=seen_commit[path],
        )
    return result
