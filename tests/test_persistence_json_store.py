import json
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Each test sets the TODOS_JSON_PATH environment variable before importing
# application modules so that any import-time validation sees the intended
# configuration. Tests intentionally import the repository modules inside the
# test after setting the env var so they fail at import/usage until the
# planned changes are implemented (this is the RED signal the reviewer
# expects).


def test_AC_2_1_post_creates_and_gets(tmp_path, monkeypatch):
    """AC-2.1: POST /api/todos creates a todo and GET /api/todos returns it"""
    store_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    # Import the app package after the env var is set so startup-time checks
    # see the configured path.
    importlib.invalidate_caches()
    app_mod = importlib.import_module("app")
    importlib.reload(app_mod)

    client = TestClient(getattr(app_mod, "app"))

    resp = client.post("/api/todos", json={"label": "task1"})
    assert 200 <= resp.status_code < 300, f"POST returned {resp.status_code}: {resp.text}"

    resp = client.get("/api/todos")
    assert 200 <= resp.status_code < 300, f"GET returned {resp.status_code}: {resp.text}"
    data = resp.json()
    assert isinstance(data, list), "GET /api/todos should return a JSON list"
    assert any(item.get("label") == "task1" for item in data), "created todo not present in GET /api/todos"


def test_AC_2_2_put_updates_persisted_todo(tmp_path, monkeypatch):
    """AC-2.2: editing an existing persisted todo is reflected in subsequent GET"""
    store_path = tmp_path / "todos.json"
    # Prepare a persisted store file that the planned changes will accept
    initial = {"todos": [{"id": 1, "label": "orig"}]}
    store_path.write_text(json.dumps(initial), encoding="utf-8")

    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    importlib.invalidate_caches()
    app_mod = importlib.import_module("app")
    importlib.reload(app_mod)

    client = TestClient(getattr(app_mod, "app"))

    resp = client.put("/api/todos/1", json={"label": "updated"})
    assert 200 <= resp.status_code < 300, f"PUT returned {resp.status_code}: {resp.text}"

    resp = client.get("/api/todos")
    assert 200 <= resp.status_code < 300, f"GET returned {resp.status_code}: {resp.text}"
    data = resp.json()
    found = [t for t in data if t.get("id") == 1]
    assert found, "todo with id 1 not found after update"
    assert found[0].get("label") == "updated", "todo label was not updated"


def test_AC_2_3_toggle_and_delete_observable(tmp_path, monkeypatch):
    """AC-2.3: toggling or deleting a persisted todo is observable via GET"""
    store_path = tmp_path / "todos.json"
    initial = {"todos": [{"id": 1, "label": "to-be-deleted", "done": False}]}
    store_path.write_text(json.dumps(initial), encoding="utf-8")

    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    importlib.invalidate_caches()
    app_mod = importlib.import_module("app")
    importlib.reload(app_mod)

    client = TestClient(getattr(app_mod, "app"))

    resp = client.patch("/api/todos/1/toggle")
    assert 200 <= resp.status_code < 300, f"PATCH(toggle) returned {resp.status_code}: {resp.text}"

    resp = client.get("/api/todos")
    assert 200 <= resp.status_code < 300, f"GET returned {resp.status_code}: {resp.text}"
    data = resp.json()
    found = [t for t in data if t.get("id") == 1]
    assert found, "todo with id 1 not found after toggle"
    assert found[0].get("done") is True, "todo was not toggled to done"

    resp = client.delete("/api/todos/1")
    assert 200 <= resp.status_code < 300, f"DELETE returned {resp.status_code}: {resp.text}"

    resp = client.get("/api/todos")
    assert 200 <= resp.status_code < 300, f"GET returned {resp.status_code}: {resp.text}"
    data = resp.json()
    assert not any(t.get("id") == 1 for t in data), "deleted todo still present after DELETE"


def test_AC_4_1_save_and_load_roundtrip(tmp_path, monkeypatch):
    """AC-4.1: save_store then load_store round-trips the saved data"""
    store_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    importlib.invalidate_caches()
    persistence = importlib.import_module("app.persistence")
    importlib.reload(persistence)

    payload = {"todos": [{"id": 1, "label": "x"}]}
    # The planned API saves a dict-shaped payload; call save_store as described
    persistence.save_store(payload)

    loaded = persistence.load_store()
    assert loaded == payload, f"loaded data {loaded!r} did not equal saved payload {payload!r}"


def test_AC_4_2_load_reads_existing_file(tmp_path, monkeypatch):
    """AC-4.2: load_store reads an existing file created by a prior invocation"""
    store_path = tmp_path / "todos.json"
    persisted = {"todos": [{"id": 42, "label": "fromfile"}]}
    store_path.write_text(json.dumps(persisted), encoding="utf-8")

    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    importlib.invalidate_caches()
    persistence = importlib.import_module("app.persistence")
    importlib.reload(persistence)

    loaded = persistence.load_store()
    assert loaded == persisted, "load_store did not return the todos written to the file"


def test_AC_5_1_validate_fails_on_nonexistent_parent(tmp_path, monkeypatch):
    """AC-5.1: validate_data_file fails when the configured parent directory doesn't exist"""
    store_path = tmp_path / "no_such_dir" / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    importlib.invalidate_caches()
    persistence = importlib.import_module("app.persistence")
    importlib.reload(persistence)

    cfg = Path(persistence.get_data_file_path())
    with pytest.raises(RuntimeError) as exc:
        persistence.validate_data_file(cfg)
    msg = str(exc.value)
    assert str(cfg) in msg, "error message must include the configured path"
    assert any(term in msg.lower() for term in ("create", "permission", "permissions", "adjust", "remedi")), (
        "error message should include remediation advice (for example: create file or adjust permissions)"
    )


def test_AC_5_2_validate_fails_on_unwritable_file(tmp_path, monkeypatch):
    """AC-5.2: validate_data_file fails when the file exists but is not writable"""
    store_path = tmp_path / "todos.json"
    store_path.write_text("[]", encoding="utf-8")
    # Attempt to remove write permissions for the current user. Restore in finally.
    store_path.chmod(0o400)

    monkeypatch.setenv("TODOS_JSON_PATH", str(store_path))

    importlib.invalidate_caches()
    persistence = importlib.import_module("app.persistence")
    importlib.reload(persistence)

    cfg = Path(persistence.get_data_file_path())
    try:
        with pytest.raises(RuntimeError) as exc:
            persistence.validate_data_file(cfg)
        msg = str(exc.value)
        assert str(cfg) in msg, "error message must include the configured path"
        assert any(term in msg.lower() for term in ("permission", "permissions", "write")), (
            "error message should suggest adjusting file permissions"
        )
    finally:
        # Restore permissions so tmp_path cleanup is not hindered on Unix-like systems
        try:
            store_path.chmod(0o600)
        except OSError:
            # If chmod is not supported on this platform, ignore so cleanup proceeds
            pass
