"""Tests for :mod:`gemma_qat_bench.models`."""

from __future__ import annotations

import pytest

from gemma_qat_bench.config import ModelSpec
from gemma_qat_bench.exceptions import ModelDownloadError
from gemma_qat_bench.models import ModelManager


def _spec(local_dir) -> ModelSpec:
    return ModelSpec(
        key="m",
        display_name="Model",
        repo_id="org/model",
        local_dir=local_dir,
    )


def test_ensure_skips_download_when_present(tmp_path, make_gguf):
    spec = _spec(tmp_path)
    gguf = make_gguf(tmp_path, "model-UD-Q4_K_XL.gguf")

    def forbidden(*_a, **_k):
        raise AssertionError("downloader should not be called")

    result = ModelManager(downloader=forbidden).ensure(spec)
    assert result == gguf


def test_ensure_downloads_when_missing(tmp_path):
    spec = _spec(tmp_path / "dl")
    recorded = {}

    def fake_downloader(repo_id, local_dir, allow_patterns):
        recorded["repo_id"] = repo_id
        recorded["local_dir"] = local_dir
        recorded["allow_patterns"] = allow_patterns
        # Produce the expected weight file.
        target = spec.local_dir / "model-UD-Q4_K_XL.gguf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"GGUF")
        return str(spec.local_dir)

    result = ModelManager(downloader=fake_downloader).ensure(spec)
    assert result.name == "model-UD-Q4_K_XL.gguf"
    assert recorded["repo_id"] == "org/model"
    assert recorded["allow_patterns"] == list(spec.include_patterns)


def test_ensure_wraps_downloader_errors(tmp_path):
    spec = _spec(tmp_path / "dl")

    def failing(*_a, **_k):
        raise RuntimeError("network down")

    with pytest.raises(ModelDownloadError) as exc:
        ModelManager(downloader=failing).ensure(spec)
    assert "network down" in str(exc.value)


def test_ensure_raises_when_download_produces_no_gguf(tmp_path):
    spec = _spec(tmp_path / "dl")

    def empty_downloader(repo_id, local_dir, allow_patterns):
        return local_dir  # creates nothing

    with pytest.raises(ModelDownloadError):
        ModelManager(downloader=empty_downloader).ensure(spec)
