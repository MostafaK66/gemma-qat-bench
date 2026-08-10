"""Tests for :mod:`gemma_qat_bench.build`."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from gemma_qat_bench.build import LlamaCppBuilder
from gemma_qat_bench.config import BuildConfig
from gemma_qat_bench.exceptions import BuildError


class RecordingRunner:
    """Records commands; optionally materialises the server binary on build."""

    def __init__(self, *, returncode: int = 0, server_binary: Path | None = None):
        self.commands: list[list[str]] = []
        self._returncode = returncode
        self._server_binary = server_binary

    def __call__(self, command, *args, **kwargs):
        self.commands.append(list(command))
        # Simulate a successful build producing the binary.
        if self._server_binary is not None and command[:2] == ["cmake", "--build"]:
            self._server_binary.parent.mkdir(parents=True, exist_ok=True)
            self._server_binary.write_bytes(b"\x7fELF")
        return subprocess.CompletedProcess(command, self._returncode)


# -- command builders ------------------------------------------------------- #


def test_clone_command():
    cfg = BuildConfig(source_dir="third_party/llama.cpp")
    cmd = LlamaCppBuilder(cfg).clone_command()
    assert cmd[:3] == ["git", "clone", "--depth"]
    assert Path(cmd[-1]) == Path("third_party/llama.cpp")
    assert cfg.repo_url in cmd


def test_configure_command_toggles_cuda():
    cfg = BuildConfig(source_dir="src", build_dir="build")
    builder = LlamaCppBuilder(cfg)
    on = builder.configure_command(use_cuda=True)
    off = builder.configure_command(use_cuda=False)
    assert "-DGGML_CUDA=ON" in on
    assert "-DGGML_CUDA=OFF" in off
    assert "-DBUILD_SHARED_LIBS=OFF" in on
    assert on[builder.configure_command(True).index("-B") + 1] == "build"


def test_build_command_includes_targets_and_jobs():
    cfg = BuildConfig(source_dir="src", jobs=8, targets=("llama-server", "llama-cli"))
    cmd = LlamaCppBuilder(cfg).build_command()
    assert cmd[:2] == ["cmake", "--build"]
    assert cmd[cmd.index("-j") + 1] == "8"
    assert "--clean-first" in cmd
    assert "--target" in cmd
    assert cmd[-2:] == ["llama-server", "llama-cli"]


def test_build_command_without_clean_first():
    cfg = BuildConfig(source_dir="src", clean_first=False)
    cmd = LlamaCppBuilder(cfg).build_command()
    assert "--clean-first" not in cmd


# -- cuda resolution -------------------------------------------------------- #


def test_resolve_cuda_explicit_wins_over_detector():
    cfg_on = BuildConfig(source_dir="s", use_cuda=True)
    cfg_off = BuildConfig(source_dir="s", use_cuda=False)
    assert LlamaCppBuilder(cfg_on, cuda_detector=lambda: False).resolve_cuda() is True
    assert LlamaCppBuilder(cfg_off, cuda_detector=lambda: True).resolve_cuda() is False


def test_resolve_cuda_auto_uses_detector():
    cfg = BuildConfig(source_dir="s")  # use_cuda=None
    assert LlamaCppBuilder(cfg, cuda_detector=lambda: True).resolve_cuda() is True
    assert LlamaCppBuilder(cfg, cuda_detector=lambda: False).resolve_cuda() is False


# -- server_binary resolution ---------------------------------------------- #


def test_server_binary_found_in_bin(tmp_path):
    cfg = BuildConfig(source_dir=tmp_path / "src", build_dir=tmp_path / "build")
    (tmp_path / "build" / "bin").mkdir(parents=True)
    binary = tmp_path / "build" / "bin" / "llama-server"
    binary.write_bytes(b"x")
    assert LlamaCppBuilder(cfg).server_binary() == binary


def test_server_binary_found_in_build_root(tmp_path):
    cfg = BuildConfig(source_dir=tmp_path / "src", build_dir=tmp_path / "build")
    (tmp_path / "build").mkdir(parents=True)
    binary = tmp_path / "build" / "llama-server"
    binary.write_bytes(b"x")
    assert LlamaCppBuilder(cfg).server_binary() == binary


def test_server_binary_missing_raises(tmp_path):
    cfg = BuildConfig(source_dir=tmp_path / "src", build_dir=tmp_path / "build")
    with pytest.raises(BuildError):
        LlamaCppBuilder(cfg).server_binary()


# -- build driver ----------------------------------------------------------- #


def test_build_runs_all_steps_and_returns_binary(tmp_path):
    src = tmp_path / "src"  # does not exist -> clone runs
    build_dir = tmp_path / "build"
    binary = build_dir / "bin" / "llama-server"
    cfg = BuildConfig(source_dir=src, build_dir=build_dir, use_cuda=False)
    runner = RecordingRunner(server_binary=binary)

    result = LlamaCppBuilder(cfg, runner=runner, cuda_detector=lambda: False).build()

    assert result == binary
    verbs = [c[0] for c in runner.commands]
    assert verbs == ["git", "cmake", "cmake"]  # clone, configure, build


def test_build_skips_clone_when_source_exists(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    build_dir = tmp_path / "build"
    binary = build_dir / "bin" / "llama-server"
    cfg = BuildConfig(source_dir=src, build_dir=build_dir, use_cuda=False)
    runner = RecordingRunner(server_binary=binary)

    LlamaCppBuilder(cfg, runner=runner).build()
    assert [c[0] for c in runner.commands] == ["cmake", "cmake"]  # no git clone


def test_run_raises_on_nonzero_returncode(tmp_path):
    cfg = BuildConfig(source_dir=tmp_path / "src", use_cuda=False)
    runner = RecordingRunner(returncode=1)
    with pytest.raises(BuildError):
        LlamaCppBuilder(cfg, runner=runner).build()


def test_run_raises_on_missing_command(tmp_path):
    cfg = BuildConfig(source_dir=tmp_path / "src", use_cuda=False)

    def missing(command, *args, **kwargs):
        raise FileNotFoundError(command[0])

    with pytest.raises(BuildError):
        LlamaCppBuilder(cfg, runner=missing).build()
