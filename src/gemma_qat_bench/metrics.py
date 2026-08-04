"""Performance metrics captured from ``llama-server`` responses.

Two levels of metric are modelled:

* :class:`RunMetrics` -- one request/response pair;
* :class:`AggregatedMetrics` -- mean/median/spread over several runs for a model.

Token counts come from the standard OpenAI ``usage`` block. Throughput prefers
``llama.cpp``'s non-standard ``timings`` block (the numbers the tutorial quotes)
and falls back to wall-clock throughput when it is absent, so the tool still
works against a strictly OpenAI-compatible backend.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .config import ModelSpec


def _extract_text(payload: Mapping[str, Any]) -> str:
    """Best-effort extraction of assistant text from a chat completion.

    Falls back to ``reasoning_content`` because Gemma 4 is a thinking model: with
    reasoning enabled the visible answer can live there while ``content`` is
    empty.
    """
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if content:
        return str(content)
    reasoning = message.get("reasoning_content")
    return str(reasoning) if reasoning else ""


@dataclass(frozen=True, slots=True)
class RunMetrics:
    """Metrics for a single benchmarked request."""

    prompt_tokens: int
    completion_tokens: int
    wall_time_s: float
    server_prompt_per_s: float | None
    server_gen_per_s: float | None
    response_text: str

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def wall_gen_per_s(self) -> float:
        """Completion tokens per second measured by the client wall clock."""
        if self.wall_time_s <= 0:
            return 0.0
        return self.completion_tokens / self.wall_time_s

    @property
    def effective_gen_per_s(self) -> float:
        """Server-reported generation speed if available, else wall-clock."""
        if self.server_gen_per_s is not None:
            return self.server_gen_per_s
        return self.wall_gen_per_s

    @classmethod
    def from_response(
        cls, payload: Mapping[str, Any], wall_time_s: float
    ) -> "RunMetrics":
        usage = payload.get("usage") or {}
        timings = payload.get("timings") or {}
        return cls(
            prompt_tokens=int(
                usage.get("prompt_tokens", timings.get("prompt_n", 0)) or 0
            ),
            completion_tokens=int(
                usage.get("completion_tokens", timings.get("predicted_n", 0)) or 0
            ),
            wall_time_s=float(wall_time_s),
            server_prompt_per_s=_opt_float(timings.get("prompt_per_second")),
            server_gen_per_s=_opt_float(timings.get("predicted_per_second")),
            response_text=_extract_text(payload),
        )


@dataclass(frozen=True, slots=True)
class AggregatedMetrics:
    """Aggregate of several :class:`RunMetrics` for one model variant."""

    model_key: str
    display_name: str
    is_qat: bool
    n_runs: int
    mean_gen_per_s: float
    median_gen_per_s: float
    stdev_gen_per_s: float
    mean_prompt_per_s: float
    mean_wall_time_s: float
    prompt_tokens: int
    completion_tokens: int
    vram_used_mib: int | None
    runs: tuple[RunMetrics, ...]

    @classmethod
    def from_runs(
        cls,
        spec: ModelSpec,
        runs: Sequence[RunMetrics],
        *,
        vram_used_mib: int | None = None,
    ) -> "AggregatedMetrics":
        if not runs:
            raise ValueError("cannot aggregate an empty run sequence")

        gen = [r.effective_gen_per_s for r in runs]
        prompt_rates = [
            r.server_prompt_per_s for r in runs if r.server_prompt_per_s is not None
        ]
        return cls(
            model_key=spec.key,
            display_name=spec.display_name,
            is_qat=spec.is_qat,
            n_runs=len(runs),
            mean_gen_per_s=statistics.fmean(gen),
            median_gen_per_s=statistics.median(gen),
            stdev_gen_per_s=_stdev(gen),
            mean_prompt_per_s=statistics.fmean(prompt_rates) if prompt_rates else 0.0,
            mean_wall_time_s=statistics.fmean([r.wall_time_s for r in runs]),
            # Token counts are deterministic for a fixed prompt + max_tokens, so
            # the last run is representative.
            prompt_tokens=runs[-1].prompt_tokens,
            completion_tokens=runs[-1].completion_tokens,
            vram_used_mib=vram_used_mib,
            runs=tuple(runs),
        )


def _opt_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _stdev(values: Sequence[float]) -> float:
    """Sample standard deviation, defined as 0.0 for fewer than two points."""
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


__all__ = ["RunMetrics", "AggregatedMetrics"]
