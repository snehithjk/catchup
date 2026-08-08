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
        post_paths = set(truth["post_window_paths"])
        precision = (1.0 if result.ranked and selected_paths & post_paths else 0.0)
        recall = 1.0 if expected & selected_paths else 0.0
        grounded, errors = verify_brief(directory, brief)
        noise = len(result.ranked) / 10.0
        print("synthetic precision={:.2f} recall={:.2f} grounding={:.2f} noise={:.2f} items={}".format(
            precision, recall, 1.0 if grounded else 0.0, noise, len(result.ranked)))
        if not grounded:
            print("grounding errors: {}".format("; ".join(errors)), file=sys.stderr)
        return 0 if precision == 1.0 and recall == 1.0 and grounded and noise <= 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
