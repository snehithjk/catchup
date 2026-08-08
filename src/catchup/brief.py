"""Brief rendering plus an optional OpenAI-compatible provider edge."""

import json
import os
import re
from typing import List, Mapping, Optional, Sequence
from urllib import request

from .models import RankedChange


def _path_summary(item: RankedChange) -> str:
    paths = list(item.change.paths[:4])
    if len(item.change.paths) > 4:
        paths.append("+{} more".format(len(item.change.paths) - 4))
    return ", ".join("`{}`".format(path) for path in paths) or "the repository"


def truncate_diff(patch: str, prioritized_paths: Sequence[str], limit: int = 12000) -> str:
    """Keep complete diff sections, preferring files in the user's map."""
    if len(patch) <= limit:
        return patch
    chunks = []
    current = []
    for line in patch.splitlines(True):
        if line.startswith("diff --git ") and current:
            chunks.append("".join(current))
            current = []
        current.append(line)
    if current:
        chunks.append("".join(current))
    wanted = set(prioritized_paths)
    chunks.sort(key=lambda chunk: (0 if any(
        re.search(r"b/{}(?:\s|$)".format(re.escape(path)), chunk.splitlines()[0])
        for path in wanted
    ) else 1))
    selected = []
    used = 0
    for chunk in chunks:
        if used + len(chunk) > limit:
            continue
        selected.append(chunk)
        used += len(chunk)
    if not selected:
        return patch[:max(0, limit - 24)] + "\n[diff truncated]\n"
    return "".join(selected) + ("\n[diff truncated]\n" if used < len(patch) else "")


def render_stub_brief(items: Sequence[RankedChange], other_commits: Sequence[str] = ()) -> str:
    lines = ["# catchup brief"]
    for index, item in enumerate(items, 1):
        change = item.change
        paths = _path_summary(item)
        lines.append("## {}. {}".format(index, change.subject))
        lines.append("- {} changed {} (+{} / -{} lines), overlapping your exposed work ({}).".format(
            change.short_commit, paths, change.additions, change.deletions, change.short_commit))
        if item.reasons:
            reason = ", ".join(item.reasons)
            lines.append("- The relevant signal is {}; acting on stale knowledge here risks relying on an old contract ({}).".format(
                reason, change.short_commit))
        else:
            lines.append("- This change is ranked because it sits in a part of the codebase you previously touched ({}).".format(
                change.short_commit))
    if other_commits:
        citations = " ".join("({})".format(commit) for commit in other_commits)
        lines.append("- {} other window changes were not selected for the top-N brief {}.".format(
            len(other_commits), citations))
    if not items and not other_commits:
        # An empty brief contains no claim and therefore needs no citation.
        return "# catchup brief\n"
    return "\n".join(lines) + "\n"


def build_prompt(items: Sequence[RankedChange], email: str,
                 prioritized_paths: Sequence[str] = ()) -> str:
    payload = []
    for item in items:
        payload.append({
            "commit": item.change.commit,
            "subject": item.change.subject,
            "paths": list(item.change.paths),
            "exposure": round(item.exposure_overlap, 4),
            "reasons": list(item.reasons),
            "diff": truncate_diff(item.change.diff, prioritized_paths),
        })
    return (
        "You are writing a sharp colleague's catch-up brief for {}. Return Markdown only. "
        "Write 2-4 short sentences per item. Every sentence must end with a citation in "
        "the form (full-or-short-commit-hash). Mention only paths, symbols, and changes "
        "visible in the supplied diffs. Explain what changed, why it invalidates this "
        "person's prior knowledge, and what stale assumption could break.\n\n{}"
    ).format(email, json.dumps(payload, indent=2, sort_keys=True))


def call_compatible_api(prompt: str) -> str:
    url = os.environ.get("CATCHUP_API_URL", "https://api.openai.com/v1/chat/completions")
    key = os.environ.get("CATCHUP_API_KEY")
    model = os.environ.get("CATCHUP_MODEL", "gpt-4o-mini")
    if not key:
        raise RuntimeError("CATCHUP_API_KEY is required for --llm")
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = request.Request(url, data=body, headers={
        "Authorization": "Bearer {}".format(key),
        "Content-Type": "application/json",
    }, method="POST")
    with request.urlopen(req, timeout=90) as response:
        value = json.loads(response.read().decode("utf-8"))
    return value["choices"][0]["message"]["content"]
