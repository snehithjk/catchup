"""Generate a tiny history with a known personalized ground truth."""

import os
import subprocess
from typing import Dict


ALICE = "alice@example.com"
BOB = "bob@example.com"
CUTOFF = "2025-02-01T00:00:00+00:00"
WINDOW_END = "2025-03-01T00:00:00+00:00"


def _run(repo: str, args, env=None):
    command = ["git", "-C", repo] + list(args)
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                   text=True, env=env)


def _write(repo: str, relative: str, content: str) -> None:
    path = os.path.join(repo, relative)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _commit(repo: str, message: str, date: str, email: str) -> None:
    env = os.environ.copy()
    env.update({"GIT_AUTHOR_NAME": email.split("@")[0], "GIT_AUTHOR_EMAIL": email,
                "GIT_COMMITTER_NAME": email.split("@")[0], "GIT_COMMITTER_EMAIL": email,
                "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
    _run(repo, ["add", "."], env=env)
    _run(repo, ["commit", "-q", "-m", message], env=env)


def create_repo(path: str) -> Dict[str, object]:
    os.makedirs(path, exist_ok=True)
    _run(path, ["init", "-q", "-b", "main"])
    _run(path, ["config", "user.name", "fixture"])
    _run(path, ["config", "user.email", "fixture@example.com"])

    _write(path, "app/service.py", """def parse_order(order_id):
    return {\"id\": order_id, \"status\": \"ready\"}
""")
    _write(path, "app/api.py", """from app.service import parse_order


def get_order(order_id):
    return parse_order(order_id)
""")
    _write(path, "README.md", "# fixture\n")
    _commit(path, "feat: add order service", "2025-01-01T10:00:00+00:00", ALICE)

    _write(path, "app/test_service.py", """from app.service import parse_order


def test_order():
    assert parse_order(1)[\"status\"] == \"ready\"
""")
    _commit(path, "test: cover order parsing", "2025-01-10T10:00:00+00:00", ALICE)

    _write(path, "app/service.py", """def parse_order(order_id, currency):
    return {\"id\": order_id, \"currency\": currency, \"status\": \"ready\"}
""")
    _commit(path, "refactor: require currency for order parsing", "2025-02-05T10:00:00+00:00", BOB)

    _write(path, "docs/operations.md", "# Operations\n\nRestart the worker after deploy.\n")
    _commit(path, "docs: add operations note", "2025-02-10T10:00:00+00:00", BOB)

    _write(path, "app/test_service.py", """from app.service import parse_order


def test_order_contract():
    assert parse_order(1, \"USD\")[\"status\"] == \"ready\"
""")
    _commit(path, "test: rename order contract fixture", "2025-02-20T10:00:00+00:00", BOB)

    _write(path, "app/service.py", """def parse_order(order_id, currency):
    if not currency:
        raise ValueError(\"currency is required\")
    return {\"id\": order_id, \"currency\": currency, \"status\": \"ready\"}
""")
    _commit(path, "fix: reject orders without currency", "2025-03-10T10:00:00+00:00", ALICE)

    return {
        "user": ALICE,
        "cutoff": CUTOFF,
        "window_end": WINDOW_END,
        "expected_paths": ["app/service.py"],
        "post_window_paths": ["app/service.py"],
    }
