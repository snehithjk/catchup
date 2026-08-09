"""Command-line entry point."""

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from .git import GitError, discover_email, repo_root
from .pipeline import parse_window_start, run_pipeline
from .storage import append_feedback, load_last_run


def _emails(values: Sequence[str]) -> List[str]:
    result = []
    for value in values:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return result


def _run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="catchup",
        description="Surface git changes that threaten one developer's knowledge.",
    )
    parser.add_argument("--repo", default=".", help="local git repository (default: .)")
    parser.add_argument("--me", action="append",
                        help="your git email; repeat or comma-separate identities (default: local Git identity)")
    parser.add_argument("--since", default="30d",
                        help="window such as 30d, 2w, last, or an ISO timestamp")
    parser.add_argument("--top", type=int, default=5, help="maximum brief items (default: 5)")
    parser.add_argument("--half-life", type=float, default=90.0,
                        help="exposure decay half-life in days (default: 90)")
    parser.add_argument("--authored-weight", type=float, default=1.0,
                        help="authored exposure weight (default: 1.0)")
    parser.add_argument("--reviewed-weight", type=float, default=0.6,
                        help="reviewed exposure weight (default: 0.6)")
    parser.add_argument("--as-of", help=argparse.SUPPRESS)
    parser.add_argument("--llm", action="store_true",
                        help="use the configured OpenAI-compatible API instead of the offline brief")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def _mark_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="catchup mark", description="Record brief feedback.")
    parser.add_argument("item_id")
    parser.add_argument("label", choices=("knew", "new", "irrelevant"))
    parser.add_argument("--repo", default=".")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    values = list(argv if argv is not None else sys.argv[1:])
    try:
        if values and values[0] == "mark":
            args = _mark_parser().parse_args(values[1:])
            root = repo_root(args.repo)
            path = append_feedback(root, args.item_id, args.label)
            print("recorded {} for {} in {}".format(args.label, args.item_id, path))
            return 0
        args = _run_parser().parse_args(values)
        root = repo_root(args.repo)
        if args.as_of:
            as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
            if as_of.tzinfo is None:
                as_of = as_of.replace(tzinfo=timezone.utc)
        else:
            as_of = datetime.now(timezone.utc)
        last_run = load_last_run(root) if args.since.strip().lower() == "last" else None
        start = parse_window_start(args.since, as_of, last_run)
        emails = _emails(args.me) if args.me else [discover_email(root)]
        if not emails or not emails[0]:
            raise ValueError("could not infer a Git email; pass --me explicitly")
        result, brief = run_pipeline(root, emails, start, as_of,
                                     top_n=args.top, half_life_days=args.half_life,
                                     authored_weight=args.authored_weight,
                                     reviewed_weight=args.reviewed_weight,
                                     use_llm=args.llm)
        if args.format == "json":
            print(json.dumps({
                "knowledge_map": {key: value.to_dict() for key, value in result.knowledge_map.items()},
                "ranked": [item.to_dict() for item in result.ranked],
                "other_count": result.other_count,
                "brief": brief,
            }, indent=2, sort_keys=True))
        else:
            print(brief, end="")
        return 0
    except (GitError, OSError, RuntimeError, ValueError) as error:
        print("catchup: {}".format(error), file=sys.stderr)
        return 2
