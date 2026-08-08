"""Human-inspectable state under .catchup."""

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, Mapping, Sequence

from .models import ExposureEntry, Feedback, RankedChange


def _state_directory(repo: str) -> str:
    directory = os.path.join(repo, ".catchup")
    if os.path.lexists(directory) and os.path.islink(directory):
        raise RuntimeError("refusing symlinked .catchup directory")
    os.makedirs(directory, mode=0o700, exist_ok=True)
    if not os.path.isdir(directory):
        raise RuntimeError(".catchup is not a directory")
    return directory


def _state_path(repo: str, name: str) -> str:
    directory = _state_directory(repo)
    path = os.path.join(directory, name)
    if os.path.lexists(path) and os.path.islink(path):
        raise RuntimeError("refusing symlinked .catchup/{}".format(name))
    return path


def _atomic_json(path: str, payload: object) -> None:
    directory = os.path.dirname(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         prefix=".catchup-", delete=False) as handle:
            temporary = handle.name
            os.chmod(temporary, 0o600)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def save_knowledge_map(repo: str, entries: Mapping[str, ExposureEntry]) -> str:
    path = _state_path(repo, "knowledge-map.json")
    payload = {key: entries[key].to_dict() for key in sorted(entries)}
    _atomic_json(path, payload)
    return path


def load_feedback(repo: str) -> Dict[str, Feedback]:
    path = os.path.join(repo, ".catchup", "feedback.jsonl")
    if os.path.lexists(path) and os.path.islink(path):
        raise RuntimeError("refusing symlinked .catchup/feedback.jsonl")
    if not os.path.exists(path):
        return {}
    result = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
                if value.get("label") in ("knew", "new", "irrelevant"):
                    result[value["item_id"]] = Feedback(
                        item_id=value["item_id"], label=value["label"],
                        created_at=value.get("created_at", ""),
                        path_prefix=value.get("path_prefix", ""),
                    )
            except (ValueError, KeyError, TypeError):
                continue
    return result


def save_last_brief(repo: str, items: Sequence[RankedChange]) -> str:
    """Persist the item-to-path map that makes feedback useful beyond one commit."""
    path = _state_path(repo, "last-brief.json")
    payload = {
        item.change.item_id: {"paths": list(item.change.paths)}
        for item in items
    }
    _atomic_json(path, payload)
    return path


def load_last_brief(repo: str) -> Dict[str, Sequence[str]]:
    path = os.path.join(repo, ".catchup", "last-brief.json")
    if os.path.lexists(path) and os.path.islink(path):
        return {}
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
        return {
            item_id: tuple(item.get("paths", ()))
            for item_id, item in value.items()
            if isinstance(item, dict)
        }
    except (OSError, ValueError, AttributeError):
        return {}


def append_feedback(repo: str, item_id: str, label: str, path_prefix: str = "") -> str:
    if label not in ("knew", "new", "irrelevant"):
        raise ValueError("label must be knew, new, or irrelevant")
    path = _state_path(repo, "feedback.jsonl")
    payload = {"item_id": item_id, "label": label,
               "created_at": datetime.now(timezone.utc).isoformat(),
               "path_prefix": path_prefix}
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    return path
