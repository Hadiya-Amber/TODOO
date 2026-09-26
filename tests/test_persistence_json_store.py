import json
import os
from pathlib import Path
import pytest

# Intentionally import the planned symbol that does not yet exist so collection
# fails with a clear import-time error until the implementation is added.
# This provides the required RED evidence that the new validation API is
# missing. Do not guard this import: the test harness needs to see the
# import-time failure.
from app.persistence import save_store, load_store, validate_data_file_path  # pragma: no cover - expected missing until implemented


def test_AC_4_1_save_and_load_roundtrip_persists_store(tmp_path, monkeypatch):
    """AC-4.1: save_store then load_store round-trip persists the sample list.

    Configure the runtime via TODOS_JSON_PATH to point at a temporary file,
    write a sample list and assert load_store() returns the identical data.
    """
    file_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(file_path))

    sample = [{"id": 1, "title": "x", "completed": False}]

    # Call save_store and load_store as the public API promises.
    save_store(sample)
    loaded = load_store()

    assert isinstance(loaded, list), "load_store must return a list"
    assert loaded == sample, "loaded store must match what was saved"


def test_AC_6_1_save_store_atomic_write_produces_valid_json(tmp_path, monkeypatch):
    """AC-6.1: After save_store completes the target file must contain valid JSON."""
    file_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(file_path))

    sample = [{"id": 2, "title": "atomic", "completed": True}]

    # Save and then immediately read the file to ensure it is parseable JSON.
    save_store(sample)

    # Ensure the file exists and contains valid JSON matching the sample.
    assert file_path.exists(), "persistence must create the target file"

    with file_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    assert data == sample, "on-disk JSON must equal the saved sample"


def test_AC_5_1_validate_data_file_path_raises_on_missing_or_unwritable(tmp_path, monkeypatch):
    """AC-5.1: validate_data_file_path must raise RuntimeError for missing/unwritable paths.

    We simulate an unwritable file by creating a directory and a file with
    no write permission for the current user. The function should raise a
    RuntimeError naming the path and offering remediation steps.
    """
    # Create a directory and a file inside it, then remove write perms.
    dir_path = tmp_path / "nodir"
    dir_path.mkdir()
    target = dir_path / "todos.json"
    target.write_text("[]", encoding="utf-8")

    # Remove write permission for owner to simulate unwritable file.
    # This may not behave identically on all platforms (Windows), but the
    # intent is to provide a path that validate_data_file_path will treat as
    # not writable. If chmod is ignored, the implementation must still check
    # writability and raise accordingly.
    try:
        mode = target.stat().st_mode
        target.chmod(0o444)
    except PermissionError:
        # If chmod is not permitted in the environment, proceed: the
        # implementation under test must still perform checks that cause a
        # RuntimeError for unwritable paths.
        pass

    monkeypatch.setenv("TODOS_JSON_PATH", str(target))

    with pytest.raises(RuntimeError) as excinfo:
        validate_data_file_path()

    msg = str(excinfo.value)
    assert str(target) in msg, "error message must name the configured path"
    assert any(term in msg.lower() for term in ("create", "chmod", "permissions", "writ")), (
        "error message should advise remediation such as creating the file or adjusting permissions"
    )


def _client_post_create(client, payload):
    resp = client.post("/api/todos", json=payload)
    assert 200 <= resp.status_code < 300, f"POST /api/todos must return 2xx, got {resp.status_code}"
    return resp.json()


def test_AC_2_1_post_creates_and_reflected_via_get(tmp_path, monkeypatch):
    """AC-2.1: POST /api/todos creates an item and GET /api/todos returns it."""
    file_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(file_path))

    # Import TestClient inside the test to avoid pulling starlette/testclient at
    # module import time. The app FastAPI instance is expected to be exposed
    # as `app` from the package import point (e.g. `from app import app`).
    from fastapi.testclient import TestClient
    from app import app  # This import is expected to fail until the FastAPI app is added

    client = TestClient(app)

    # Create a todo
    created = _client_post_create(client, {"title": "task1"})
    assert any(created.get(k) for k in ("id", "title")), "created item must include id or title"

    # Ensure GET reflects the created todo
    resp = client.get("/api/todos")
    assert 200 <= resp.status_code < 300
    items = resp.json()
    assert any(item.get("title") == "task1" for item in items), "GET must return the created todo"


def test_AC_2_2_patch_updates_and_reflected(tmp_path, monkeypatch):
    """AC-2.2: PATCH an existing todo and see updated fields on GET."""
    file_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(file_path))

    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)

    # Create
    created = _client_post_create(client, {"title": "to-update"})
    todo_id = created.get("id")
    assert todo_id is not None, "created todo must have an id for update"

    # Patch/update
    resp = client.patch(f"/api/todos/{todo_id}", json={"title": "updated", "completed": True})
    assert 200 <= resp.status_code < 300

    # Verify
    resp = client.get("/api/todos")
    assert 200 <= resp.status_code < 300
    items = resp.json()
    found = next((t for t in items if t.get("id") == todo_id), None)
    assert found is not None, "updated todo must still be present"
    assert found.get("title") == "updated"
    assert found.get("completed") is True


def test_AC_2_3_delete_removes_and_reflected(tmp_path, monkeypatch):
    """AC-2.3: DELETE a todo and ensure it no longer appears in GET."""
    file_path = tmp_path / "todos.json"
    monkeypatch.setenv("TODOS_JSON_PATH", str(file_path))

    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)

    # Create
    created = _client_post_create(client, {"title": "to-delete"})
    todo_id = created.get("id")
    assert todo_id is not None

    # Delete
    resp = client.delete(f"/api/todos/{todo_id}")
    assert 200 <= resp.status_code < 300

    # Verify absence
    resp = client.get("/api/todos")
    assert 200 <= resp.status_code < 300
    items = resp.json()
    assert not any(t.get("id") == todo_id for t in items), "deleted todo must not be present"
