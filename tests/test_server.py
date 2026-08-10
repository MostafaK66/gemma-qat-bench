"""Tests for :mod:`gemma_qat_bench.server`."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemma_qat_bench.config import ServerConfig
from gemma_qat_bench.exceptions import ServerStartupError
from gemma_qat_bench.server import ServerManager

from conftest import FakeHealthClient, FakeProcess, SequenceClock


def _manager(
    *,
    config: ServerConfig | None = None,
    process: FakeProcess | None = None,
    health: list[bool] | None = None,
    clock: SequenceClock | None = None,
) -> tuple[ServerManager, FakeProcess]:
    config = config or ServerConfig(binary_path="bin/llama-server", port=8001)
    process = process or FakeProcess(poll_results=[None])
    health_client = FakeHealthClient(health if health is not None else [True])
    manager = ServerManager(
        config,
        Path("models/model.gguf"),
        process_factory=lambda _cmd: process,
        client_factory=lambda _url: health_client,
        sleep=lambda _s: None,
        monotonic=clock or SequenceClock([0.0, 0.0, 1.0, 2.0, 3.0, 4.0]),
    )
    return manager, process


# -- build_command ---------------------------------------------------------- #


def test_build_command_contains_all_flags():
    config = ServerConfig(
        binary_path="bin/llama-server",
        host="0.0.0.0",
        port=8001,
        ctx_size=8192,
        n_gpu_layers=99,
        extra_args=("--flash-attn", "on"),
    )
    manager = ServerManager(config, Path("m.gguf"))
    cmd = manager.build_command()
    assert Path(cmd[0]) == Path("bin/llama-server")
    assert cmd[cmd.index("-m") + 1] == "m.gguf"
    assert cmd[cmd.index("--host") + 1] == "0.0.0.0"
    assert cmd[cmd.index("--port") + 1] == "8001"
    assert cmd[cmd.index("--ctx-size") + 1] == "8192"
    assert cmd[cmd.index("--n-gpu-layers") + 1] == "99"
    assert cmd[-2:] == ["--flash-attn", "on"]


# -- start / health --------------------------------------------------------- #


def test_start_waits_for_health_then_ready():
    manager, process = _manager(
        process=FakeProcess(poll_results=[None]),
        health=[False, False, True],
    )
    manager.start()
    assert manager.base_url == "http://127.0.0.1:8001"
    manager.stop()
    assert process.terminated is True


def test_start_raises_if_process_exits_before_healthy():
    manager, _ = _manager(
        process=FakeProcess(poll_results=[7]),  # exited with code 7
        health=[False],
    )
    with pytest.raises(ServerStartupError) as exc:
        manager.start()
    assert "7" in str(exc.value)


def test_start_times_out_and_stops_process():
    process = FakeProcess(poll_results=[None])
    manager, _ = _manager(
        config=ServerConfig(binary_path="bin/llama-server", startup_timeout_s=2.0),
        process=process,
        health=[False],
        clock=SequenceClock([0.0, 0.0, 1.0, 2.0]),
    )
    with pytest.raises(ServerStartupError) as exc:
        manager.start()
    assert "healthy" in str(exc.value)
    assert process.terminated is True


def test_start_twice_raises():
    manager, _ = _manager(health=[True])
    manager.start()
    with pytest.raises(ServerStartupError):
        manager.start()


# -- stop ------------------------------------------------------------------- #


def test_stop_is_idempotent_when_not_started():
    manager, _ = _manager()
    manager.stop()  # should not raise


def test_stop_kills_process_when_terminate_times_out():
    process = FakeProcess(poll_results=[None], wait_raises_once=True)
    manager, _ = _manager(process=process, health=[True])
    manager.start()
    manager.stop()
    assert process.terminated is True
    assert process.killed is True


# -- context manager -------------------------------------------------------- #


def test_context_manager_starts_and_stops():
    process = FakeProcess(poll_results=[None])
    manager, _ = _manager(process=process, health=[True])
    with manager as running:
        assert running is manager
    assert process.terminated is True
