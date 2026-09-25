"""Persistence scaffolding for TODOO.

This module documents and provides a minimal, non-invasive scaffold for the
server-side JSON file store. It intentionally does not implement application
storage semantics; instead it exposes a small, well-documented surface that
future work can extend.

Design notes:
- The runtime JSON file path is resolved from the TODOO_DATA_FILE environment
  variable. If not set, a reasonable default inside the repository is used
  (./data/todoo.json). Callers should not rely on the default for production
  deployments.
- File access is intentionally conservative: helper functions return empty
  lists or sensible defaults rather than raising when the file is absent.
- This module is structured so future changes can add locking, atomic
  replace semantics, fsync guarantees, or migrate to a different backend with
  minimal caller impact.

Public helpers:
- get_data_file_path() -> str
- load_store() -> list[dict]
- save_store(items: list[dict]) -> None

Type hints are provided for clarity.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any, List


_ENV_VAR = "TODOO_DATA_FILE"
_DEFAULT_RELATIVE = Path("data") / "todoo.json"


def get_data_file_path() -> str:
    """Resolve the JSON store path from the environment or use a safe default.

    The returned path is absolute. Callers should ensure the process has
    appropriate permissions to read and write this location.
    """
    env = os.environ.get(_ENV_VAR)
    if env:
        return str(Path(env).expanduser().resolve())
    # default relative to repository root (current working directory)
    return str(_DEFAULT_RELATIVE.resolve())


def load_store() -> List[dict]:
    """Load the JSON store and return a list of items.

    If the file does not exist, return an empty list. If the file contains
    invalid JSON, raise a ValueError with context for the caller.
    """
    path = Path(get_data_file_path())
    if not path.exists():
        # Absence of the file is interpreted as an empty store
        return []

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"persistence: invalid JSON in {path}: {exc}") from exc

    # Expecting a JSON array at top-level; coerce where reasonable.
    if isinstance(data, list):
        return data
    # If a dict is stored, wrap it for callers that expect a list.
    if isinstance(data, dict):
        return [data]
    # Unknown shape — raise so callers notice and handle migration.
    raise ValueError(f"persistence: unexpected JSON shape in {path}; expected list or dict")


def save_store(items: List[dict]) -> None:
    """Persist the provided list of dict items to the JSON store path.

    This is a simple implementation intended only as a scaffold. It writes
    the JSON file with UTF-8 encoding and 2-space indentation. Future work
    should replace this with atomic write + fsync semantics for durability.
    """
    path = Path(get_data_file_path())
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    # Write the file. For now this is not atomic; callers relying on this
    # behavior should be aware and convert to an atomic replace pattern.
    with path.open("w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


def _example_usage() -> None:  # pragma: no cover - documentation helper
    """Small internal example demonstrating how callers will use this module.

    Not executed in tests; kept for developer reference.
    """
    items = load_store()
    items.append({"id": 1, "title": "example"})
    save_store(items)


__all__ = ["get_data_file_path", "load_store", "save_store"]
