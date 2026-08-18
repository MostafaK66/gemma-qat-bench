"""Download and resolve GGUF model files from Hugging Face.

The heavy dependency (``huggingface_hub``) is imported lazily inside the default
downloader so that importing this module -- and running the test suite with an
injected fake downloader -- requires nothing extra.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ._logging import get_logger
from .config import ModelSpec
from .exceptions import ModelDownloadError

_LOG = get_logger("models")

# Signature: (repo_id, local_dir, allow_patterns) -> downloaded path (ignored).
Downloader = Callable[[str, str, list[str]], str]


def _default_downloader(repo_id: str, local_dir: str, allow_patterns: list[str]) -> str:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover - exercised only without the dep
        raise ModelDownloadError(
            "huggingface_hub is required to download models; install it with "
            "`pip install huggingface_hub` or provide a custom downloader."
        ) from exc
    return snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        allow_patterns=allow_patterns,
    )


class ModelManager:
    """Ensures a model's GGUF file is present locally, downloading if needed."""

    def __init__(
        self,
        *,
        downloader: Downloader = _default_downloader,
    ) -> None:
        self._downloader = downloader

    def ensure(self, spec: ModelSpec) -> Path:
        """Return the local path to the model's primary GGUF weight file.

        Skips the download when the file is already on disk. Any exception from
        the downloader is normalised to :class:`ModelDownloadError`.
        """
        existing = self._try_resolve(spec)
        if existing is not None:
            _LOG.info("model %s already present: %s", spec.key, existing)
            return existing

        _LOG.info("downloading %s -> %s", spec.repo_id, spec.local_dir)
        spec.local_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._downloader(
                spec.repo_id,
                str(spec.local_dir),
                list(spec.include_patterns),
            )
        except ModelDownloadError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalise any backend failure
            raise ModelDownloadError(f"failed to download {spec.repo_id}: {exc}") from exc

        try:
            return spec.resolve_gguf()
        except ModelDownloadError as exc:
            raise ModelDownloadError(
                f"download of {spec.repo_id} completed but no file matching "
                f"{spec.gguf_pattern!r} was found under {spec.local_dir}"
            ) from exc

    @staticmethod
    def _try_resolve(spec: ModelSpec) -> Path | None:
        try:
            return spec.resolve_gguf()
        except ModelDownloadError:
            return None


__all__ = ["ModelManager", "Downloader"]
