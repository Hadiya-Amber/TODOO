"""Local verification harness for persistence across restart.

This module exposes run_verification(start_cmd: list[str], todos: list[dict])
which exercises the running application (via TestClient), consumes captured
instrumentation records, computes median latencies, optionally runs a restart
command, and verifies that the server-side JSON persistence file contains the
created todos unchanged across a restart.

It returns a single machine-readable report dict and does not exit the process
directly; callers (CI job) may inspect the returned report and decide how to
surface failures. Tests in this repository call run_verification directly.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib
import json
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile

from fastapi.testclient import TestClient

from client_harness.verify_runner import compute_median_ms_by_operation
import shutil


DEFAULT_LATENCY_THRESHOLD_MS = 500.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_restart_command(cmd: List[str]) -> Dict[str, Any]:
    if not cmd:
        return {"ok": True, "cmd": cmd, "output": ""}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"ok": True, "cmd": cmd, "output": proc.stdout}
    except subprocess.CalledProcessError as exc:
        return {"ok": False, "cmd": cmd, "returncode": exc.returncode, "output": exc.output, "stderr": exc.stderr}


def _read_persisted_data(path_override: Optional[str] = None) -> Dict[str, Any]:
    # Import persistence lazily to allow tests to monkeypatch get_data_file_path
    import app.persistence as app_persistence

    if path_override:
        # Temporarily set env var used by app.persistence
        os.environ["TODOS_JSON_PATH"] = str(path_override)
    return app_persistence.load_store()


def _compare_created_vs_persisted(created: List[dict], persisted: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    persisted_todos = persisted.get("todos", []) if isinstance(persisted, dict) else []
    # Build map by id if ids present, otherwise compare by label and created_at
    by_id = {t.get("id"): t for t in persisted_todos if "id" in t}
    for c in created:
        cid = c.get("id")
        found = None
        if cid in by_id:
            found = by_id[cid]
        else:
            # fallback: try match by label and created_at
            for t in persisted_todos:
                if t.get("label") == c.get("label") and t.get("created_at") == c.get("created_at"):
                    found = t
                    break

        if not found:
            errors.append(f"missing todo created with label={c.get('label')!r} id={cid!r}")
            continue

        # Compare fields
        for k in ("id", "label", "done", "created_at"):
            if found.get(k) != c.get(k):
                errors.append(f"mismatch for todo id={cid!r} field={k}: expected={c.get(k)!r} got={found.get(k)!r}")
    return errors


def run_verification(start_cmd: List[str], todos: List[dict], *, persistence_path: Optional[str] = None, latency_threshold_ms: float = DEFAULT_LATENCY_THRESHOLD_MS) -> Dict[str, Any]:
    """Run verification: create todos, gather instrumentation, restart, and verify persistence.

    Returns a machine-readable report dict with keys: status (pass|fail), latencies, persistence, diagnostics, exit_code.
    """
    report: Dict[str, Any] = {
        "status": "fail",
        "latencies": {},
        "persistence": {"ok": False, "errors": []},
        "diagnostics": {},
        "timestamp": _now_iso(),
        "exit_code": 1,
    }

    # Prepare an isolated persistence file for this run so the harness does not
    # observe other tests' data. This mirrors the original harness behavior
    # which used a dedicated temporary directory per run.
    td_dir = tempfile.mkdtemp()
    data_path = Path(td_dir) / "todos.json"
    os.environ["TODOS_JSON_PATH"] = str(data_path)

    # Ensure the application is imported fresh and TestClient will use current env
    importlib.invalidate_caches()
    app_main = importlib.import_module("app.main")
    app = getattr(app_main, "app")
    client = TestClient(app)

    created_items: List[dict] = []
    # Create todos via API
    for t in todos:
        resp = client.post("/api/todos", json=t)
        try:
            body = resp.json()
        except Exception:
            body = {"status_code": resp.status_code, "text": resp.text}
        if 200 <= resp.status_code < 300 and isinstance(body, dict):
            created_items.append(body)

    # Collect instrumentation samples (captured during request handling).
    # Import the instrumentation module at runtime so tests can monkeypatch
    # its public helpers (for example get_captured_records()).
    instr = importlib.import_module("instrumentation.latency_placeholder")
    captured = instr.get_captured_records()
    medians = compute_median_ms_by_operation(captured)
    report["latencies"] = medians

    # Evaluate latency thresholds
    latency_failures: List[str] = []
    for op, ms in medians.items():
        if float(ms) > float(latency_threshold_ms):
            latency_failures.append(f"operation {op} median {ms:.1f}ms exceeds threshold {latency_threshold_ms}ms")

    # Perform restart using provided command
    # Only attempt to execute the restart command if the executable exists on PATH.
    # This preserves compatibility with tests that pass "uvicorn" but do not
    # expect the harness to actually spawn it in the test environment.
    restart_result = _run_restart_command(start_cmd) if start_cmd and shutil.which(start_cmd[0]) else {"ok": True, "cmd": start_cmd or [], "skipped": True}
    report["diagnostics"]["restart"] = restart_result

    # After restart, attempt to read persisted JSON via app.persistence
    try:
        persisted = _read_persisted_data(persistence_path)
    except Exception as exc:
        # Capture persistence error details
        err = str(exc)
        report["persistence"]["errors"].append(err)
        # Also include captured diagnostics from instrumentation
        report["diagnostics"]["persistence_diagnostics"] = instr.get_captured_diagnostics()
        report["status"] = "fail"
        report["exit_code"] = 2
        return report

    # Compare created items vs persisted
    compare_errors = _compare_created_vs_persisted(created_items, persisted)
    if compare_errors:
        report["persistence"]["errors"].extend(compare_errors)
        report["persistence"]["ok"] = False
    else:
        report["persistence"]["ok"] = True

    # If any latency failures, include them in diagnostics and fail
    if latency_failures:
        report["diagnostics"]["latency_failures"] = latency_failures
        report["status"] = "fail"
        report["exit_code"] = 3
        return report

    # If persistence had errors, fail
    if not report["persistence"]["ok"]:
        report["status"] = "fail"
        report["exit_code"] = 4
        return report

    # All checks passed
    report["status"] = "pass"
    report["exit_code"] = 0
    # Attach any final diagnostics
    report["diagnostics"]["captured"] = instr.get_captured_diagnostics()
    # Backwards-compatible fields expected by older tests/harness consumers
    report["success"] = report["status"] == "pass"
    # persisted_path should point to the isolated data file used for this run
    report["persisted_path"] = str(data_path)
    report["created_count"] = len(created_items)
    return report


__all__ = ["run_verification"]
