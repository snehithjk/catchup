"""Human-inspectable state under .catchup."""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Mapping

from .models import ExposureEntry, Feedback


def save_knowledge_map(repo: str, entries: Mapping[str, ExposureEntry]) -> str:
    directory = os.path.join(repo, ".catchup")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "knowledge-map.json")
    payload = {key: entries[key].to_dict() for key in sorted(entries)}
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def load_feedback(repo: str) -> Dict[str, Feedback]:
    path = os.path.join(repo, ".catchup", "feedback.jsonl")
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


def append_feedback(repo: str, item_id: str, label: str, path_prefix: str = "") -> str:
    if label not in ("knew", "new", "irrelevant"):
        raise ValueError("label must be knew, new, or irrelevant")
    directory = os.path.join(repo, ".catchup")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "feedback.jsonl")
    payload = {"item_id": item_id, "label": label,
               "created_at": datetime.now(timezone.utc).isoformat(),
               "path_prefix": path_prefix}
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return path

