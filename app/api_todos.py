"""HTTP API router for todo operations.

This module provides a small FastAPI APIRouter exposing the CRUD endpoints
used by the project tests and by local development. The router delegates
persistence to the package-level helpers defined in app.__init__ which keep
behaviour consistent with the rest of the codebase.
"""
from __future__ import annotations

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

# Import the package-level functions from app which define the behaviour used
# elsewhere in the repository. Import names are deliberately explicit to avoid
# circular import surprises when uvicorn imports app.main:app.
from app import list_todos as _list_todos
from app import create_todo as _create_todo
from app import update_todo as _update_todo
from app import toggle_todo as _toggle_todo
from app import delete_todo as _delete_todo

router = APIRouter(prefix="/api/todos", tags=["todos"])


class TodoIn(BaseModel):
    """Request model for creating or updating a todo.

    label: optional human-readable text for the todo
    done: optional boolean flag indicating completion
    """
    label: str | None = None
    done: bool | None = None


class TodoOut(BaseModel):
    """Response model for a persisted todo."""
    id: int
    label: str | None = None
    done: bool = False


@router.get("", response_model=List[TodoOut])
def get_todos() -> List[Dict[str, Any]]:
    """Return all todos."""
    return _list_todos()


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def post_todo(item: TodoIn) -> Dict[str, Any]:
    """Create a new todo from the request body."""
    payload = {k: v for k, v in item.dict().items() if v is not None}
    return _create_todo(payload)


@router.put("/{todo_id}", response_model=TodoOut)
def put_todo(todo_id: int, item: TodoIn) -> Dict[str, Any]:
    """Update/replace fields of an existing todo."""
    payload = {k: v for k, v in item.dict().items() if v is not None}
    try:
        return _update_todo(todo_id, payload)
    except HTTPException as exc:
        # re-raise to keep FastAPI's behaviour and status codes
        raise exc


@router.patch("/{todo_id}/toggle", response_model=TodoOut)
def patch_toggle(todo_id: int) -> Dict[str, Any]:
    """Toggle the done state of a todo."""
    try:
        return _toggle_todo(todo_id)
    except HTTPException as exc:
        raise exc


@router.delete("/{todo_id}")
def delete(todo_id: int) -> Dict[str, int]:
    """Delete a todo by id and return a confirmation JSON object."""
    try:
        return _delete_todo(todo_id)
    except HTTPException as exc:
        raise exc
