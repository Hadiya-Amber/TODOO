"""Verification runner helpers for TODOO.

This module provides utilities used by the verification harness to compute
median per-operation latencies from captured instrumentation records.

Public API
- compute_median_ms_by_operation(records: list[dict]) -> dict
  Returns a mapping operation -> median elapsed milliseconds (float).
"""
from __future__ import annotations

from typing import Dict, Iterable, List
import math


def _median(vals: List[float]) -> float:
    """Return median of a non-empty list of floats."""
    n = len(vals)
    if n == 0:
        raise ValueError("cannot compute median of empty list")
    vals_sorted = sorted(vals)
    mid = n // 2
    if n % 2 == 1:
        return vals_sorted[mid]
    return (vals_sorted[mid - 1] + vals_sorted[mid]) / 2.0


def compute_median_ms_by_operation(records: Iterable[dict]) -> Dict[str, float]:
    """Compute median elapsed time per operation from instrumentation records.

    Each record is expected to be a mapping with at least the keys:
    - 'operation': a string label (create/edit/toggle/delete)
    - 'elapsed_s': floating-point seconds

    Returns a dict mapping operation -> median milliseconds (float).
    """
    by_op: Dict[str, List[float]] = {}
    for r in records:
        op = r.get("operation")
        if not op:
            continue
        elapsed_s = r.get("elapsed_s")
        try:
            elapsed = float(elapsed_s)
        except Exception:
            # Skip malformed entries
            continue
        by_op.setdefault(op, []).append(elapsed)

    medians_ms: Dict[str, float] = {}
    for op, vals in by_op.items():
        if not vals:
            continue
        med_s = _median(vals)
        # convert to milliseconds
        med_ms = med_s * 1000.0
        # normalize NaN/inf to a large sentinel
        if math.isfinite(med_ms):
            medians_ms[op] = med_ms
    return medians_ms


__all__ = ["compute_median_ms_by_operation"]
