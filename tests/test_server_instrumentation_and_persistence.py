import json
import importlib
import os
from pathlib import Path
from datetime import datetime

import pytest
from fastapi.testclient import TestClient


# These tests exercise the planned instrumentation and verification harness
# behaviour described in the task plan. They import the names the plan says
# will be added so the test suite serves as RED evidence until the
# implementation is provided.


def test_AC_1_1_create_records_latency(tmp_path, monkeypatch):
    """AC-1.1: POST /api/todos should cause the instrumentation to capture a 'create' latency record with an ISO-8601 timestamp."""
    store_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    # Import instrumentation helpers that the planned change will provide.
    from instrumentation.latency_placeholder import clear_captured_records, get_captured_records

    # Import the ASGI app after setting TODOS_JSON_PATH so validation sees the test file.
    importlib.invalidate_caches()
    app_main = importlib.import_module("app.main")
    app = getattr(app_main, "app")

    client = TestClient(app)

    clear_captured_records()

    resp = client.post("/api/todos", json={"label": "task A"})
    assert 200 <= resp.status_code < 300, f"POST failed: {resp.status_code} {resp.text}"

    records = get_captured_records()
    assert isinstance(records, list), "get_captured_records() must return a list"

    # Find a create record and assert timestamp parses as ISO-8601.
    create_recs = [r for r in records if r.get("operation") == "create"]
    assert create_recs, f"no 'create' record found in captured records: {records!r}"

    ts = create_recs[0].get("timestamp")
    assert isinstance(ts, str), "record timestamp must be a string"
    # datetime.fromisoformat will raise if not valid ISO-8601; let that surface.
    datetime.fromisoformat(ts)


def test_AC_2_1_edit_and_toggle_records_have_operation_and_iso_timestamp(tmp_path, monkeypatch):
    """AC-2.1: PUT (edit) and PATCH (toggle) should emit latency records labelled 'edit' and 'toggle' with ISO-8601 timestamps."""
    store_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    from instrumentation.latency_placeholder import clear_captured_records, get_captured_records

    importlib.invalidate_caches()
    app_main = importlib.import_module("app.main")
    app = getattr(app_main, "app")

    client = TestClient(app)

    # Create a todo first
    resp = client.post("/api/todos", json={"label": "to-edit"})
    assert 200 <= resp.status_code < 300, f"POST failed: {resp.status_code} {resp.text}"
    todo = resp.json()
    todo_id = todo.get("id")
    assert todo_id is not None, "created todo must include an id"

    clear_captured_records()

    # Edit
    resp = client.put(f"/api/todos/{todo_id}", json={"label": "edited"})
    assert 200 <= resp.status_code < 300, f"PUT failed: {resp.status_code} {resp.text}"

    # Toggle
    resp = client.patch(f"/api/todos/{todo_id}/toggle")
    assert 200 <= resp.status_code < 300, f"PATCH(toggle) failed: {resp.status_code} {resp.text}"

    records = get_captured_records()
    ops = [r.get("operation") for r in records]

    assert "edit" in ops, f"no 'edit' operation captured: {records!r}"
    assert "toggle" in ops, f"no 'toggle' operation captured: {records!r}"

    # Verify timestamps parse
    for r in records:
        ts = r.get("timestamp")
        assert isinstance(ts, str), "timestamp must be a string"
        datetime.fromisoformat(ts)


def test_AC_3_1_verification_harness_creates_restarts_and_persists(tmp_path, monkeypatch):
    """AC-3.1: client_harness.run_verification shall perform create -> restart -> verify and return a report indicating persisted todos."""
    # The harness is expected to create its own temp dir; we provide a harmless start command.
    start_cmd = ["uvicorn", "app.main:app"]
    todos = [{"label": "a"}, {"label": "b"}]

    # Import the verification harness planned for client_harness.verification
    from client_harness.verification import run_verification

    report = run_verification(start_cmd, todos)
    assert isinstance(report, dict), "run_verification must return a dict report"

    # Required keys
    assert "success" in report and "persisted_path" in report and "created_count" in report and "timestamp" in report, (
        f"report missing required keys: {report!r}"
    )

    assert isinstance(report["success"], bool), "success must be a boolean"
    assert report["success"] is True, f"verification reported failure: {report!r}"

    persisted = Path(report["persisted_path"])
    assert persisted.exists(), f"persisted_path does not exist: {persisted}"

    data = json.loads(persisted.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and "todos" in data, "persisted JSON must contain top-level 'todos'"
    assert len(data["todos"]) == report["created_count"] == 2, (
        f"expected 2 persisted todos; got file={len(data['todos'])} report={report['created_count']}"
    )

    # Verify that persisted todos have the requested fields.
    for t in data["todos"]:
        assert all(k in t for k in ("id", "label", "done", "created_at")), f"persisted todo missing fields: {t!r}"
        # created_at must parse as ISO-8601
        datetime.fromisoformat(t["created_at"])


def test_AC_4_1_each_api_operation_emits_operation_label_and_iso_timestamp(tmp_path, monkeypatch):
    """AC-4.1: For POST/PUT/PATCH/DELETE each captured record contains an operation in the allowed set and an ISO-8601 timestamp."""
    store_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    from instrumentation.latency_placeholder import clear_captured_records, get_captured_records

    importlib.invalidate_caches()
    app_main = importlib.import_module("app.main")
    app = getattr(app_main, "app")
    client = TestClient(app)

    # create
    resp = client.post("/api/todos", json={"label": "one"})
    assert 200 <= resp.status_code < 300
    todo = resp.json()
    todo_id = todo.get("id")
    assert todo_id is not None

    clear_captured_records()

    # perform each operation once
    client.post("/api/todos", json={"label": "c"})
    client.put(f"/api/todos/{todo_id}", json={"label": "u"})
    client.patch(f"/api/todos/{todo_id}/toggle")
    client.delete(f"/api/todos/{todo_id}")

    records = get_captured_records()
    ops_seen = [r.get("operation") for r in records]
    allowed = {"create", "edit", "toggle", "delete"}

    # Assert each of the four operations produced at least one record
    for expected in allowed:
        assert expected in ops_seen, f"operation {expected} not captured; records: {records!r}"

    # All timestamps must be parseable ISO-8601
    for r in records:
        ts = r.get("timestamp")
        assert isinstance(ts, str)
        datetime.fromisoformat(ts)


def test_AC_5_1_persistence_failure_emits_diagnostic_and_latency_record(tmp_path, monkeypatch):
    """AC-5.1: When persistence.save_store fails the handler still records latency and a persistence_error diagnostic is emitted."""
    store_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    # Import persistence to monkeypatch save_store, and instrumentation to observe emissions
    importlib.invalidate_caches()
    persistence = importlib.import_module("app.persistence")
    from instrumentation.latency_placeholder import clear_captured_records, get_captured_records, get_captured_diagnostics

    # Replace save_store with a function that simulates a locked file condition
    def fail_save_store(payload):
        raise PermissionError("locked")

    monkeypatch.setattr(persistence, "save_store", fail_save_store)

    app_main = importlib.import_module("app.main")
    app = getattr(app_main, "app")
    client = TestClient(app)

    clear_captured_records()

    # Perform create which will attempt to persist and hit our simulated failure
    resp = client.post("/api/todos", json={"label": "locked test"})
    # The handler should still complete; accept any 2xx/4xx/5xx but we assert latency recorded below
    assert resp is not None

    records = get_captured_records()
    assert any(r.get("operation") == "create" for r in records), (
        f"latency 'create' record not found after persistence failure; records: {records!r}"
    )

    # Diagnostics API planned to be available for tests
    diagnostics = get_captured_diagnostics()
    assert isinstance(diagnostics, list), "get_captured_diagnostics must return a list"
    found = [d for d in diagnostics if d.get("error_type") == "persistence_error" and "locked" in json.dumps(d)]
    assert found, f"no persistence_error diagnostic containing 'locked' found in diagnostics: {diagnostics!r}"


def test_AC_6_1_malformed_json_load_emits_parse_diagnostic(tmp_path, monkeypatch):
    """AC-6.1: Loading a malformed JSON file causes a parse diagnostic to be emitted (with error_type 'parse_error')."""
    bad = tmp_path / "todos.json"
    bad.write_text("{ malformed json", encoding="utf-8")
    monkeypatch.setenv("TODOS_JSON_PATH", str(bad))

    importlib.invalidate_caches()
    persistence = importlib.import_module("app.persistence")
    from instrumentation.latency_placeholder import get_captured_diagnostics

    # Calling load_store may raise or may emit a diagnostic depending on the planned behaviour.
    try:
        _ = persistence.load_store()
    except Exception:
        # ignore the exception; the important observable for this test is the diagnostic emission
        pass

    diagnostics = get_captured_diagnostics()
    assert isinstance(diagnostics, list), "get_captured_diagnostics must return a list"
    parse_diags = [d for d in diagnostics if d.get("error_type") == "parse_error"]
    assert parse_diags, f"no parse_error diagnostic found after loading malformed JSON: {diagnostics!r}"
    # Error message should contain some JSON decoding detail
    assert any("JSONDecodeError" in json.dumps(d) or "Expecting" in json.dumps(d) for d in parse_diags), (
        f"parse_error diagnostics do not include JSONDecodeError details: {parse_diags!r}"
    )


def test_AC_7_1_verification_report_includes_required_keys_and_iso_timestamp(tmp_path, monkeypatch):
    """AC-7.1: The verification harness must return a JSON-report containing 'success', 'persisted_path', 'timestamp' (ISO-8601), and on success 'created_count' equal to number of created todos."""
    start_cmd = ["uvicorn", "app.main:app"]
    todos = [{"label": "x"}]

    from client_harness.verification import run_verification

    report = run_verification(start_cmd, todos)
    assert isinstance(report, dict)
    assert "success" in report and "persisted_path" in report and "timestamp" in report
    assert isinstance(report["success"], bool)
    # timestamp must be ISO-8601
    datetime.fromisoformat(report["timestamp"])

    if report["success"]:
        assert "created_count" in report and report["created_count"] == len(todos)
        persisted = Path(report["persisted_path"])
        assert persisted.exists()
        data = json.loads(persisted.read_text(encoding="utf-8"))
        assert len(data.get("todos", [])) == report["created_count"]
