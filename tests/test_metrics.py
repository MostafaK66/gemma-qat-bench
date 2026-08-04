"""Tests for :mod:`gemma_qat_bench.metrics`."""

from __future__ import annotations

import pytest

from gemma_qat_bench.config import ModelSpec
from gemma_qat_bench.metrics import AggregatedMetrics, RunMetrics

from conftest import chat_response


def _spec(is_qat: bool = False) -> ModelSpec:
    return ModelSpec(
        key="qat" if is_qat else "non-qat",
        display_name="Model",
        repo_id="org/model",
        local_dir="models/model",
        is_qat=is_qat,
    )


# -- RunMetrics.from_response ----------------------------------------------- #


def test_from_response_reads_usage_and_timings():
    payload = chat_response(prompt_tokens=40, completion_tokens=512, gen_per_s=94.65)
    run = RunMetrics.from_response(payload, wall_time_s=5.5)
    assert run.prompt_tokens == 40
    assert run.completion_tokens == 512
    assert run.total_tokens == 552
    assert run.server_gen_per_s == 94.65
    assert run.effective_gen_per_s == 94.65  # server value preferred


def test_from_response_falls_back_to_wall_clock_without_timings():
    payload = chat_response(completion_tokens=100, include_timings=False)
    run = RunMetrics.from_response(payload, wall_time_s=2.0)
    assert run.server_gen_per_s is None
    assert run.wall_gen_per_s == pytest.approx(50.0)
    assert run.effective_gen_per_s == pytest.approx(50.0)


def test_from_response_prefers_content_but_falls_back_to_reasoning():
    with_content = chat_response(content="visible answer")
    assert RunMetrics.from_response(with_content, 1.0).response_text == "visible answer"

    only_reasoning = chat_response(content="", reasoning_content="hidden chain")
    assert RunMetrics.from_response(only_reasoning, 1.0).response_text == "hidden chain"


def test_from_response_handles_no_choices():
    run = RunMetrics.from_response({}, wall_time_s=1.0)
    assert run.response_text == ""
    assert run.completion_tokens == 0


def test_wall_gen_per_s_zero_when_no_time():
    payload = chat_response(completion_tokens=100, include_timings=False)
    assert RunMetrics.from_response(payload, wall_time_s=0.0).wall_gen_per_s == 0.0


# -- AggregatedMetrics ------------------------------------------------------ #


def test_aggregate_computes_mean_median_stdev():
    runs = [
        RunMetrics.from_response(chat_response(gen_per_s=90.0), 1.0),
        RunMetrics.from_response(chat_response(gen_per_s=100.0), 1.0),
        RunMetrics.from_response(chat_response(gen_per_s=110.0), 1.0),
    ]
    agg = AggregatedMetrics.from_runs(_spec(), runs)
    assert agg.n_runs == 3
    assert agg.mean_gen_per_s == pytest.approx(100.0)
    assert agg.median_gen_per_s == pytest.approx(100.0)
    assert agg.stdev_gen_per_s == pytest.approx(10.0)


def test_aggregate_single_run_has_zero_stdev():
    runs = [RunMetrics.from_response(chat_response(gen_per_s=95.0), 1.0)]
    agg = AggregatedMetrics.from_runs(_spec(is_qat=True), runs, vram_used_mib=8627)
    assert agg.stdev_gen_per_s == 0.0
    assert agg.is_qat is True
    assert agg.vram_used_mib == 8627


def test_aggregate_token_counts_from_last_run():
    runs = [
        RunMetrics.from_response(chat_response(completion_tokens=10), 1.0),
        RunMetrics.from_response(chat_response(completion_tokens=512), 1.0),
    ]
    agg = AggregatedMetrics.from_runs(_spec(), runs)
    assert agg.completion_tokens == 512


def test_aggregate_empty_runs_raises():
    with pytest.raises(ValueError):
        AggregatedMetrics.from_runs(_spec(), [])
