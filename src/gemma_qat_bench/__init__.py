"""gemma_qat_bench -- benchmark QAT vs non-QAT GGUF models with llama.cpp.

A small, fully-tested toolkit that reproduces the DataCamp "Gemma 4 QAT"
tutorial: build ``llama.cpp``, download the non-QAT and QAT GGUF variants, serve
each with ``llama-server``, and compare generation speed and VRAM use.
"""

from __future__ import annotations

from .benchmark import BenchmarkRunner
from .build import LlamaCppBuilder
from .client import LlamaClient
from .config import (
    AppConfig,
    BenchmarkConfig,
    BuildConfig,
    ModelSpec,
    SamplingConfig,
    ServerConfig,
)
from .exceptions import (
    BuildError,
    ConfigError,
    GemmaQATBenchError,
    InferenceError,
    ModelDownloadError,
    ServerStartupError,
)
from .metrics import AggregatedMetrics, RunMetrics
from .models import ModelManager
from .report import BenchmarkReport, ComparisonSummary
from .server import ServerManager
from .vram import query_vram_used_mib

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Orchestration
    "BenchmarkRunner",
    "BenchmarkReport",
    "ComparisonSummary",
    # Building blocks
    "LlamaCppBuilder",
    "LlamaClient",
    "ModelManager",
    "ServerManager",
    "query_vram_used_mib",
    # Metrics
    "AggregatedMetrics",
    "RunMetrics",
    # Config
    "AppConfig",
    "BenchmarkConfig",
    "BuildConfig",
    "ModelSpec",
    "SamplingConfig",
    "ServerConfig",
    # Errors
    "GemmaQATBenchError",
    "ConfigError",
    "BuildError",
    "ModelDownloadError",
    "ServerStartupError",
    "InferenceError",
]
