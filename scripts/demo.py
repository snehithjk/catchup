"""Print a complete offline personalized brief from the synthetic history."""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from catchup.cli import main
from fixtures.synthetic.generate import CUTOFF, WINDOW_END, create_repo


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="catchup-demo-") as directory:
        create_repo(directory)
        raise SystemExit(main([
            "--repo", directory, "--me", "alice@example.com",
            "--since", CUTOFF, "--as-of", WINDOW_END,
        ]))
