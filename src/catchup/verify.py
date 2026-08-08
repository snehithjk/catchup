"""Fail-closed citation and diff-grounding checks."""

import re
from typing import List, Tuple

from .git import GitError, diff as git_diff, log as git_log


_CITATION = re.compile(r"\(([0-9a-f]{7,40})\)")
_CODE = re.compile(r"`([^`]+)`")
_PATH = re.compile(r"\b(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\b")


def sentences(text: str) -> List[str]:
    lines = [line.strip().lstrip("-* ") for line in text.splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    prose = " ".join(lines)
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", prose) if part.strip()]


def _diff_for_hash(repo: str, short_hash: str) -> str:
    records = git_log(repo)
    matches = [record for record in records if record.commit.startswith(short_hash)]
    if not matches:
        raise GitError("citation does not resolve: {}".format(short_hash))
    return git_diff(repo, matches[0])


def verify_brief(repo: str, text: str) -> Tuple[bool, Tuple[str, ...]]:
    errors = []
    for index, sentence in enumerate(sentences(text), 1):
        citations = _CITATION.findall(sentence)
        if not citations:
            errors.append("sentence {} has no commit citation".format(index))
            continue
        for citation in citations:
            try:
                patch = _diff_for_hash(repo, citation)
            except GitError as error:
                errors.append("sentence {}: {}".format(index, error))
                continue
            references = list(_CODE.findall(sentence)) + _PATH.findall(sentence)
            for reference in references:
                reference = reference.strip()
                if reference in (citation, "catchup", "git") or len(reference) < 2:
                    continue
                if reference not in patch:
                    errors.append("sentence {} mentions `{}` absent from diff {}".format(
                        index, reference, citation))
    return not errors, tuple(errors)
