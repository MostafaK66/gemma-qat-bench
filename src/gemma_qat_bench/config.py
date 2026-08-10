"""Configuration objects for the benchmark.

All configuration is expressed as **frozen** dataclasses that validate their
own invariants in ``__post_init__``. Constructing an invalid config raises
:class:`~gemma_qat_bench.exceptions.ConfigError` immediately, so a bad value can
never silently propagate into a subprocess command or an HTTP payload.

The defaults reproduce the DataCamp "Gemma 4 QAT" tutorial, with two
corrections discovered against the live Hugging Face repos:

* the non-QAT repo id is ``unsloth/gemma-4-12b-it-GGUF`` (lowercase ``b``); the
  tutorial's capital-``B`` spelling does not match the case-sensitive repo id;
* Gemma 4 is a *thinking* model, so :attr:`SamplingConfig.extra_body` provides a
  hook to disable reasoning (otherwise ``content`` comes back empty).
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .exceptions import ConfigError

# --------------------------------------------------------------------------- #
# Tutorial defaults                                                           #
# --------------------------------------------------------------------------- #

DEFAULT_PROMPT = (
    "Explain why quantization-aware training is useful for running LLMs on "
    "consumer GPUs."
)
DEFAULT_SYSTEM_PROMPT = "You are a helpful local AI assistant."

# Conventional location of the server binary after a `cmake -B build` build.
DEFAULT_SERVER_BINARY = Path("third_party/llama.cpp/build/bin/llama-server")


# --------------------------------------------------------------------------- #
# Sampling                                                                     #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SamplingConfig:
    """Decoding parameters sent with every chat request.

    ``extra_body`` is merged verbatim into the request JSON. Use it for engine
    specific knobs, e.g. to stop Gemma 4 from spending the token budget on
    hidden reasoning::

        SamplingConfig(extra_body={"chat_template_kwargs": {"thinking": False}})
    """

    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 64
    max_tokens: int = 512
    extra_body: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.temperature < 0:
            raise ConfigError(f"temperature must be >= 0, got {self.temperature}")
        if not 0.0 < self.top_p <= 1.0:
            raise ConfigError(f"top_p must be in (0, 1], got {self.top_p}")
        if self.top_k < 0:
            raise ConfigError(f"top_k must be >= 0, got {self.top_k}")
        if self.max_tokens <= 0:
            raise ConfigError(f"max_tokens must be > 0, got {self.max_tokens}")
        # Freeze the mapping so the frozen dataclass is genuinely immutable.
        object.__setattr__(self, "extra_body", dict(self.extra_body))


# --------------------------------------------------------------------------- #
# Server                                                                       #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ServerConfig:
    """Everything needed to launch and reach a single ``llama-server``."""

    binary_path: Path = DEFAULT_SERVER_BINARY
    host: str = "127.0.0.1"
    port: int = 8001
    ctx_size: int = 8192
    n_gpu_layers: int = 99
    startup_timeout_s: float = 180.0
    health_poll_interval_s: float = 1.0
    extra_args: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "binary_path", Path(self.binary_path))
        object.__setattr__(self, "extra_args", tuple(self.extra_args))
        if not 0 < self.port <= 65535:
            raise ConfigError(f"port must be in 1..65535, got {self.port}")
        if self.ctx_size <= 0:
            raise ConfigError(f"ctx_size must be > 0, got {self.ctx_size}")
        if self.n_gpu_layers < 0:
            raise ConfigError(f"n_gpu_layers must be >= 0, got {self.n_gpu_layers}")
        if self.startup_timeout_s <= 0:
            raise ConfigError(
                f"startup_timeout_s must be > 0, got {self.startup_timeout_s}"
            )
        if self.health_poll_interval_s <= 0:
            raise ConfigError(
                "health_poll_interval_s must be > 0, "
                f"got {self.health_poll_interval_s}"
            )

    @property
    def base_url(self) -> str:
        """Client-facing base URL.

        A server bound to ``0.0.0.0`` (or an empty host) is reachable locally at
        ``127.0.0.1``; translating here keeps health checks from failing.
        """
        host = self.host
        if host in {"", "0.0.0.0", "::"}:
            host = "127.0.0.1"
        return f"http://{host}:{self.port}"


# --------------------------------------------------------------------------- #
# Models                                                                       #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Identifies one GGUF model variant on Hugging Face and on disk."""

    key: str
    display_name: str
    repo_id: str
    local_dir: Path
    is_qat: bool = False
    include_patterns: tuple[str, ...] = ("*UD-Q4_K_XL*", "*mmproj-BF16*")
    gguf_pattern: str = "*UD-Q4_K_XL*.gguf"

    def __post_init__(self) -> None:
        object.__setattr__(self, "local_dir", Path(self.local_dir))
        object.__setattr__(self, "include_patterns", tuple(self.include_patterns))
        for attr in ("key", "display_name", "repo_id", "gguf_pattern"):
            if not str(getattr(self, attr)).strip():
                raise ConfigError(f"ModelSpec.{attr} must be a non-empty string")
        if not self.include_patterns:
            raise ConfigError("ModelSpec.include_patterns must not be empty")

    def resolve_gguf(self) -> Path:
        """Return the primary ``.gguf`` weight file under :attr:`local_dir`.

        Multimodal projector files (``mmproj*``) are excluded. When a model is
        sharded, the ``*-00001-of-*`` shard is returned because ``llama.cpp``
        auto-discovers the remaining shards from the first one.

        Raises :class:`ModelDownloadError` if nothing matches.
        """
        from .exceptions import ModelDownloadError

        candidates = [
            path
            for path in sorted(self.local_dir.rglob(self.gguf_pattern))
            if path.is_file() and not path.name.startswith("mmproj")
        ]
        if not candidates:
            raise ModelDownloadError(
                f"No file matching {self.gguf_pattern!r} under {self.local_dir}"
            )
        for path in candidates:
            if "00001-of-" in path.name:
                return path
        return candidates[0]


# --------------------------------------------------------------------------- #
# Build                                                                        #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class BuildConfig:
    """Inputs for cloning and compiling ``llama.cpp`` (mirrors the tutorial)."""

    source_dir: Path = Path("third_party/llama.cpp")
    build_dir: Path | None = None
    repo_url: str = "https://github.com/ggml-org/llama.cpp"
    use_cuda: bool | None = None  # None => auto-detect
    build_shared_libs: bool = False
    targets: tuple[str, ...] = (
        "llama-cli",
        "llama-mtmd-cli",
        "llama-server",
        "llama-gguf-split",
    )
    jobs: int | None = None
    clean_first: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_dir", Path(self.source_dir))
        object.__setattr__(self, "targets", tuple(self.targets))
        if self.build_dir is not None:
            object.__setattr__(self, "build_dir", Path(self.build_dir))
        if not self.repo_url.strip():
            raise ConfigError("BuildConfig.repo_url must not be empty")
        if not self.targets:
            raise ConfigError("BuildConfig.targets must not be empty")
        if self.jobs is not None and self.jobs <= 0:
            raise ConfigError(f"jobs must be > 0 when set, got {self.jobs}")

    @property
    def resolved_build_dir(self) -> Path:
        return self.build_dir if self.build_dir is not None else self.source_dir / "build"


# --------------------------------------------------------------------------- #
# Benchmark                                                                    #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    """Prompt and repetition settings for a benchmark run.

    Unlike the single-shot tutorial, the default runs a warmup plus several
    measured passes so reported throughput has a mean and spread rather than one
    noisy sample.
    """

    prompt: str = DEFAULT_PROMPT
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    n_runs: int = 3
    warmup_runs: int = 1
    request_timeout_s: float = 300.0

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise ConfigError("BenchmarkConfig.prompt must not be empty")
        if self.n_runs <= 0:
            raise ConfigError(f"n_runs must be > 0, got {self.n_runs}")
        if self.warmup_runs < 0:
            raise ConfigError(f"warmup_runs must be >= 0, got {self.warmup_runs}")
        if self.request_timeout_s <= 0:
            raise ConfigError(
                f"request_timeout_s must be > 0, got {self.request_timeout_s}"
            )


# --------------------------------------------------------------------------- #
# Top-level application config                                                 #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Aggregate of every config object required to run the benchmark."""

    models: tuple[ModelSpec, ...]
    server: ServerConfig = field(default_factory=ServerConfig)
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    build: BuildConfig = field(default_factory=BuildConfig)
    models_root: Path = Path("models")
    results_dir: Path = Path("results")
    capture_vram: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "models", tuple(self.models))
        object.__setattr__(self, "models_root", Path(self.models_root))
        object.__setattr__(self, "results_dir", Path(self.results_dir))
        if not self.models:
            raise ConfigError("AppConfig.models must contain at least one model")
        keys = [m.key for m in self.models]
        if len(keys) != len(set(keys)):
            raise ConfigError(f"ModelSpec keys must be unique, got {keys}")

    # -- factories ---------------------------------------------------------- #

    @classmethod
    def tutorial_default(
        cls,
        *,
        server_binary: Path | str = DEFAULT_SERVER_BINARY,
        models_root: Path | str = "models",
    ) -> AppConfig:
        """Build the two-model (non-QAT vs QAT) Gemma 4 12B configuration."""
        models_root = Path(models_root)
        models = (
            ModelSpec(
                key="non-qat",
                display_name="Gemma 4 12B IT (non-QAT)",
                repo_id="unsloth/gemma-4-12b-it-GGUF",
                local_dir=models_root / "gemma-4-12b-it-GGUF",
                is_qat=False,
            ),
            ModelSpec(
                key="qat",
                display_name="Gemma 4 12B IT (QAT)",
                repo_id="unsloth/gemma-4-12B-it-qat-GGUF",
                local_dir=models_root / "gemma-4-12B-it-qat-GGUF",
                is_qat=True,
            ),
        )
        return cls(
            models=models,
            server=ServerConfig(binary_path=Path(server_binary)),
            models_root=models_root,
        )

    @classmethod
    def from_toml(cls, path: Path | str) -> AppConfig:
        """Load an :class:`AppConfig` from a TOML file (see ``configs/``)."""
        path = Path(path)
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
        except FileNotFoundError as exc:
            raise ConfigError(f"Config file not found: {path}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
        return cls.from_mapping(raw)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> AppConfig:
        """Build an :class:`AppConfig` from a plain (already parsed) mapping."""
        model_entries = raw.get("models")
        if not model_entries:
            raise ConfigError("config must define a non-empty [[models]] array")

        models = tuple(_model_from_mapping(entry) for entry in model_entries)
        server = _server_from_mapping(raw.get("server", {}))
        sampling = _sampling_from_mapping(raw.get("sampling", {}))
        benchmark = _benchmark_from_mapping(raw.get("benchmark", {}))
        build = _build_from_mapping(raw.get("build", {}))

        return cls(
            models=models,
            server=server,
            sampling=sampling,
            benchmark=benchmark,
            build=build,
            models_root=Path(raw.get("models_root", "models")),
            results_dir=Path(raw.get("results_dir", "results")),
            capture_vram=bool(raw.get("capture_vram", True)),
        )


# --------------------------------------------------------------------------- #
# Mapping -> dataclass helpers (kept small and pure for easy testing)         #
# --------------------------------------------------------------------------- #


def _require(mapping: Mapping[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise ConfigError(f"missing required key {key!r} in {context}")
    return mapping[key]


def _model_from_mapping(entry: Mapping[str, Any]) -> ModelSpec:
    return ModelSpec(
        key=_require(entry, "key", "[[models]]"),
        display_name=_require(entry, "display_name", "[[models]]"),
        repo_id=_require(entry, "repo_id", "[[models]]"),
        local_dir=Path(_require(entry, "local_dir", "[[models]]")),
        is_qat=bool(entry.get("is_qat", False)),
        include_patterns=tuple(
            entry.get("include_patterns", ("*UD-Q4_K_XL*", "*mmproj-BF16*"))
        ),
        gguf_pattern=entry.get("gguf_pattern", "*UD-Q4_K_XL*.gguf"),
    )


def _server_from_mapping(entry: Mapping[str, Any]) -> ServerConfig:
    defaults = ServerConfig()
    return ServerConfig(
        binary_path=Path(entry.get("binary_path", defaults.binary_path)),
        host=entry.get("host", defaults.host),
        port=int(entry.get("port", defaults.port)),
        ctx_size=int(entry.get("ctx_size", defaults.ctx_size)),
        n_gpu_layers=int(entry.get("n_gpu_layers", defaults.n_gpu_layers)),
        startup_timeout_s=float(
            entry.get("startup_timeout_s", defaults.startup_timeout_s)
        ),
        health_poll_interval_s=float(
            entry.get("health_poll_interval_s", defaults.health_poll_interval_s)
        ),
        extra_args=tuple(entry.get("extra_args", ())),
    )


def _sampling_from_mapping(entry: Mapping[str, Any]) -> SamplingConfig:
    defaults = SamplingConfig()
    return SamplingConfig(
        temperature=float(entry.get("temperature", defaults.temperature)),
        top_p=float(entry.get("top_p", defaults.top_p)),
        top_k=int(entry.get("top_k", defaults.top_k)),
        max_tokens=int(entry.get("max_tokens", defaults.max_tokens)),
        extra_body=dict(entry.get("extra_body", {})),
    )


def _benchmark_from_mapping(entry: Mapping[str, Any]) -> BenchmarkConfig:
    defaults = BenchmarkConfig()
    return BenchmarkConfig(
        prompt=entry.get("prompt", defaults.prompt),
        system_prompt=entry.get("system_prompt", defaults.system_prompt),
        n_runs=int(entry.get("n_runs", defaults.n_runs)),
        warmup_runs=int(entry.get("warmup_runs", defaults.warmup_runs)),
        request_timeout_s=float(
            entry.get("request_timeout_s", defaults.request_timeout_s)
        ),
    )


def _build_from_mapping(entry: Mapping[str, Any]) -> BuildConfig:
    defaults = BuildConfig()
    use_cuda = entry.get("use_cuda", None)
    build_dir = entry.get("build_dir", None)
    jobs = entry.get("jobs", None)
    return BuildConfig(
        source_dir=Path(entry.get("source_dir", defaults.source_dir)),
        build_dir=Path(build_dir) if build_dir is not None else None,
        repo_url=entry.get("repo_url", defaults.repo_url),
        use_cuda=None if use_cuda is None else bool(use_cuda),
        build_shared_libs=bool(
            entry.get("build_shared_libs", defaults.build_shared_libs)
        ),
        targets=tuple(entry.get("targets", defaults.targets)),
        jobs=int(jobs) if jobs is not None else None,
        clean_first=bool(entry.get("clean_first", defaults.clean_first)),
    )


__all__ = [
    "SamplingConfig",
    "ServerConfig",
    "ModelSpec",
    "BuildConfig",
    "BenchmarkConfig",
    "AppConfig",
    "DEFAULT_PROMPT",
    "DEFAULT_SYSTEM_PROMPT",
    "DEFAULT_SERVER_BINARY",
]
