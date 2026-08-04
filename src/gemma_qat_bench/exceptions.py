"""Exception hierarchy for :mod:`gemma_qat_bench`.

Every error raised by this package derives from :class:`GemmaQATBenchError`, so
callers can catch the whole family with a single ``except`` clause while still
being able to discriminate on the concrete subclass when they need to.
"""

from __future__ import annotations


class GemmaQATBenchError(Exception):
    """Base class for all errors raised by this package."""


class ConfigError(GemmaQATBenchError, ValueError):
    """Raised when a configuration object fails validation.

    Subclasses :class:`ValueError` as well so that existing ``except ValueError``
    handlers keep working for callers that treat config problems generically.
    """


class BuildError(GemmaQATBenchError):
    """Raised when building ``llama.cpp`` fails."""


class ModelDownloadError(GemmaQATBenchError):
    """Raised when a model cannot be downloaded or resolved on disk."""


class ServerStartupError(GemmaQATBenchError):
    """Raised when ``llama-server`` does not come up healthy in time."""


class InferenceError(GemmaQATBenchError):
    """Raised when an inference request fails or returns an unusable payload."""


__all__ = [
    "GemmaQATBenchError",
    "ConfigError",
    "BuildError",
    "ModelDownloadError",
    "ServerStartupError",
    "InferenceError",
]
