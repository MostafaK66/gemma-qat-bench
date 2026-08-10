"""Tests for :mod:`gemma_qat_bench.cli`."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import chat_response
from gemma_qat_bench import cli
from gemma_qat_bench.config import AppConfig, ModelSpec
from gemma_qat_bench.metrics import AggregatedMetrics, RunMetrics
from gemma_qat_bench.report import BenchmarkReport


def _parse(argv):
    return cli.build_parser().parse_args(argv)


# -- parsing ---------------------------------------------------------------- #


def test_parser_requires_a_command(capsys):
    import pytest

    with pytest.raises(SystemExit):
        _parse([])


def test_parser_accepts_known_commands():
    for command in ("build", "download", "bench", "all"):
        assert _parse([command]).command == command


# -- config resolution ------------------------------------------------------ #


def test_resolve_default_is_tutorial_config():
    config = cli.resolve_config(_parse(["bench"]))
    assert isinstance(config, AppConfig)
    assert [m.key for m in config.models] == ["non-qat", "qat"]
    assert config.benchmark.n_runs == 3  # untouched default


def test_resolve_applies_bench_overrides():
    args = _parse(
        ["bench", "--runs", "5", "--warmup", "0", "--no-vram",
         "--server-binary", "/opt/llama-server", "--out", "results2"]
    )
    config = cli.resolve_config(args)
    assert config.benchmark.n_runs == 5
    assert config.benchmark.warmup_runs == 0
    assert config.capture_vram is False
    assert config.server.binary_path == Path("/opt/llama-server")
    assert config.results_dir == Path("results2")


def test_resolve_applies_build_overrides():
    config = cli.resolve_config(_parse(["build", "--no-cuda", "--jobs", "2"]))
    assert config.build.use_cuda is False
    assert config.build.jobs == 2


def test_resolve_from_config_file(tmp_path):
    toml = """
    [[models]]
    key = "solo"
    display_name = "Solo"
    repo_id = "org/solo"
    local_dir = "models/solo"
    """
    path = tmp_path / "c.toml"
    path.write_text(toml, encoding="utf-8")
    config = cli.resolve_config(_parse(["--config", str(path), "bench"]))
    assert [m.key for m in config.models] == ["solo"]


# -- report emission -------------------------------------------------------- #


def _sample_report() -> BenchmarkReport:
    config = AppConfig.tutorial_default()
    spec = ModelSpec(
        key="qat", display_name="QAT", repo_id="org/qat", local_dir="d", is_qat=True
    )
    run = RunMetrics.from_response(chat_response(gen_per_s=101.65), 5.0)
    agg = AggregatedMetrics.from_runs(spec, [run], vram_used_mib=8627)
    return BenchmarkReport.build([agg], config)


def test_emit_report_writes_json_and_markdown(tmp_path, capsys):
    cli._emit_report(_sample_report(), tmp_path)

    json_files = list(tmp_path.glob("benchmark-*.json"))
    md_files = list(tmp_path.glob("benchmark-*.md"))
    assert len(json_files) == 1
    assert len(md_files) == 1

    data = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert data["results"][0]["model_key"] == "qat"
