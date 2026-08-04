"""End-to-end tests for :mod:`gemma_qat_bench.benchmark` (no I/O)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from gemma_qat_bench.benchmark import BenchmarkRunner
from gemma_qat_bench.config import AppConfig, BenchmarkConfig

from conftest import FakeChatClient, FakeServer, chat_response


class FakeModelManager:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def ensure(self, spec) -> Path:
        self.calls.append(spec.key)
        return Path(f"models/{spec.key}.gguf")


def _config(*, n_runs: int = 2, warmup_runs: int = 1, capture_vram: bool = True) -> AppConfig:
    base = AppConfig.tutorial_default()
    return replace(
        base,
        benchmark=replace(
            BenchmarkConfig(), n_runs=n_runs, warmup_runs=warmup_runs
        ),
        capture_vram=capture_vram,
    )


def _runner(config, *, clients, servers, vram_values):
    client_iter = iter(clients)
    vram_iter = iter(vram_values)

    def client_factory(base_url, timeout):
        return next(client_iter)

    def server_factory(server_config, gguf):
        server = FakeServer()
        servers.append(server)
        return server

    def vram_sampler():
        return next(vram_iter)

    mm = FakeModelManager()
    runner = BenchmarkRunner(
        config,
        model_manager=mm,
        server_factory=server_factory,
        client_factory=client_factory,
        vram_sampler=vram_sampler,
    )
    return runner, mm


def test_full_run_produces_expected_report():
    config = _config(n_runs=2, warmup_runs=1)
    clients = [
        FakeChatClient(chat_response(gen_per_s=94.65)),
        FakeChatClient(chat_response(gen_per_s=101.65)),
    ]
    servers: list[FakeServer] = []
    runner, mm = _runner(
        config, clients=clients, servers=servers, vram_values=[9247, 8627]
    )

    report = runner.run()

    # Two models benchmarked in declared order.
    assert mm.calls == ["non-qat", "qat"]
    assert [r.model_key for r in report.results] == ["non-qat", "qat"]

    non_qat, qat = report.results
    assert non_qat.mean_gen_per_s == pytest.approx(94.65)
    assert non_qat.vram_used_mib == 9247
    assert qat.mean_gen_per_s == pytest.approx(101.65)
    assert qat.vram_used_mib == 8627

    # Comparison reflects the QAT gains.
    summary = report.comparison
    assert summary is not None
    assert summary.gen_speedup_pct == pytest.approx(7.4, abs=0.1)
    assert summary.vram_saved_mib == 620

    # Warmup + measured runs all executed against each client.
    assert clients[0].calls == 3  # 1 warmup + 2 measured
    assert clients[1].calls == 3

    # Each server context entered and exited.
    assert len(servers) == 2
    assert all(s.entered and s.exited for s in servers)


def test_no_warmup_runs_only_measured_calls():
    config = _config(n_runs=3, warmup_runs=0)
    clients = [FakeChatClient(chat_response()), FakeChatClient(chat_response())]
    servers: list[FakeServer] = []
    runner, _ = _runner(
        config, clients=clients, servers=servers, vram_values=[100, 90]
    )

    runner.run()
    assert clients[0].calls == 3
    assert clients[1].calls == 3


def test_capture_vram_disabled_skips_sampler():
    config = _config(capture_vram=False)
    clients = [FakeChatClient(chat_response()), FakeChatClient(chat_response())]
    servers: list[FakeServer] = []

    def exploding_sampler():
        raise AssertionError("vram sampler must not be called when disabled")

    runner = BenchmarkRunner(
        config,
        model_manager=FakeModelManager(),
        server_factory=lambda cfg, gguf: servers.append(FakeServer()) or servers[-1],
        client_factory=lambda url, timeout: clients.pop(0),
        vram_sampler=exploding_sampler,
    )

    report = runner.run()
    assert all(r.vram_used_mib is None for r in report.results)
