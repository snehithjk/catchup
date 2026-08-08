"""A deliberately small import graph for Python and JS/TS files."""

import os
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Mapping, Sequence, Set


_PY_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))")
_JS_IMPORT = re.compile(r"(?:from\s+|import\s*\(|require\(\s*[\"'])([.@\w_/-]+)")


def _candidates(source: str, imported: str) -> List[str]:
    base = os.path.dirname(source)
    if imported.startswith("."):
        path = os.path.normpath(os.path.join(base, imported))
    else:
        path = imported.replace(".", "/")
    return [path, path + ".py", path + ".js", path + ".ts", path + "/__init__.py",
            path + "/index.js", path + "/index.ts"]


def build_import_graph(files: Sequence[str], contents: Mapping[str, str]) -> Dict[str, int]:
    known = set(files)
    incoming = defaultdict(set)
    for source in files:
        if not source.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
            continue
        text = contents.get(source, "")
        imports = []
        if source.endswith(".py"):
            imports = [a or b for a, b in (_PY_IMPORT.match(line).groups()
                      for line in text.splitlines() if _PY_IMPORT.match(line))]
        else:
            imports = [match.group(1) for match in _JS_IMPORT.finditer(text)]
        for imported in imports:
            for candidate in _candidates(source, imported):
                if candidate in known and candidate != source:
                    incoming[candidate].add(source)
                    break
    return {path: len(incoming.get(path, ())) for path in files}


def path_distance_fan_in(path: str) -> float:
    """Conservative fallback for languages with no parser in v1."""
    depth = path.count("/")
    return 1.0 + (1.0 / (1.0 + depth))

