"""Tests for :mod:`gemma_qat_bench.config`."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemma_qat_bench.config import (
    AppConfig,
    BenchmarkConfig,
    BuildConfig,
    ModelSpec,
    SamplingConfig,
    ServerConfig,
)
from gemma_qat_bench.exceptions import ConfigError, ModelDownloadError

# -- SamplingConfig --------------------------------------------------------- #


def test_sampling_defaults_are_valid():
    cfg = SamplingConfig()
    assert cfg.temperature == 1.0
    assert cfg.top_p == 0.95
    assert cfg.top_k == 64
    assert cfg.max_tokens == 512


@pytest.mark.parametrize(
    "kwargs",
    [
        {"temperature": -0.1},
        {"top_p": 0.0},
        {"top_p": 1.5},
        {"top_k": -1},
        {"max_tokens": 0},
    ],
)
def test_sampling_rejects_invalid(kwargs):
    with pytest.raises(ConfigError):
        SamplingConfig(**kwargs)


def test_sampling_extra_body_is_copied_to_plain_dict():
    source = {"chat_template_kwargs": {"thinking": False}}
    cfg = SamplingConfig(extra_body=source)
    assert cfg.extra_body == source
    assert cfg.extra_body is not source  # defensively copied


# -- ServerConfig ----------------------------------------------------------- #


def test_server_base_url_translates_wildcard_host():
    assert ServerConfig(host="0.0.0.0", port=8001).base_url == "http://127.0.0.1:8001"
    assert ServerConfig(host="::", port=9).base_url == "http://127.0.0.1:9"


def test_server_base_url_keeps_explicit_host():
    assert ServerConfig(host="1.2.3.4", port=80).base_url == "http://1.2.3.4:80"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"port": 0},
        {"port": 70000},
        {"ctx_size": 0},
        {"n_gpu_layers": -1},
        {"startup_timeout_s": 0},
        {"health_poll_interval_s": 0},
    ],
)
def test_server_rejects_invalid(kwargs):
    with pytest.raises(ConfigError):
        ServerConfig(**kwargs)


def test_server_binary_path_coerced_to_path():
    cfg = ServerConfig(binary_path="some/dir/llama-server")
    assert isinstance(cfg.binary_path, Path)


# -- ModelSpec -------------------------------------------------------------- #


def test_model_spec_rejects_empty_fields():
    with pytest.raises(ConfigError):
        ModelSpec(key="", display_name="x", repo_id="r", local_dir="d")


def test_resolve_gguf_finds_single_file(tmp_path, make_gguf):
    spec = ModelSpec(key="m", display_name="M", repo_id="r", local_dir=tmp_path)
    gguf = make_gguf(tmp_path, "model-UD-Q4_K_XL.gguf")
    assert spec.resolve_gguf() == gguf


def test_resolve_gguf_excludes_mmproj(tmp_path, make_gguf):
    spec = ModelSpec(
        key="m",
        display_name="M",
        repo_id="r",
        local_dir=tmp_path,
        gguf_pattern="*.gguf",
    )
    make_gguf(tmp_path, "mmproj-BF16.gguf")
    weight = make_gguf(tmp_path, "model-UD-Q4_K_XL.gguf")
    assert spec.resolve_gguf() == weight


def test_resolve_gguf_prefers_first_shard(tmp_path, make_gguf):
    spec = ModelSpec(key="m", display_name="M", repo_id="r", local_dir=tmp_path)
    make_gguf(tmp_path, "model-UD-Q4_K_XL-00002-of-00002.gguf")
    first = make_gguf(tmp_path, "model-UD-Q4_K_XL-00001-of-00002.gguf")
    assert spec.resolve_gguf() == first


def test_resolve_gguf_missing_raises(tmp_path):
    spec = ModelSpec(key="m", display_name="M", repo_id="r", local_dir=tmp_path)
    with pytest.raises(ModelDownloadError):
        spec.resolve_gguf()


# -- BuildConfig ------------------------------------------------------------ #


def test_build_default_build_dir():
    cfg = BuildConfig(source_dir="third_party/llama.cpp")
    assert cfg.resolved_build_dir == Path("third_party/llama.cpp/build")


def test_build_explicit_build_dir():
    cfg = BuildConfig(source_dir="a", build_dir="b/out")
    assert cfg.resolved_build_dir == Path("b/out")


@pytest.mark.parametrize("kwargs", [{"jobs": 0}, {"targets": ()}, {"repo_url": "  "}])
def test_build_rejects_invalid(kwargs):
    with pytest.raises(ConfigError):
        BuildConfig(**kwargs)


# -- BenchmarkConfig -------------------------------------------------------- #


@pytest.mark.parametrize(
    "kwargs",
    [{"n_runs": 0}, {"warmup_runs": -1}, {"prompt": "   "}, {"request_timeout_s": 0}],
)
def test_benchmark_rejects_invalid(kwargs):
    with pytest.raises(ConfigError):
        BenchmarkConfig(**kwargs)


# -- AppConfig -------------------------------------------------------------- #


def test_tutorial_default_uses_corrected_repo_ids():
    cfg = AppConfig.tutorial_default()
    by_key = {m.key: m for m in cfg.models}
    # Non-QAT repo id uses lowercase 'b' (the tutorial's capital-B is wrong).
    assert by_key["non-qat"].repo_id == "unsloth/gemma-4-12b-it-GGUF"
    assert by_key["non-qat"].is_qat is False
    assert by_key["qat"].repo_id == "unsloth/gemma-4-12B-it-qat-GGUF"
    assert by_key["qat"].is_qat is True


def test_app_config_rejects_duplicate_keys():
    m = ModelSpec(key="dup", display_name="A", repo_id="r", local_dir="d")
    m2 = ModelSpec(key="dup", display_name="B", repo_id="r2", local_dir="d2")
    with pytest.raises(ConfigError):
        AppConfig(models=(m, m2))


def test_app_config_rejects_empty_models():
    with pytest.raises(ConfigError):
        AppConfig(models=())


def test_from_toml_round_trip(tmp_path):
    toml = """
    models_root = "models"
    results_dir = "out"
    capture_vram = false

    [server]
    binary_path = "bin/llama-server"
    host = "0.0.0.0"
    port = 9000
    ctx_size = 4096

    [sampling]
    temperature = 0.7
    max_tokens = 128

    [benchmark]
    n_runs = 5
    warmup_runs = 2

    [build]
    use_cuda = false
    jobs = 4

    [[models]]
    key = "a"
    display_name = "Model A"
    repo_id = "org/a"
    local_dir = "models/a"
    is_qat = false

    [[models]]
    key = "b"
    display_name = "Model B"
    repo_id = "org/b"
    local_dir = "models/b"
    is_qat = true
    """
    path = tmp_path / "config.toml"
    path.write_text(toml, encoding="utf-8")

    cfg = AppConfig.from_toml(path)
    assert cfg.capture_vram is False
    assert cfg.results_dir == Path("out")
    assert cfg.server.port == 9000
    assert cfg.server.ctx_size == 4096
    assert cfg.sampling.temperature == 0.7
    assert cfg.sampling.max_tokens == 128
    assert cfg.benchmark.n_runs == 5
    assert cfg.benchmark.warmup_runs == 2
    assert cfg.build.use_cuda is False
    assert cfg.build.jobs == 4
    assert [m.key for m in cfg.models] == ["a", "b"]
    assert cfg.models[1].is_qat is True


def test_from_toml_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        AppConfig.from_toml(tmp_path / "nope.toml")


def test_from_toml_invalid_syntax_raises(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text("this is = = not toml", encoding="utf-8")
    with pytest.raises(ConfigError):
        AppConfig.from_toml(path)


def test_from_mapping_requires_models():
    with pytest.raises(ConfigError):
        AppConfig.from_mapping({"server": {}})
