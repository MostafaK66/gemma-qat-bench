"""Orchestrate the end-to-end benchmark.

For each model the runner: ensures the GGUF is present, starts a server, runs
warmup passes, samples VRAM at steady state, runs the measured passes, and
aggregates. Every collaborator (model manager, server factory, client factory,
VRAM sampler) is injectable, so :meth:`BenchmarkRunner.run` is fully exercised
offline in the test suite.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol

from ._logging import get_logger
from .client import LlamaClient
from .config import AppConfig, ServerConfig
from .metrics import AggregatedMetrics, RunMetrics
from .models import ModelManager
from .report import BenchmarkReport
from .server import ServerManager
from .vram import query_vram_used_mib

_LOG = get_logger("benchmark")


class ManagedServer(Protocol):
    """Structural type for the object returned by a server factory."""

    @property
    def base_url(self) -> str: ...

    def __enter__(self) -> "ManagedServer": ...

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Any: ...


ServerFactory = Callable[[ServerConfig, Path], ManagedServer]
ClientFactory = Callable[[str, float], LlamaClient]
VramSampler = Callable[[], "int | None"]


def _default_server_factory(config: ServerConfig, gguf: Path) -> ManagedServer:
    return ServerManager(config, gguf)


def _default_client_factory(base_url: str, timeout_s: float) -> LlamaClient:
    return LlamaClient(base_url, timeout_s=timeout_s)


class BenchmarkRunner:
    """Runs the QAT vs non-QAT benchmark described by an :class:`AppConfig`."""

    def __init__(
        self,
        config: AppConfig,
        *,
        model_manager: ModelManager | None = None,
        server_factory: ServerFactory = _default_server_factory,
        client_factory: ClientFactory = _default_client_factory,
        vram_sampler: VramSampler = query_vram_used_mib,
    ) -> None:
        self._config = config
        self._model_manager = model_manager or ModelManager()
        self._server_factory = server_factory
        self._client_factory = client_factory
        self._vram_sampler = vram_sampler

    def run(self) -> BenchmarkReport:
        """Benchmark every configured model and return the assembled report."""
        results: list[AggregatedMetrics] = []
        for spec in self._config.models:
            _LOG.info("=== benchmarking %s ===", spec.display_name)
            gguf = self._model_manager.ensure(spec)
            results.append(self._benchmark_model(spec, gguf))
        return BenchmarkReport.build(results, self._config)

    # -- internals ---------------------------------------------------------- #

    def _benchmark_model(self, spec, gguf: Path) -> AggregatedMetrics:
        bench = self._config.benchmark
        with self._server_factory(self._config.server, gguf) as server:
            client = self._client_factory(server.base_url, bench.request_timeout_s)

            for i in range(bench.warmup_runs):
                _LOG.info("warmup %d/%d", i + 1, bench.warmup_runs)
                self._one_chat(client, spec)

            vram = self._vram_sampler() if self._config.capture_vram else None
            if vram is not None:
                _LOG.info("VRAM in use (steady state): %d MiB", vram)

            runs: list[RunMetrics] = []
            for i in range(bench.n_runs):
                payload, wall = self._one_chat(client, spec)
                run = RunMetrics.from_response(payload, wall)
                _LOG.info(
                    "run %d/%d: %d tok in %.3fs (%.2f tok/s)",
                    i + 1,
                    bench.n_runs,
                    run.completion_tokens,
                    run.wall_time_s,
                    run.effective_gen_per_s,
                )
                runs.append(run)

        return AggregatedMetrics.from_runs(spec, runs, vram_used_mib=vram)

    def _one_chat(self, client: LlamaClient, spec) -> tuple[dict[str, Any], float]:
        bench = self._config.benchmark
        return client.chat(
            model=spec.key,
            system_prompt=bench.system_prompt,
            user_prompt=bench.prompt,
            sampling=self._config.sampling,
        )


__all__ = ["BenchmarkRunner", "ServerFactory", "ClientFactory", "VramSampler"]
