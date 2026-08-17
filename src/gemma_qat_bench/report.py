"""Assemble and render the benchmark report.

:class:`BenchmarkReport` holds the aggregated metrics for every model plus a
derived :class:`ComparisonSummary` (baseline vs QAT deltas, matching the
tutorial's headline numbers). Rendering to console, Markdown, and a
JSON-serialisable dict lives here so the runner stays focused on measurement.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from .config import AppConfig
from .metrics import AggregatedMetrics


@dataclass(frozen=True, slots=True)
class ComparisonSummary:
    """Baseline (non-QAT) vs QAT deltas."""

    baseline_key: "str"
    qat_key: "str"
    baseline_gen_per_s: "float"
    qat_gen_per_s: "float"
    gen_speedup_pct: "float"
    baseline_wall_s: "float"
    qat_wall_s: "float"
    baseline_vram_mib: "int | None"
    qat_vram_mib: "int | None"
    vram_saved_mib: "int | None"
    vram_saved_pct: "float | None"

    @classmethod
    def from_pair(
        cls, baseline: "AggregatedMetrics", qat: "AggregatedMetrics"
    ) -> "ComparisonSummary":
        speedup = _pct_change(baseline.mean_gen_per_s, qat.mean_gen_per_s)
        vram_saved, vram_pct = _vram_delta(
            baseline.vram_used_mib, qat.vram_used_mib
        )
        return cls(
            baseline_key=baseline.model_key,
            qat_key=qat.model_key,
            baseline_gen_per_s=baseline.mean_gen_per_s,
            qat_gen_per_s=qat.mean_gen_per_s,
            gen_speedup_pct=speedup,
            baseline_wall_s=baseline.mean_wall_time_s,
            qat_wall_s=qat.mean_wall_time_s,
            baseline_vram_mib=baseline.vram_used_mib,
            qat_vram_mib=qat.vram_used_mib,
            vram_saved_mib=vram_saved,
            vram_saved_pct=vram_pct,
        )


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    """Full result set for one benchmark invocation."""

    results: "tuple[AggregatedMetrics, ...]"
    prompt: "str"
    max_tokens: "int"
    quantization: "str"
    created_at: "str"

    @classmethod
    def build(
        cls,
        results: "Sequence[AggregatedMetrics]",
        config: "AppConfig",
        *,
        quantization: "str" = "UD-Q4_K_XL",
        created_at: "str | None" = None,
    ) -> "BenchmarkReport":
        return cls(
            results=tuple(results),
            prompt=config.benchmark.prompt,
            max_tokens=config.sampling.max_tokens,
            quantization=quantization,
            created_at=created_at or datetime.now(UTC).isoformat(),
        )

    @property
    def comparison(self) -> "ComparisonSummary | None":
        """Pair the first non-QAT baseline with the first QAT result, if both exist."""
        baseline = next((r for r in self.results if not r.is_qat), None)
        qat = next((r for r in self.results if r.is_qat), None)
        if baseline is None or qat is None:
            return None
        return ComparisonSummary.from_pair(baseline, qat)

    # -- rendering ---------------------------------------------------------- #

    def to_json_dict(self) -> "dict[str, Any]":
        comparison = self.comparison
        return {
            "created_at": self.created_at,
            "prompt": self.prompt,
            "max_tokens": self.max_tokens,
            "quantization": self.quantization,
            "results": [_aggregate_to_dict(r) for r in self.results],
            "comparison": asdict(comparison) if comparison else None,
        }

    def to_markdown(self) -> "str":
        header = (
            "| Metric | " + " | ".join(r.display_name for r in self.results) + " |"
        )
        divider = "| --- | " + " | ".join("---" for _ in self.results) + " |"
        rows = [
            _md_row("Quantization", [self.quantization for _ in self.results]),
            _md_row("Prompt tokens", [str(r.prompt_tokens) for r in self.results]),
            _md_row(
                "Completion tokens",
                [str(r.completion_tokens) for r in self.results],
            ),
            _md_row(
                "Gen speed (tok/s)",
                [f"{r.mean_gen_per_s:.2f}" for r in self.results],
            ),
            _md_row(
                "Gen stdev (tok/s)",
                [f"{r.stdev_gen_per_s:.2f}" for r in self.results],
            ),
            _md_row(
                "Prompt speed (tok/s)",
                [f"{r.mean_prompt_per_s:.2f}" for r in self.results],
            ),
            _md_row(
                "Wall time (s)",
                [f"{r.mean_wall_time_s:.3f}" for r in self.results],
            ),
            _md_row(
                "VRAM used (MiB)",
                [_fmt_vram(r.vram_used_mib) for r in self.results],
            ),
        ]
        lines = ["# QAT vs non-QAT benchmark", "", header, divider, *rows]
        comparison = self.comparison
        if comparison is not None:
            lines += ["", "## Comparison (QAT vs baseline)", ""]
            lines += _comparison_lines(comparison, bullet="- ")
        return "\n".join(lines) + "\n"

    def to_console(self) -> "str":
        labels = [
            "Model",
            "Gen tok/s",
            "±stdev",
            "Prompt tok/s",
            "Wall s",
            "VRAM MiB",
        ]
        rows = [
            [
                r.display_name,
                f"{r.mean_gen_per_s:.2f}",
                f"{r.stdev_gen_per_s:.2f}",
                f"{r.mean_prompt_per_s:.2f}",
                f"{r.mean_wall_time_s:.3f}",
                _fmt_vram(r.vram_used_mib),
            ]
            for r in self.results
        ]
        table = _fixed_width_table(labels, rows)
        comparison = self.comparison
        if comparison is not None:
            table += "\n\nComparison (QAT vs baseline):\n"
            table += "\n".join(_comparison_lines(comparison, bullet="  - "))
        return table


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _pct_change(baseline: "float", new: "float") -> "float":
    if baseline == 0:
        return 0.0
    return (new - baseline) / baseline * 100.0


def _vram_delta(
    baseline: "int | None", qat: "int | None"
) -> "tuple[int | None, float | None]":
    if baseline is None or qat is None:
        return None, None
    saved = baseline - qat
    pct = (saved / baseline * 100.0) if baseline else None
    return saved, pct


def _aggregate_to_dict(agg: "AggregatedMetrics") -> "dict[str, Any]":
    data = asdict(agg)
    # Expand nested RunMetrics with their derived properties for completeness.
    data["runs"] = [
        {
            **asdict(run),
            "total_tokens": run.total_tokens,
            "wall_gen_per_s": run.wall_gen_per_s,
            "effective_gen_per_s": run.effective_gen_per_s,
        }
        for run in agg.runs
    ]
    return data


def _md_row(label: "str", cells: "Sequence[str]") -> "str":
    return f"| {label} | " + " | ".join(cells) + " |"


def _fmt_vram(value: "int | None") -> "str":
    return "n/a" if value is None else str(value)


def _comparison_lines(summary: "ComparisonSummary", *, bullet: "str") -> "list[str]":
    lines = [
        f"{bullet}Generation speed: {summary.baseline_gen_per_s:.2f} -> "
        f"{summary.qat_gen_per_s:.2f} tok/s ({summary.gen_speedup_pct:+.1f}%)",
    ]
    if summary.vram_saved_mib is not None and summary.vram_saved_pct is not None:
        saved, pct = summary.vram_saved_mib, summary.vram_saved_pct
        if saved >= 0:
            lines.append(
                f"{bullet}VRAM: {saved} MiB saved ({pct:.1f}% less than baseline)"
            )
        else:
            lines.append(
                f"{bullet}VRAM: {abs(saved)} MiB more "
                f"({abs(pct):.1f}% more than baseline)"
            )
    lines.append(
        f"{bullet}Wall time: {summary.baseline_wall_s:.3f}s -> "
        f"{summary.qat_wall_s:.3f}s"
    )
    return lines


def _fixed_width_table(header: "Sequence[str]", rows: "Sequence[Sequence[str]]") -> "str":
    columns = list(zip(header, *rows, strict=True)) if rows else [(h,) for h in header]
    widths = [max(len(str(cell)) for cell in col) for col in columns]

    def fmt(cells: "Sequence[str]") -> "str":
        return "  ".join(
            str(c).ljust(w) for c, w in zip(cells, widths, strict=True)
        )

    sep = "  ".join("-" * w for w in widths)
    lines = [fmt(header), sep]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines)


__all__ = ["BenchmarkReport", "ComparisonSummary"]
