"""Tests for :mod:`gemma_qat_bench.report`."""

from pathlib import Path

import pytest

from conftest import chat_response
from gemma_qat_bench import report as report_module
from gemma_qat_bench.config import AppConfig, ModelSpec
from gemma_qat_bench.metrics import AggregatedMetrics, RunMetrics
from gemma_qat_bench.report import BenchmarkReport, ComparisonSummary


def test_report_module_uses_explicit_string_annotations():
    source = Path(report_module.__file__).read_text(encoding="utf-8")
    assert "from __future__ import annotations" not in source

    assert ComparisonSummary.__annotations__["baseline_key"] == "str"
    assert ComparisonSummary.__annotations__["vram_saved_pct"] == "float | None"

    from_pair_annotations = ComparisonSummary.from_pair.__annotations__
    assert from_pair_annotations == {
        "baseline": "AggregatedMetrics",
        "qat": "AggregatedMetrics",
        "return": "ComparisonSummary",
    }

    assert BenchmarkReport.__annotations__["results"] == "tuple[AggregatedMetrics, ...]"
    assert BenchmarkReport.__annotations__["created_at"] == "str"

    build_annotations = BenchmarkReport.build.__annotations__
    assert build_annotations["results"] == "Sequence[AggregatedMetrics]"
    assert build_annotations["config"] == "AppConfig"
    assert build_annotations["quantization"] == "str"
    assert build_annotations["created_at"] == "str | None"
    assert build_annotations["return"] == "BenchmarkReport"


def _agg(
    key: str,
    *,
    is_qat: bool,
    gen_per_s: float,
    vram: int | None,
    wall: float = 5.0,
) -> AggregatedMetrics:
    spec = ModelSpec(
        key=key,
        display_name=f"Model {key}",
        repo_id=f"org/{key}",
        local_dir="d",
        is_qat=is_qat,
    )
    run = RunMetrics.from_response(chat_response(gen_per_s=gen_per_s), wall)
    return AggregatedMetrics.from_runs(spec, [run], vram_used_mib=vram)


# -- ComparisonSummary ------------------------------------------------------ #


def test_comparison_matches_tutorial_numbers():
    baseline = _agg("non-qat", is_qat=False, gen_per_s=94.65, vram=9247)
    qat = _agg("qat", is_qat=True, gen_per_s=101.65, vram=8627)
    summary = ComparisonSummary.from_pair(baseline, qat)

    # ~7.4% faster generation and 620 MiB / ~6.7% less VRAM, per the article.
    assert summary.gen_speedup_pct == pytest.approx(7.4, abs=0.1)
    assert summary.vram_saved_mib == 620
    assert summary.vram_saved_pct == pytest.approx(6.7, abs=0.1)


def test_comparison_handles_missing_vram():
    baseline = _agg("non-qat", is_qat=False, gen_per_s=90.0, vram=None)
    qat = _agg("qat", is_qat=True, gen_per_s=100.0, vram=None)
    summary = ComparisonSummary.from_pair(baseline, qat)
    assert summary.vram_saved_mib is None
    assert summary.vram_saved_pct is None


# -- BenchmarkReport -------------------------------------------------------- #


def _report() -> BenchmarkReport:
    config = AppConfig.tutorial_default()
    results = [
        _agg("non-qat", is_qat=False, gen_per_s=94.65, vram=9247),
        _agg("qat", is_qat=True, gen_per_s=101.65, vram=8627),
    ]
    return BenchmarkReport.build(results, config)


def test_report_pairs_baseline_and_qat():
    summary = _report().comparison
    assert summary is not None
    assert summary.baseline_key == "non-qat"
    assert summary.qat_key == "qat"


def test_report_comparison_none_without_qat():
    config = AppConfig.tutorial_default()
    results = [_agg("a", is_qat=False, gen_per_s=90.0, vram=None)]
    assert BenchmarkReport.build(results, config).comparison is None


def test_to_json_dict_structure():
    data = _report().to_json_dict()
    assert set(data) >= {"created_at", "prompt", "results", "comparison"}
    assert len(data["results"]) == 2
    assert data["comparison"]["qat_key"] == "qat"
    # Nested runs carry derived fields.
    assert "effective_gen_per_s" in data["results"][0]["runs"][0]


def test_to_markdown_contains_names_and_numbers():
    md = _report().to_markdown()
    assert "Model qat" in md  # display name from the _agg helper
    assert "101.65" in md
    assert "Comparison" in md


def test_to_console_contains_headers():
    text = _report().to_console()
    assert "Gen tok/s" in text
    assert "VRAM MiB" in text
    assert "Comparison" in text
