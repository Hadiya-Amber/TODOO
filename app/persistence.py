"""Persistence helpers for TODOO.

This module provides a small, well-documented persistence surface used by the
application and tests. It reads the configured JSON store path from the
environment and performs atomic writes to avoid exposing partial JSON to
readers. A startup-time validation helper is provided to ensure the configured
path is writable and to surface a clear developer-facing error when it is not.

Environment variables supported (in order of precedence):
- TODOS_JSON_PATH: preferred name used by tests and newer deployments.
- TODOO_DATA_FILE: legacy name retained for backwards compatibility.

Public API:
- get_data_file_path() -> str
- load_store() -> list[dict]
- save_store(items: list[dict]) -> None
- validate_data_file_path() -> None  # raise RuntimeError on configuration problems
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
import errno
from typing import List


# Environment variables supported (prefer TODOS_JSON_PATH)
_ENV_PREFS = ("TODOS_JSON_PATH", "TODOO_DATA_FILE")
_DEFAULT_RELATIVE = Path("data") / "todoo.json"


def get_data_file_path() -> str:
    """Return the absolute path to the JSON persistence file.

    The function prefers TODOS_JSON_PATH, falls back to TODOO_DATA_FILE, and
    finally to a repository-local default (./data/todoo.json). The returned
    path is absolute and expanded; callers should not mutate the returned
    string in-place.
    """
    for name in _ENV_PREFS:
        val = os.environ.get(name)
        if val:
            return str(Path(val).expanduser().resolve())
    # default relative to current working directory
    return str(_DEFAULT_RELATIVE.resolve())


def load_store() -> List[dict]:
    """Load and return the list of todos from the configured JSON file.

    If the file does not exist, an empty list is returned. If the file exists
    but contains invalid JSON or an unexpected shape, a ValueError is raised.
    """
    path = Path(get_data_file_path())
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"persistence: invalid JSON in {path}: {exc}") from exc

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"persistence: unexpected JSON shape in {path}; expected list or dict")


def save_store(items: List[dict]) -> None:
    """Atomically write ``items`` (a list of dicts) to the configured JSON file.

    The implementation writes to a temporary file in the same directory and
    then performs an atomic replace using os.replace(). It also attempts to
    fsync the temporary file to reduce the chance of partial writes reaching
    disk on crash. Parent directories are created if missing.
    """
    path = Path(get_data_file_path())
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    # Use a NamedTemporaryFile in the same directory to ensure os.replace()
    # can be atomic across filesystems when possible.
    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=".todoo-", dir=str(parent))
        # Write JSON to the file descriptor
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(items, fh, ensure_ascii=False, indent=2)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                # Best-effort; continue even if fsync is unavailable
                pass
        # Atomic replace
        os.replace(tmp_path, str(path))
        tmp_path = None
    finally:
        # Clean up temp file if something went wrong before replace
        if tmp_path and Path(tmp_path).exists():
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass


def validate_data_file_path() -> None:
    """Validate the configured JSON path is writable.

    Behaviour:
    - If the file exists: check that it is writable by attempting an os.access
      check and by opening the file for appending. If not writable, raise
      RuntimeError with remediation guidance.
    - If the file does not exist: attempt to create an empty JSON file ("[]").
      If creation fails, raise RuntimeError naming the path and suggesting
      remediation (create the file, adjust permissions).

    The exception message intentionally names the offending path and offers
    actionable remediation steps for developers.
    """
    path = Path(get_data_file_path())
    # If the file exists, ensure writable
    if path.exists():
        if not os.access(str(path), os.W_OK):
            raise RuntimeError(
                f"persistence: configured JSON path is not writable: {path}. "
                "Ensure the file exists and adjust ownership or permissions (e.g. chown/chmod)."
            )
        # Try opening for append to detect subtle cases (readonly filesystem)
        try:
            with path.open("a", encoding="utf-8"):
                pass
        except OSError as exc:
            raise RuntimeError(
                f"persistence: cannot open configured JSON path for writing: {path}: {exc}. "
                "Try creating the file or adjusting permissions (chmod/chown)."
            ) from exc
        return

    # File doesn't exist; attempt to create parent directory then the file
    parent = path.parent
    try:
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"persistence: cannot create parent directory for configured JSON path {parent}: {exc}. "
            "Check directory permissions or set TODOS_JSON_PATH to a different location."
        ) from exc

    # Attempt to create an empty JSON array file atomically
    try:
        save_store([])
    except OSError as exc:
        raise RuntimeError(
            f"persistence: failed to create configured JSON file {path}: {exc}. "
            "Create the file manually or adjust permissions (mkdir/chown/chmod)."
        ) from exc


__all__ = [
    "get_data_file_path",
    "load_store",
    "save_store",
    "validate_data_file_path",
]
