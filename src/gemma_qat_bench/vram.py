"""Sample GPU memory usage via ``nvidia-smi``.

Everything here degrades gracefully: on a machine with no NVIDIA GPU (or no
``nvidia-smi``) the sampler simply returns ``None`` and the benchmark proceeds
without a VRAM column.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable

from ._logging import get_logger

_LOG = get_logger("vram")

CommandRunner = Callable[..., subprocess.CompletedProcess]

_NVIDIA_SMI_ARGS = [
    "nvidia-smi",
    "--query-gpu=memory.used",
    "--format=csv,noheader,nounits",
]


def query_vram_used_mib(
    *,
    gpu_index: int = 0,
    runner: CommandRunner = subprocess.run,
) -> int | None:
    """Return used VRAM in MiB for ``gpu_index``, or ``None`` if unavailable."""
    try:
        result = runner(
            _NVIDIA_SMI_ARGS,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        _LOG.debug("nvidia-smi not found; skipping VRAM capture")
        return None
    except (OSError, subprocess.SubprocessError) as exc:
        _LOG.debug("nvidia-smi failed to run: %s", exc)
        return None

    if getattr(result, "returncode", 1) != 0:
        _LOG.debug("nvidia-smi returned non-zero exit code")
        return None

    lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    if gpu_index >= len(lines):
        _LOG.debug("gpu_index %d out of range (%d GPUs)", gpu_index, len(lines))
        return None

    try:
        return int(lines[gpu_index])
    except ValueError:
        _LOG.debug("could not parse nvidia-smi output: %r", lines[gpu_index])
        return None


__all__ = ["query_vram_used_mib"]
