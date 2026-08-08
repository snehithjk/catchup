"""Pipeline orchestration kept separate from the pure scoring stages."""

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .brief import build_prompt, call_compatible_api, render_stub_brief
from .changes import ingest
from .exposure import build_knowledge_map
from .git import changed_paths, list_files, log, repo_root
from .graph import build_import_graph
from .models import Change, CommitRecord, ExposureEntry, Feedback, PipelineResult, RankedChange
from .ranking import rank_changes
from .storage import load_feedback, save_knowledge_map
from .verify import verify_brief


_DURATION = re.compile(r"^(\d+)([mhdw])$")


def parse_window_start(value: str, as_of: datetime) -> datetime:
    match = _DURATION.match(value.strip().lower())
    if match:
        amount = int(match.group(1))
        units = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
        return as_of - timedelta(seconds=amount * units[match.group(2)])
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _read_contents(repo: str, files: Sequence[str]) -> Dict[str, str]:
    result = {}
    for path in files:
        if not path.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
            continue
        full_path = os.path.join(repo, path)
        try:
            with open(full_path, encoding="utf-8") as handle:
                result[path] = handle.read()
        except (OSError, UnicodeDecodeError):
            continue
    return result


def run_pipeline(repo: str, emails: Sequence[str], window_start: datetime,
                 window_end: Optional[datetime] = None, top_n: int = 10,
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
    window_records = log(root, since=window_start.isoformat(), before=end.isoformat())
    prior_paths = {record.commit: [path for _, path in changed_paths(root, record)]
                   for record in prior_records}
    knowledge_map = build_knowledge_map(
        prior_records, prior_paths, emails, window_start,
        half_life_days=half_life_days,
        authored_weight=authored_weight,
        reviewed_weight=reviewed_weight,
    )
    if persist:
        save_knowledge_map(root, knowledge_map)
    changes = ingest(root, window_records)
    contents = _read_contents(root, list_files(root))
    fan_in = build_import_graph(list(contents), contents)
    feedback = load_feedback(root) if persist else {}
    selected, _ = rank_changes(changes, knowledge_map, fan_in, feedback, top_n=top_n)
    selected_ids = {item.change.item_id for item in selected}
    other_commits = [change.item_id for change in changes if change.item_id not in selected_ids]
    result = PipelineResult(knowledge_map=dict(knowledge_map), ranked=list(selected),
                            other_count=len(other_commits))
    if use_llm and selected:
        brief = call_compatible_api(build_prompt(
            selected, ",".join(emails), tuple(knowledge_map)))
    else:
        brief = render_stub_brief(selected, other_commits)
    grounded, errors = verify_brief(root, brief)
    if not grounded:
        raise RuntimeError("brief failed grounding checks: {}".format("; ".join(errors)))
    return result, brief
