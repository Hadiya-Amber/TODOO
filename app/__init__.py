"""Application package for TODOO.

This module exposes the FastAPI application instance as ``app`` so tests and
uvicorn can import it directly (``from app import app``). A small set of
HTTP endpoints implement the /api/todos CRUD surface used by the test-suite.

The persistence module is validated at startup to ensure the configured JSON
path is writable; when validation fails the server will raise a clear
RuntimeError and exit so developers can remediate filesystem permissions or
create the missing file.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

from . import persistence


class TodoIn(BaseModel):
    """Incoming model for creating a todo item.

    Attributes:
        title: str: Short human-readable title for the todo.
    """
    title: str


class Todo(BaseModel):
    """Representation of a persisted todo item returned by the API.

    Attributes:
        id: int: Numeric identifier for the todo.
        title: str: Title text.
        completed: bool: Completion flag.
    """
    id: int
    title: str
    completed: bool = False


app = FastAPI()


@app.get("/")
def read_root() -> dict:
    """Health-check root endpoint returning a short OK message."""
    return {"message": "ok"}



@app.on_event("startup")
def _validate_persistence_on_startup() -> None:
    """Validate persistence configuration during application startup.

    This runs when the ASGI server starts and will raise a RuntimeError if the
    configured JSON file path is missing or not writable. Raising here prevents
    the server from starting with a broken persistence backing.
    """
    persistence.validate_data_file_path()


def _read_store() -> List[dict]:
    return persistence.load_store()


def _write_store(items: List[dict]) -> None:
    persistence.save_store(items)


def _next_id(items: List[dict]) -> int:
    ids = [int(i.get("id", 0)) for i in items if i.get("id") is not None]
    return max(ids, default=0) + 1


@app.get("/api/todos", response_model=List[Todo])
def list_todos() -> List[Todo]:
    """Return the list of todos persisted in the configured store.

    Returns a list of Todo objects. If the store is empty or missing an
    empty list is returned.
    """
    return _read_store()


@app.post("/api/todos", response_model=Todo)
def create_todo(payload: TodoIn) -> Todo:
    """Create a new todo item with the provided title.

    The new item is persisted to disk and returned.
    """
    items = _read_store()
    nid = _next_id(items)
    item = {"id": nid, "title": payload.title, "completed": False}
    items.append(item)
    _write_store(items)
    return JSONResponse(status_code=200, content=item)


@app.patch("/api/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: int, payload: dict) -> Todo:
    """Apply a partial update to an existing todo.

    The payload may include any of the Todo fields (title, completed).
    """
    items = _read_store()
    for it in items:
        if int(it.get("id")) == int(todo_id):
            # Allow partial updates
            it.update(payload)
            _write_store(items)
            return it
    raise HTTPException(status_code=404, detail="todo not found")


@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int) -> JSONResponse:
    """Delete the todo with the given id from the store.

    Returns a JSONResponse indicating the id deleted on success. Raises 404
    when the todo does not exist.
    """
    items = _read_store()
    new_items = [it for it in items if int(it.get("id")) != int(todo_id)]
    if len(new_items) == len(items):
        raise HTTPException(status_code=404, detail="todo not found")
    _write_store(new_items)
    return JSONResponse(status_code=200, content={"deleted": todo_id})


__all__ = ["app", "persistence"]
