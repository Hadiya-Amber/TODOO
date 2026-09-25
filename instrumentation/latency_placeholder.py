"""Runtime latency instrumentation API (no-op reference implementation).

This module defines a small, stable surface for recording operation latency.
Implementations should replace or extend these functions to forward samples
to monitoring backends, batch and sample them, or expose metrics for scraping.

Public API:
- init_latency_instrumentation(config: Optional[dict]) -> None
- record_latency(operation: str, ms: float) -> None

The functions in this reference implementation are intentionally lightweight
and side-effect free so importing them during tests and early development
does not require an observability backend to be present.
"""

from __future__ import annotations

import logging
from typing import Optional

_logger = logging.getLogger("instrumentation.latency")


def init_latency_instrumentation(config: Optional[dict] = None) -> None:
    """Initialize observability exporters or collectors.

    Args:
        config: Optional configuration for exporters. This reference
            implementation ignores the value.
    """
    _logger.debug("initialized latency instrumentation (no-op reference)")


def record_latency(operation: str, ms: float) -> None:
    """Record a latency sample for the given operation name.

    The reference implementation logs the observation at debug level. Real
    implementations should take care to avoid high-cardinality labels and to
    batch or sample events to reduce overhead.
    """
    _logger.debug("latency sample - %s: %.3fms", operation, ms)


__all__ = ["init_latency_instrumentation", "record_latency"]
