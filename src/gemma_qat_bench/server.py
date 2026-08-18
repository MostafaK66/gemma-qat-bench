"""Lifecycle management for a single ``llama-server`` process.

:class:`ServerManager` is a context manager: entering it launches the server and
blocks until ``/health`` reports ready; leaving it terminates the process. Both
the process factory and the health-check client are injectable so the state
machine can be unit-tested without spawning anything.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import Protocol

from ._logging import get_logger
from .client import LlamaClient
from .config import ServerConfig
from .exceptions import ServerStartupError

_LOG = get_logger("server")

_TERMINATE_TIMEOUT_S = 10.0


class _Process(Protocol):
    """The subset of :class:`subprocess.Popen` that this module relies on."""

    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...
    def wait(self, timeout: float | None = ...) -> int: ...


ProcessFactory = Callable[[list[str]], _Process]
ClientFactory = Callable[[str], LlamaClient]


def _default_process_factory(command: list[str]) -> _Process:
    return subprocess.Popen(  # noqa: S603 - command is built from validated config
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class ServerManager:
    """Start, health-check, and stop a ``llama-server`` for one model."""

    def __init__(
        self,
        config: ServerConfig,
        model_gguf: Path,
        *,
        process_factory: ProcessFactory = _default_process_factory,
        client_factory: ClientFactory | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._model_gguf = Path(model_gguf)
        self._process_factory = process_factory
        self._client_factory = client_factory or self._default_client_factory
        self._sleep = sleep
        self._monotonic = monotonic
        self._process: _Process | None = None

    # -- public API --------------------------------------------------------- #

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def build_command(self) -> list[str]:
        """Assemble the ``llama-server`` argument vector from config."""
        cfg = self._config
        command = [
            str(cfg.binary_path),
            "-m",
            str(self._model_gguf),
            "--host",
            cfg.host,
            "--port",
            str(cfg.port),
            "--ctx-size",
            str(cfg.ctx_size),
            "--n-gpu-layers",
            str(cfg.n_gpu_layers),
        ]
        command.extend(cfg.extra_args)
        return command

    def start(self) -> None:
        """Launch the server and block until it is healthy."""
        if self._process is not None:
            raise ServerStartupError("server is already running")
        command = self.build_command()
        _LOG.info("starting llama-server: %s", " ".join(command))
        self._process = self._process_factory(command)
        self._wait_until_healthy()
        _LOG.info("llama-server ready at %s", self.base_url)

    def stop(self) -> None:
        """Terminate the server if running (idempotent)."""
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=_TERMINATE_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                _LOG.warning("llama-server ignored SIGTERM; killing")
                process.kill()
                process.wait(timeout=_TERMINATE_TIMEOUT_S)
        self._process = None

    # -- context manager ---------------------------------------------------- #

    def __enter__(self) -> ServerManager:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.stop()

    # -- internals ---------------------------------------------------------- #

    def _default_client_factory(self, base_url: str) -> LlamaClient:
        return LlamaClient(base_url, timeout_s=5.0)

    def _wait_until_healthy(self) -> None:
        if self._process is None:
            raise ServerStartupError("server process is not available during startup")

        client = self._client_factory(self.base_url)
        deadline = self._monotonic() + self._config.startup_timeout_s
        while self._monotonic() < deadline:
            exit_code = self._process.poll()
            if exit_code is not None:
                self._process = None
                raise ServerStartupError(
                    f"llama-server exited with code {exit_code} before becoming "
                    "healthy (check the binary path, model file, and free VRAM)"
                )
            if client.health():
                return
            self._sleep(self._config.health_poll_interval_s)

        self.stop()
        raise ServerStartupError(
            f"llama-server did not become healthy within "
            f"{self._config.startup_timeout_s:.0f}s"
        )


__all__ = ["ServerManager", "ProcessFactory", "ClientFactory"]
