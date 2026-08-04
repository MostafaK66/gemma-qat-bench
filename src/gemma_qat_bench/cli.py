"""Command-line interface: ``gemma-qat-bench <command>``.

Commands
--------
``build``     Clone and compile ``llama.cpp`` (CUDA auto-detected).
``download``  Fetch the configured model GGUFs from Hugging Face.
``bench``     Run the benchmark against an already-built server binary.
``all``       ``build`` then ``bench`` (which downloads on demand) in one shot.

With no ``--config`` the Gemma 4 12B non-QAT vs QAT tutorial setup is used.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from ._logging import configure_logging, get_logger
from .benchmark import BenchmarkRunner
from .build import LlamaCppBuilder
from .config import AppConfig
from .exceptions import BuildError, GemmaQATBenchError
from .models import ModelManager
from .report import BenchmarkReport

_LOG = get_logger("cli")


# --------------------------------------------------------------------------- #
# Argument parsing                                                             #
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gemma-qat-bench",
        description="Benchmark QAT vs non-QAT GGUF models with llama.cpp.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a TOML config file (defaults to the Gemma 4 tutorial setup).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Clone and compile llama.cpp.")
    _add_build_args(p_build)

    sub.add_parser("download", help="Download the configured model files.")

    p_bench = sub.add_parser("bench", help="Run the benchmark.")
    _add_bench_args(p_bench)

    p_all = sub.add_parser("all", help="Build, then run the full benchmark.")
    _add_build_args(p_all)
    _add_bench_args(p_all)

    return parser


def _add_build_args(parser: argparse.ArgumentParser) -> None:
    cuda = parser.add_mutually_exclusive_group()
    cuda.add_argument(
        "--cuda", dest="cuda", action="store_true", default=None,
        help="Force a CUDA (GPU) build.",
    )
    cuda.add_argument(
        "--no-cuda", dest="cuda", action="store_false", default=None,
        help="Force a CPU-only build.",
    )
    parser.add_argument("--jobs", type=int, default=None, help="Parallel build jobs.")
    parser.add_argument(
        "--source-dir", type=Path, default=None,
        help="Where to clone/build llama.cpp.",
    )


def _add_bench_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runs", type=int, default=None, help="Measured runs per model.")
    parser.add_argument("--warmup", type=int, default=None, help="Warmup runs per model.")
    parser.add_argument(
        "--server-binary", type=Path, default=None,
        help="Path to the llama-server binary.",
    )
    parser.add_argument(
        "--no-vram", dest="capture_vram", action="store_false", default=None,
        help="Skip nvidia-smi VRAM capture.",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Directory for JSON/Markdown results.",
    )


# --------------------------------------------------------------------------- #
# Config resolution                                                            #
# --------------------------------------------------------------------------- #


def resolve_config(args: argparse.Namespace) -> AppConfig:
    """Load the base config and apply any CLI overrides."""
    config = (
        AppConfig.from_toml(args.config)
        if args.config is not None
        else AppConfig.tutorial_default()
    )

    # Benchmark overrides
    bench = config.benchmark
    if getattr(args, "runs", None) is not None:
        bench = replace(bench, n_runs=args.runs)
    if getattr(args, "warmup", None) is not None:
        bench = replace(bench, warmup_runs=args.warmup)
    config = replace(config, benchmark=bench)

    # Server overrides
    if getattr(args, "server_binary", None) is not None:
        config = replace(
            config, server=replace(config.server, binary_path=args.server_binary)
        )

    # Build overrides
    build = config.build
    if getattr(args, "cuda", None) is not None:
        build = replace(build, use_cuda=args.cuda)
    if getattr(args, "jobs", None) is not None:
        build = replace(build, jobs=args.jobs)
    if getattr(args, "source_dir", None) is not None:
        build = replace(build, source_dir=args.source_dir)
    config = replace(config, build=build)

    # Misc overrides
    if getattr(args, "capture_vram", None) is not None:
        config = replace(config, capture_vram=args.capture_vram)
    if getattr(args, "out", None) is not None:
        config = replace(config, results_dir=args.out)

    return config


# --------------------------------------------------------------------------- #
# Commands                                                                     #
# --------------------------------------------------------------------------- #


def cmd_build(config: AppConfig) -> AppConfig:
    builder = LlamaCppBuilder(config.build)
    binary = builder.build()
    print(f"Built llama-server: {binary}")
    return replace(config, server=replace(config.server, binary_path=binary))


def cmd_download(config: AppConfig) -> None:
    manager = ModelManager()
    for spec in config.models:
        path = manager.ensure(spec)
        print(f"{spec.key}: {path}")


def cmd_bench(config: AppConfig) -> BenchmarkReport:
    _require_server_binary(config)
    report = BenchmarkRunner(config).run()
    _emit_report(report, config.results_dir)
    return report


def cmd_all(config: AppConfig) -> BenchmarkReport:
    config = cmd_build(config)
    return cmd_bench(config)


# --------------------------------------------------------------------------- #
# Output helpers                                                               #
# --------------------------------------------------------------------------- #


def _require_server_binary(config: AppConfig) -> None:
    binary = config.server.binary_path
    if not binary.exists():
        raise BuildError(
            f"llama-server binary not found at {binary}. Run `gemma-qat-bench build` "
            "first, or pass --server-binary /path/to/llama-server."
        )


def _emit_report(report: BenchmarkReport, results_dir: Path) -> None:
    print()
    print(report.to_console())

    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = results_dir / f"benchmark-{stamp}.json"
    md_path = results_dir / f"benchmark-{stamp}.md"
    json_path.write_text(json.dumps(report.to_json_dict(), indent=2), encoding="utf-8")
    md_path.write_text(report.to_markdown(), encoding="utf-8")
    print(f"\nSaved: {json_path}\n       {md_path}")


# --------------------------------------------------------------------------- #
# Entry point                                                                  #
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(logging.DEBUG if args.verbose else logging.INFO)

    try:
        config = resolve_config(args)
        if args.command == "build":
            cmd_build(config)
        elif args.command == "download":
            cmd_download(config)
        elif args.command == "bench":
            cmd_bench(config)
        elif args.command == "all":
            cmd_all(config)
        else:  # pragma: no cover - argparse enforces the choices
            parser.error(f"unknown command {args.command!r}")
    except GemmaQATBenchError as exc:
        _LOG.error("%s", exc)
        return 1
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        _LOG.warning("interrupted")
        return 130
    return 0


__all__ = ["main", "build_parser", "resolve_config"]
