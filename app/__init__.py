"""Application package for TODOO.

This package exposes application-level modules such as persistence. It is a
stable import point used by tests and by the application entrypoint. Keep
top-level initialization here minimal to avoid side-effects during imports.
"""

__all__ = ["persistence"]
