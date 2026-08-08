"""Offline synthetic backtest; prints one scoreboard line."""

import os
import sys
import tempfile
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from catchup.git import changed_paths, log
from catchup.pipeline import run_pipeline
from catchup.verify import verify_brief
from fixtures.synthetic.generate import create_repo


def _dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    with tempfile.TemporaryDirectory(prefix="catchup-eval-") as directory:
        truth = create_repo(directory)
        result, brief = run_pipeline(
            directory, [truth["user"]], _dt(truth["cutoff"]), _dt(truth["window_end"]),
            top_n=10, persist=False,
        )
        selected_paths = {path for item in result.ranked for path in item.change.paths}
        expected = set(truth["expected_paths"])
        post_records = log(directory, since=truth["window_end"])
        post_paths = {path for record in post_records
                      for _, path in changed_paths(directory, record)}
        relevant_items = sum(1 for item in result.ranked
                             if set(item.change.paths) & post_paths)
        precision = relevant_items / len(result.ranked) if result.ranked else 0.0
        recall = len(expected & selected_paths) / len(expected) if expected else 1.0
        grounded, errors = verify_brief(directory, brief)
        noise = len(result.ranked) / 10.0
        print("synthetic precision={:.2f} recall={:.2f} grounding={:.2f} noise={:.2f} items={}".format(
            precision, recall, 1.0 if grounded else 0.0, noise, len(result.ranked)))
        if not grounded:
            print("grounding errors: {}".format("; ".join(errors)), file=sys.stderr)
        # A non-perfect proxy score is useful signal, not a harness failure.
        # Grounding remains a hard gate; recall/noise must still be non-empty and bounded.
        return 0 if grounded and recall > 0.0 and noise <= 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
