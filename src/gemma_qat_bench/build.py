"""Clone and compile ``llama.cpp``.

This mirrors the tutorial's shell steps as pure, testable command builders plus
a thin driver. CUDA is auto-detected (overridable), so the same code produces a
GPU build on a CUDA box and a CPU build elsewhere. The command runner is
injectable for tests.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from ._logging import get_logger
from .config import BuildConfig
from .exceptions import BuildError

_LOG = get_logger("build")

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
CudaDetector = Callable[[], bool]

# Server binary locations across llama.cpp build layouts (newer builds put
# binaries under build/bin/).
_SERVER_BINARY_NAMES = ("llama-server", "llama-server.exe")
_SERVER_SUBDIRS = ("bin", ".")


def detect_cuda() -> bool:
    """Return ``True`` if a CUDA toolchain/runtime appears to be present."""
    return shutil.which("nvcc") is not None or shutil.which("nvidia-smi") is not None


class LlamaCppBuilder:
    """Drives ``git clone`` + ``cmake`` to produce a ``llama-server`` binary."""

    def __init__(
        self,
        config: BuildConfig,
        *,
        runner: CommandRunner = subprocess.run,
        cuda_detector: CudaDetector = detect_cuda,
    ) -> None:
        self._config = config
        self._runner = runner
        self._cuda_detector = cuda_detector

    # -- command builders (pure) ------------------------------------------- #

    def clone_command(self) -> list[str]:
        return [
            "git",
            "clone",
            "--depth",
            "1",
            self._config.repo_url,
            str(self._config.source_dir),
        ]

    def configure_command(self, use_cuda: bool) -> list[str]:
        cfg = self._config
        shared = "ON" if cfg.build_shared_libs else "OFF"
        cuda = "ON" if use_cuda else "OFF"
        return [
            "cmake",
            str(cfg.source_dir),
            "-B",
            str(cfg.resolved_build_dir),
            f"-DBUILD_SHARED_LIBS={shared}",
            f"-DGGML_CUDA={cuda}",
        ]

    def build_command(self) -> list[str]:
        cfg = self._config
        jobs = str(cfg.jobs) if cfg.jobs is not None else str(os.cpu_count() or 1)
        command = [
            "cmake",
            "--build",
            str(cfg.resolved_build_dir),
            "--config",
            "Release",
            "-j",
            jobs,
        ]
        if cfg.clean_first:
            command.append("--clean-first")
        command.append("--target")
        command.extend(cfg.targets)
        return command

    # -- resolution --------------------------------------------------------- #

    def resolve_cuda(self) -> bool:
        if self._config.use_cuda is not None:
            return self._config.use_cuda
        return self._cuda_detector()

    def server_binary(self) -> Path:
        """Locate the built ``llama-server`` binary.

        Raises :class:`BuildError` if it cannot be found (e.g. build skipped).
        """
        build_dir = self._config.resolved_build_dir
        for subdir in _SERVER_SUBDIRS:
            for name in _SERVER_BINARY_NAMES:
                candidate = build_dir / subdir / name
                if candidate.exists():
                    return candidate
        raise BuildError(
            f"llama-server not found under {build_dir} (looked in "
            f"{', '.join(_SERVER_SUBDIRS)}); has the build completed?"
        )

    # -- driver ------------------------------------------------------------- #

    def clone(self) -> None:
        if self._config.source_dir.exists():
            _LOG.info("llama.cpp source already present at %s", self._config.source_dir)
            return
        self._run(self.clone_command(), "git clone")

    def build(self) -> Path:
        """Clone (if needed), configure, and build. Returns the server binary."""
        self.clone()
        use_cuda = self.resolve_cuda()
        _LOG.info("configuring llama.cpp (CUDA=%s)", "ON" if use_cuda else "OFF")
        self._run(self.configure_command(use_cuda), "cmake configure")
        _LOG.info("building targets: %s", ", ".join(self._config.targets))
        self._run(self.build_command(), "cmake build")
        binary = self.server_binary()
        _LOG.info("built llama-server at %s", binary)
        return binary

    # -- internals ---------------------------------------------------------- #

    def _run(self, command: list[str], label: str) -> None:
        try:
            result = self._runner(command)
        except FileNotFoundError as exc:
            raise BuildError(
                f"{label} failed: command not found ({command[0]!r}). "
                "Install the build prerequisites (git, cmake, a C/C++ toolchain)."
            ) from exc
        except OSError as exc:
            raise BuildError(f"{label} failed to launch: {exc}") from exc

        returncode = getattr(result, "returncode", 0)
        if returncode != 0:
            raise BuildError(f"{label} exited with code {returncode}: {command}")


__all__ = ["LlamaCppBuilder", "detect_cuda", "CommandRunner", "CudaDetector"]
