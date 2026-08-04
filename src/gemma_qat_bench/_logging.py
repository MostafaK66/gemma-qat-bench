"""Internal logging helpers.

The library itself never configures the root logger; that is the application's
job. :func:`configure_logging` is a convenience used only by the CLI so that a
bare ``gemma-qat-bench`` invocation produces readable output.
"""

from __future__ import annotations

import logging

_LOGGER_NAME = "gemma_qat_bench"
_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a package logger, optionally namespaced by ``name``."""
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


def configure_logging(level: int = logging.INFO) -> None:
    """Attach a single stream handler to the package logger (idempotent)."""
    logger = get_logger()
    logger.setLevel(level)
    # Avoid stacking duplicate handlers when the CLI is invoked more than once
    # in the same process (e.g. in tests).
    if any(getattr(h, "_gqb_handler", False) for h in logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT))
    handler._gqb_handler = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.propagate = False


__all__ = ["get_logger", "configure_logging"]
