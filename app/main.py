"""ASGI entrypoint for TODOO.

Expose the FastAPI application as the module-level `app` variable so a
server can be started with: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

This module intentionally keeps initialization minimal and relies on
app.__init__ to validate the configured JSON persistence path at import
time.
"""
from __future__ import annotations

from pathlib import Path
import importlib
from typing import Any

from . import persistence


def __getattr__(name: str) -> Any:  # module-level accessor (PEP 562)
    """Lazily expose the FastAPI `app` after validating the current config.

    Using __getattr__ means attribute access (including 'from app.main import
    app') performs a fresh validation of the configured JSON store path based
    on the current TODOS_JSON_PATH environment variable. This makes tests that
    set the env var and then import this symbol behave deterministically even
    when the module has been imported earlier by other tests.
    """
    if name != "app":
        raise AttributeError(name)

    cfg_path = Path(persistence.get_data_file_path())
    # This will raise RuntimeError with an actionable message if the path is
    # invalid (missing parent dir, not writable, etc.).
    persistence.validate_data_file(cfg_path)

    # Import the package-level app object from app.__init__ and return it.
    pkg = importlib.import_module("app")
    app_obj = getattr(pkg, "app")

    # Include the API router if it exists so uvicorn-served app exposes the
    # /api/todos endpoints. Import locally to avoid import-time cycles.
    try:
        from app.api_todos import router as todos_router  # type: ignore
    except Exception:
        todos_router = None

    if todos_router is not None:
        # Avoid double inclusion if multiple imports occur
        if todos_router not in getattr(app_obj, "user_mounts", []):
            app_obj.include_router(todos_router)
            # track inclusion to keep idempotent
            app_obj.user_mounts = getattr(app_obj, "user_mounts", []) + [todos_router]

    return app_obj


__all__ = ["app"]
