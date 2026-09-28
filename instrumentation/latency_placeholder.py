"""Runtime latency instrumentation API.

This module provides a compact, test-friendly instrumentation API used by
the application. It records latency samples and diagnostics into an
in-memory capture that tests can inspect. Production deployments can replace
or extend these helpers to forward samples to a metrics backend.

Public API
- init_latency_instrumentation(config: Optional[dict]) -> None
- record_latency(operation: str, elapsed_s: float, extra: Optional[dict]) -> None
- emit_diagnostic(kind: str, details: dict) -> None
- get_captured_records() -> list
- get_captured_diagnostics() -> list
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Optional

_logger = logging.getLogger("instrumentation.latency")

# In-memory capture used by tests and by the verification harness. Tests should
# call clear_captured_* helpers to reset state between cases.
_CAPTURED: list[dict] = []
_DIAGNOSTICS: list[dict] = []


def init_latency_instrumentation(config: Optional[dict] = None) -> None:
    """Initialize the instrumentation subsystem.

    The reference implementation only configures module-level logging and
    optionally accepts a config dict for future extensions. Calling this is
    idempotent.
    """
    _logger.debug("latency instrumentation initialized: %s", bool(config))


def record_latency(operation: str, elapsed_s: float, extra: Optional[dict] = None) -> None:
    """Record a latency measurement.

    The recorded entry is a dict with fields:
    - timestamp: ISO-8601 UTC timestamp string
    - operation: operation label (create, edit, toggle, delete)
    - elapsed_s: floating point seconds of wall-clock time
    - extra: optional dict with additional context
    """
    ts = datetime.now(timezone.utc).isoformat()
    entry = {"timestamp": ts, "operation": operation, "elapsed_s": float(elapsed_s)}
    if extra:
        entry["extra"] = extra
    _CAPTURED.append(entry)
    # Also emit a structured debug log for operators who prefer logs.
    _logger.debug("latency %s %s", operation, entry)


def emit_diagnostic(kind: str, details: dict) -> None:
    """Emit a diagnostic event for persistence or parsing issues.

    The diagnostic has at minimum: error_type, timestamp, and details. Tests
    in this repository look for the 'error_type' key specifically, so include
    it here while keeping 'kind' for backwards compatibility.
    """
    ts = datetime.now(timezone.utc).isoformat()
    diag = {"error_type": kind, "kind": kind, "timestamp": ts, "details": details}
    _DIAGNOSTICS.append(diag)
    _logger.warning("diagnostic %s %s", kind, details)


def get_captured_records() -> list[dict]:
    """Return a copy of the list of captured latency records.

    Tests should not mutate the returned list in-place.
    """
    return list(_CAPTURED)


def clear_captured_records() -> None:
    """Clear the in-memory latency record capture.

    Useful to reset state between tests.
    """
    _CAPTURED.clear()


def get_captured_diagnostics() -> list[dict]:
    """Return a copy of emitted diagnostics.

    Diagnostics are emitted for persistence and parse errors to aid automated
    verification.
    """
    return list(_DIAGNOSTICS)


def clear_captured_diagnostics() -> None:
    """Clear the in-memory diagnostics capture."""
    _DIAGNOSTICS.clear()


__all__ = [
    "init_latency_instrumentation",
    "record_latency",
    "emit_diagnostic",
    "get_captured_records",
    "clear_captured_records",
    "get_captured_diagnostics",
    "clear_captured_diagnostics",
]
