import json
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


# AC-2.1: create a todo and verify it is returned by GET and persisted to the JSON file
def test_AC_2_1_create_persists(monkeypatch, tmp_path):
    store_path = tmp_path / "store.json"
    # ensure parent exists (tmp_path always exists)
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    # Import the ASGI app after setting TODOS_JSON_PATH so startup validation
    # observes the test-provided path.
    from app.main import app

    client = TestClient(app)

    resp = client.post("/api/todos", json={"label": "buy milk"})
    assert 200 <= resp.status_code < 300, f"expected 2xx, got {resp.status_code}"
    created = resp.json()
    assert created.get("label") == "buy milk"

    resp_get = client.get("/api/todos")
    assert 200 <= resp_get.status_code < 300
    todos = resp_get.json()
    assert any(t.get("label") == "buy milk" for t in todos)

    # Verify the JSON file on disk contains the persisted todo
    with store_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, dict)
    assert any(t.get("label") == "buy milk" for t in data.get("todos", []))


# AC-2.2: given an existing todo, update it (PUT) and toggle it (PATCH) and
# assert both return 2xx and the GET shows the updated/toggled fields
def test_AC_2_2_update_toggle(monkeypatch, tmp_path):
    store_path = tmp_path / "store2.json"
    initial = {"todos": [{"id": 1, "label": "old text", "done": False}]}
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(initial), encoding="utf-8")

    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))
    from app.main import app

    client = TestClient(app)

    resp_put = client.put("/api/todos/1", json={"label": "new text"})
    assert 200 <= resp_put.status_code < 300, f"PUT did not return 2xx: {resp_put.status_code}"

    resp_patch = client.patch("/api/todos/1/toggle")
    assert 200 <= resp_patch.status_code < 300, f"PATCH did not return 2xx: {resp_patch.status_code}"

    resp_get = client.get("/api/todos")
    assert 200 <= resp_get.status_code < 300
    todos = resp_get.json()
    matched = [t for t in todos if int(t.get("id", -1)) == 1]
    assert matched, "expected todo with id 1 to be present"
    todo = matched[0]
    assert todo.get("label") == "new text"
    assert todo.get("done") is True

    # Verify on-disk store
    with store_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    todos_on_disk = data.get("todos", [])
    matched_disk = [t for t in todos_on_disk if int(t.get("id", -1)) == 1]
    assert matched_disk
    assert matched_disk[0].get("label") == "new text"
    assert matched_disk[0].get("done") is True


# AC-4.1: instantiate server and perform create/update/toggle/delete, each
# modification returns 2xx and GET reflects the persisted state
def test_AC_4_1_server_modifications_persist(monkeypatch, tmp_path):
    store_path = tmp_path / "store3.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))
    from app.main import app

    client = TestClient(app)

    # Create
    r1 = client.post("/api/todos", json={"label": "task A"})
    assert 200 <= r1.status_code < 300
    todo = r1.json()
    todo_id = int(todo.get("id"))

    # Update
    r2 = client.put(f"/api/todos/{todo_id}", json={"label": "task A updated"})
    assert 200 <= r2.status_code < 300

    # Toggle
    r3 = client.patch(f"/api/todos/{todo_id}/toggle")
    assert 200 <= r3.status_code < 300

    # Ensure GET reflects changes
    r_get = client.get("/api/todos")
    assert 200 <= r_get.status_code < 300
    todos = r_get.json()
    matched = [t for t in todos if int(t.get("id", -1)) == todo_id]
    assert matched
    assert matched[0].get("label") == "task A updated"
    assert matched[0].get("done") is True

    # Delete
    r_del = client.delete(f"/api/todos/{todo_id}")
    assert 200 <= r_del.status_code < 300

    r_after = client.get("/api/todos")
    assert 200 <= r_after.status_code < 300
    todos_after = r_after.json()
    assert all(int(t.get("id", -1)) != todo_id for t in todos_after)

    # Also verify persisted store on disk does not contain the deleted id
    with store_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert all(int(t.get("id", -1)) != todo_id for t in data.get("todos", []))


# AC-5.1: persistence across a simulated restart (tear down and re-instantiate)
def test_AC_5_1_persistence_across_restarts(monkeypatch, tmp_path):
    store_path = tmp_path / "store4.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))
    from app.main import app

    # Session A: create a todo
    client_a = TestClient(app)
    r = client_a.post("/api/todos", json={"label": "persisted task"})
    assert 200 <= r.status_code < 300
    created = r.json()
    created_id = int(created.get("id"))
    client_a.close()

    # Session B: new client against the (re-)instantiated app pointing at same file
    client_b = TestClient(app)
    r_get = client_b.get("/api/todos")
    assert 200 <= r_get.status_code < 300
    todos = r_get.json()
    assert any(int(t.get("id", -1)) == created_id and t.get("label") == "persisted task" for t in todos)

    # Verify on-disk
    with store_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert any(int(t.get("id", -1)) == created_id for t in data.get("todos", []))


# AC-6.1: startup fails with a clear error when TODOS_JSON_PATH parent dir is missing
def test_AC_6_1_startup_fails_on_bad_path(monkeypatch, tmp_path):
    missing_parent = tmp_path / "no_such_dir"
    bad_path = missing_parent / "store.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(bad_path))

    # The application startup is expected to validate the configured path and
    # raise a RuntimeError naming the problematic path and remediation advice.
    with pytest.raises(RuntimeError) as excinfo:
        # Import after setting the env so validation runs during module import/startup
        from app.main import app  # noqa: F401 - intentional import for startup validation

    # The error message should mention the configured path so it's actionable
    assert str(bad_path) in str(excinfo.value)
    assert "Remediation" in str(excinfo.value) or "create" in str(excinfo.value) or "permissions" in str(excinfo.value)
