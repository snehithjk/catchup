"""Small, serializable data objects shared by catchup's pipeline stages."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CommitRecord:
    commit: str
    authored_at: datetime
    author_email: str
    committer_email: str
    parents: Tuple[str, ...]
    subject: str
    message: str

    @property
    def short_commit(self) -> str:
        return self.commit[:12]

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


@dataclass(frozen=True)
class ExposureEntry:
    path: str
    score: float
    last_seen: str
    basis: Tuple[str, ...]
    last_commit: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "score": round(self.score, 6),
            "last_seen": self.last_seen,
            "basis": list(self.basis),
            "last_commit": self.last_commit,
        }


@dataclass(frozen=True)
class Change:
    commit: str
    authored_at: datetime
    subject: str
    paths: Tuple[str, ...]
    stats: Mapping[str, Tuple[int, int]]
    diff: str
    added_files: Tuple[str, ...] = ()
    deleted_files: Tuple[str, ...] = ()
    dependencies_added: Tuple[str, ...] = ()
    dependencies_removed: Tuple[str, ...] = ()
    signature_paths: Tuple[str, ...] = ()
    is_merge: bool = False

    @property
    def short_commit(self) -> str:
        return self.commit[:12]

    @property
    def item_id(self) -> str:
        return self.commit[:12]

    @property
    def additions(self) -> int:
        return sum(value[0] for value in self.stats.values())

    @property
    def deletions(self) -> int:
        return sum(value[1] for value in self.stats.values())

    @property
    def novelty_flags(self) -> Tuple[str, ...]:
        flags = []
        if self.dependencies_added:
            flags.append("new import or dependency")
        if any("/" not in path for path in self.added_files):
            flags.append("new top-level module")
        if self.deleted_files:
            flags.append("deleted module")
        if self.signature_paths:
            flags.append("public signature change")
        return tuple(flags)


@dataclass(frozen=True)
class RankedChange:
    change: Change
    exposure_overlap: float
    blast_radius: float
    novelty: float
    score: float
    reasons: Tuple[str, ...] = ()
    exposure_paths: Tuple[str, ...] = ()
    exposure_basis: Tuple[str, ...] = ()
    exposure_commit: str = ""

    def to_dict(self) -> Dict[str, object]:
        change = self.change
        return {
            "item_id": change.item_id,
            "commit": change.commit,
            "subject": change.subject,
            "paths": list(change.paths),
            "score": round(self.score, 6),
            "exposure_overlap": round(self.exposure_overlap, 6),
            "blast_radius": round(self.blast_radius, 6),
            "novelty": round(self.novelty, 6),
            "reasons": list(self.reasons),
            "exposure_paths": list(self.exposure_paths),
            "exposure_basis": list(self.exposure_basis),
            "exposure_commit": self.exposure_commit,
        }


@dataclass(frozen=True)
class Feedback:
    item_id: str
    label: str
    created_at: str
    path_prefix: str = ""


@dataclass
class PipelineResult:
    knowledge_map: Dict[str, ExposureEntry] = field(default_factory=dict)
    ranked: List[RankedChange] = field(default_factory=list)
    other_count: int = 0
