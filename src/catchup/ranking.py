"""Pure relevance scoring."""

from collections import defaultdict
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .graph import path_distance_fan_in
from .models import Change, ExposureEntry, Feedback, RankedChange


def _prefix(path: str) -> str:
    pieces = path.split("/")
    return "/".join(pieces[:-1]) or pieces[0]


def _feedback_for_change(change: Change, feedback: Mapping[str, Feedback]) -> Optional[Feedback]:
    direct = feedback.get(change.item_id)
    if direct:
        return direct
    for path in change.paths:
        inherited = feedback.get("prefix:" + _prefix(path))
        if inherited:
            return inherited
    return None


def _exposure_overlap(change: Change, exposure: Mapping[str, ExposureEntry]) -> float:
    total = 0.0
    for path in change.paths:
        entry = exposure.get(path)
        prefix = _prefix(path)
        if entry:
            total += entry.score
        neighbors = [value.score for known, value in exposure.items()
                     if known != path and _prefix(known) == prefix]
        if neighbors:
            total += 0.25 * max(neighbors)
    return total


def _novelty(change: Change, exposure: Mapping[str, ExposureEntry]) -> Tuple[float, Tuple[str, ...]]:
    value = 1.0
    reasons = []
    if change.dependencies_added:
        value *= 1.25
        reasons.append("new dependency/import")
    if any("/" not in path for path in change.added_files):
        value *= 1.15
        reasons.append("new top-level module")
    if change.deleted_files:
        value *= 1.20
        reasons.append("deleted module")
    if any(path in exposure for path in change.signature_paths):
        value *= 1.35
        reasons.append("signature changed in exposed code")
    return value, tuple(reasons)


def _exposure_context(change: Change, exposure: Mapping[str, ExposureEntry]) -> Tuple[
        Tuple[str, ...], Tuple[str, ...], str]:
    direct_paths = tuple(sorted(path for path in change.paths if path in exposure))
    if not direct_paths:
        return (), (), ""
    # Keep one path/commit pair so the verifier can prove the historical
    # exposure citation contains the path named in the sentence.
    path = max(direct_paths, key=lambda value: (exposure[value].last_seen, value))
    entry = exposure[path]
    return (path,), entry.basis, entry.last_commit


def rank_changes(changes: Sequence[Change], exposure: Mapping[str, ExposureEntry],
                 fan_in: Mapping[str, int], feedback: Mapping[str, Feedback] = None,
                 top_n: int = 10) -> Tuple[Tuple[RankedChange, ...], int]:
    feedback = feedback or {}
    ranked = []
    for change in changes:
        overlap = _exposure_overlap(change, exposure)
        if overlap <= 0:
            continue
        graph_fan_in = [fan_in.get(path, path_distance_fan_in(path)) for path in change.paths]
        blast = max(1.0, float(len(change.paths)) * (1.0 + sum(graph_fan_in) / max(1, len(graph_fan_in))))
        novelty, novelty_reasons = _novelty(change, exposure)
        feedback_entry = _feedback_for_change(change, feedback)
        nudge = {"knew": 0.80, "new": 1.15, "irrelevant": 0.50}.get(
            feedback_entry.label if feedback_entry else "", 1.0)
        score = overlap * blast * novelty * nudge
        reasons = list(novelty_reasons)
        if any(path in exposure for path in change.paths):
            reasons.append("overlaps your exposed files")
        else:
            reasons.append("near an exposed module")
        if feedback_entry:
            reasons.append("feedback: {}".format(feedback_entry.label))
        exposure_paths, exposure_basis, exposure_commit = _exposure_context(change, exposure)
        ranked.append(RankedChange(
            change, overlap, blast, novelty, score, tuple(reasons),
            exposure_paths, exposure_basis, exposure_commit,
        ))
    ranked.sort(key=lambda item: (-item.score, -item.change.authored_at.timestamp(), item.change.commit))
    selected = tuple(ranked[:max(0, top_n)])
    return selected, max(0, len(changes) - len(selected))
