"""Run the pinned public-repository qualitative backtest."""

import argparse
import json
import os
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from catchup.git import run_git, log
from catchup.pipeline import run_pipeline
from catchup.verify import verify_brief


def _timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _scenario(repo_root, scenario):
    repo = os.path.join(repo_root, scenario["directory"])
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise RuntimeError("missing fixture checkout: {}".format(repo))
    actual_head = run_git(repo, ["rev-parse", "HEAD"]).strip()
    if actual_head != scenario["pinned_head"]:
        raise RuntimeError("{} is at {}, expected {}".format(
            scenario["name"], actual_head, scenario["pinned_head"]))
    cutoff = _timestamp(scenario["cutoff"])
    window_end = _timestamp(scenario["window_end"])
    prior_count = len(log(repo, before=cutoff.isoformat()))
    window_count = len(log(repo, since=cutoff.isoformat(),
                           before=window_end.isoformat(), first_parent=True))
    started = time.monotonic()
    top_n = max(5, len(scenario["expected_commits"]))
    result, brief = run_pipeline(
        repo, [scenario["identity"]], cutoff, window_end,
        top_n=top_n, persist=False,
    )
    elapsed = time.monotonic() - started
    grounded, errors = verify_brief(repo, brief)
    selected = [item.change.item_id for item in result.ranked]
    anchors = set(scenario["expected_commits"])
    matched = sorted(anchors.intersection(selected))
    return {
        "name": scenario["name"],
        "head": actual_head,
        "prior_commits": prior_count,
        "window_commits": window_count,
        "top_n": top_n,
        "selected": selected,
        "other_count": result.other_count,
        "documented_anchor_matches": matched,
        "documented_anchor_recall": round(len(matched) / len(anchors), 3) if anchors else 1.0,
        "grounded": grounded,
        "grounding_errors": list(errors),
        "runtime_seconds": round(elapsed, 2),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=os.path.join(ROOT, "fixtures", "real"))
    args = parser.parse_args(argv)
    manifest_path = os.path.join(ROOT, "fixtures", "real", "manifest.json")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    results = [_scenario(args.repo_root, scenario) for scenario in manifest["scenarios"]]
    print(json.dumps({"results": results}, indent=2, sort_keys=True))
    return 0 if all(row["grounded"] for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
