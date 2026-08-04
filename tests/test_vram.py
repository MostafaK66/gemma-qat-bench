"""Tests for :mod:`gemma_qat_bench.vram`."""

from __future__ import annotations

import subprocess

from gemma_qat_bench.vram import query_vram_used_mib


def _runner(stdout: str = "", returncode: int = 0, exc: Exception | None = None):
    def run(args, *a, **k):
        if exc is not None:
            raise exc
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")

    return run


def test_parses_single_gpu():
    assert query_vram_used_mib(runner=_runner(stdout="8627\n")) == 8627


def test_selects_requested_gpu_index():
    runner = _runner(stdout="1000\n2000\n3000\n")
    assert query_vram_used_mib(gpu_index=2, runner=runner) == 3000


def test_returns_none_when_nvidia_smi_missing():
    assert query_vram_used_mib(runner=_runner(exc=FileNotFoundError())) is None


def test_returns_none_on_nonzero_exit():
    assert query_vram_used_mib(runner=_runner(returncode=9, stdout="x")) is None


def test_returns_none_on_unparseable_output():
    assert query_vram_used_mib(runner=_runner(stdout="N/A\n")) is None


def test_returns_none_when_gpu_index_out_of_range():
    assert query_vram_used_mib(gpu_index=5, runner=_runner(stdout="100\n")) is None
