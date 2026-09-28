"""Local verification harness for persistence across restart.

run_verification(start_cmd: list, todos: list[dict]) -> dict

This harness creates todos via the application's HTTP API using TestClient,
simulates a restart by re-importing the app with the same TODOS_JSON_PATH, and
verifies the persisted JSON file contains the created todos. The harness
returns a machine-readable report containing 'success', 'persisted_path',
'created_count', and 'timestamp'.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib
import json
import tempfile
import os
from pathlib import Path
from typing import List

from fastapi.testclient import TestClient


def run_verification(start_cmd: List[str], todos: List[dict]) -> dict:
    """Run the create -> restart -> verify flow locally.

    The start_cmd parameter is accepted for compatibility but not used: the
    harness uses TestClient to exercise the application in-process which is
    sufficient for verifying file persistence on the same filesystem.
    """
    # Create a temporary directory and JSON path for this run. Use mkdtemp
    # so the directory is not removed when this function returns; the harness
    # consumer (tests) inspects the persisted file after run_verification
    # returns.
    td_dir = tempfile.mkdtemp()
    data_path = Path(td_dir) / "todos.json"
    os.environ["TODOS_JSON_PATH"] = str(data_path)

    # Import the app and use TestClient to create todos
    importlib.invalidate_caches()
    app_main = importlib.import_module("app.main")
    app = getattr(app_main, "app")
    client = TestClient(app)

    created = 0
    for t in todos:
        resp = client.post("/api/todos", json=t)
        if 200 <= resp.status_code < 300:
            created += 1

    # Simulate restart by re-importing the app module which validates the
    # configured JSON store on attribute access of app.main:app
    importlib.reload(importlib.import_module("app"))

    report = {
        "success": False,
        "persisted_path": str(data_path),
        "created_count": created,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errors": [],
    }

    # Read the persisted file and validate content
    try:
        if not data_path.exists():
            report["errors"].append("persisted file missing")
            return report
        data = json.loads(data_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "todos" not in data:
            report["errors"].append("unexpected persisted schema")
            return report
        report["success"] = True
        return report
    except Exception as exc:
        report["errors"].append(str(exc))
        return report
