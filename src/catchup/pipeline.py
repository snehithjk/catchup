"""Pipeline orchestration kept separate from the pure scoring stages."""

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .brief import build_prompt, call_compatible_api, render_stub_brief
from .changes import ingest
from .exposure import build_knowledge_map
from .git import log, paths_for_commits, repo_root, resolve_commit, source_files_at_commit
from .graph import build_import_graph
from .models import Change, CommitRecord, ExposureEntry, Feedback, PipelineResult, RankedChange
from .ranking import rank_changes
from .storage import (load_feedback, load_last_brief, save_knowledge_map,
                      save_last_brief, save_last_run)
from .verify import verify_brief


_DURATION = re.compile(r"^(\d+)([mhdw])$")


def parse_window_start(value: str, as_of: datetime, last_run: Optional[str] = None) -> datetime:
    if value.strip().lower() == "last":
        if last_run:
            parsed = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        # First use should still be useful; "last" behaves like the normal
        # 30-day window until a previous successful run exists.
        return as_of - timedelta(days=30)
    match = _DURATION.match(value.strip().lower())
    if match:
        amount = int(match.group(1))
        units = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
        return as_of - timedelta(seconds=amount * units[match.group(2)])
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _expand_feedback(feedback, last_brief):
    expanded = dict(feedback)
    for item_id, entry in feedback.items():
        for path in last_brief.get(item_id, ()):
            prefix = path.rsplit("/", 1)[0] if "/" in path else path
            expanded["prefix:" + prefix] = entry
    return expanded


def run_pipeline(repo: str, emails: Sequence[str], window_start: datetime,
                 window_end: Optional[datetime] = None, top_n: int = 5,
                 half_life_days: float = 90.0, authored_weight: float = 1.0,
                 reviewed_weight: float = 0.6, use_llm: bool = False,
                 persist: bool = True) -> Tuple[PipelineResult, str]:
    root = repo_root(repo)
    end = window_end or datetime.now(timezone.utc)
    if window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    prior_records = log(root, before=window_start.isoformat())
    window_records = log(root, since=window_start.isoformat(), before=end.isoformat(),
                         first_parent=True)
    prior_paths = paths_for_commits(root, before=window_start.isoformat())
    knowledge_map = build_knowledge_map(
        prior_records, prior_paths, emails, window_start,
        half_life_days=half_life_days,
        authored_weight=authored_weight,
        reviewed_weight=reviewed_weight,
    )
    if persist:
        save_knowledge_map(root, knowledge_map)
    changes = ingest(root, window_records)
    boundary_records = window_records or prior_records
    boundary_commit = boundary_records[0].commit if boundary_records else resolve_commit(root, "HEAD")
    contents = source_files_at_commit(root, boundary_commit)
    fan_in = build_import_graph(list(contents), contents)
    feedback = load_feedback(root) if persist else {}
    if persist:
        feedback = _expand_feedback(feedback, load_last_brief(root))
    selected, _ = rank_changes(changes, knowledge_map, fan_in, feedback, top_n=top_n)
    selected_ids = {item.change.item_id for item in selected}
    other_commits = [change.item_id for change in changes if change.item_id not in selected_ids]
    result = PipelineResult(knowledge_map=dict(knowledge_map), ranked=list(selected),
                            other_count=len(other_commits))
    if use_llm and selected:
        brief = call_compatible_api(build_prompt(selected, tuple(knowledge_map)))
    else:
        brief = render_stub_brief(selected, other_commits)
    grounded, errors = verify_brief(root, brief)
    if not grounded:
        raise RuntimeError("brief failed grounding checks: {}".format("; ".join(errors)))
    if persist:
        save_last_brief(root, selected)
        save_last_run(root, end.astimezone(timezone.utc).isoformat())
    return result, brief
