"""Persistence for TODOO: a small, well-documented JSON file store.

This module provides a minimal, deterministic server-side JSON persistence
implementation used by the application. It is intentionally small and focused on
being easy to reason about in tests and in local development. The behaviour is
sufficient for the project's acceptance tests and is written to be extended for
production (locking, fsync policies, migration hooks) without changing the
public surface.

Public API
- get_data_file_path() -> str
- load_store() -> Any
- save_store(payload: Any) -> None
- validate_data_file(cfg_path: Path) -> None

The runtime JSON file path is resolved from the TODOS_JSON_PATH environment
variable. If not set, a reasonable default inside the repository is used
(./data/todoo.json). Callers should not rely on the default for production
deployments.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any


_ENV_VAR = "TODOS_JSON_PATH"
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


def load_store() -> Any:
    """Load and return the JSON content from the configured store path.

    Returns the parsed JSON value as-is (commonly a dict with a top-level
    "todos" key). If the file does not exist, return a sensible default of
    {"todos": []} so callers can assume a dict-shaped payload.

    Raises
    ------
    ValueError
        If the file contains invalid JSON.
    """
    path = Path(get_data_file_path())
    if not path.exists():
        # Absence of the file is interpreted as an empty store with a
        # dict-shaped payload used by the application routes.
        return {"todos": []}

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"persistence: invalid JSON in {path}: {exc}") from exc

    return data


def save_store(payload: Any) -> None:
    """Persist the provided JSON-serializable payload to the configured path.

    Writes are performed atomically by writing to a temporary file in the same
    directory and then atomically replacing the destination. This reduces the
    window where readers might see a partially-written file.
    """
    path = Path(get_data_file_path())
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    # Serialize to a temporary file in the same directory then replace.
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            # Not all platforms support fsync on regular files (Windows in some
            # environments). Continue without failing; atomic replace still
            # provides a significant safety improvement.
            pass

    # Atomic replace
    os.replace(str(temp), str(path))


def validate_data_file(cfg_path: Path) -> None:
    """Validate that the configured data file path is usable by the process.

    - If the parent directory does not exist: raise RuntimeError (developer
      must create the directory or update configuration).
    - If the file exists but is not writable by the current process: raise
      RuntimeError describing the problem and remediation.
    - If the file does not exist but the parent directory exists, create an
      empty JSON store file with a sensible default payload.

    The message of the raised RuntimeError includes the configured path and
    remediation advice so failures at process start are actionable.
    """
    parent = cfg_path.parent
    if not parent.exists():
        raise RuntimeError(
            f"persistence: parent directory for JSON store does not exist: {cfg_path}\n"
            "Remediation: create the parent directory or change TODOS_JSON_PATH to a writable location."
        )

    if cfg_path.exists():
        # File exists — ensure we can open it for appending (writability)
        if not os.access(str(cfg_path), os.W_OK):
            raise RuntimeError(
                f"persistence: configured JSON store is not writable: {cfg_path}\n"
                "Remediation: adjust file permissions or ownership so the process can write to the file."
            )
        # Otherwise writable — nothing to do
        return

    # File does not exist but parent exists — create an initial empty store.
    try:
        save_store({"todos": []})
    except OSError as exc:
        raise RuntimeError(
            f"persistence: unable to create initial JSON store at {cfg_path}: {exc}\n"
            "Remediation: ensure the parent directory is writable by the process user."
        ) from exc


__all__ = ["get_data_file_path", "load_store", "save_store", "validate_data_file"]
