"""Executable implementation-fingerprint-v1 service."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Protocol

from .domain import DomainError, ImplementationFingerprint, normalize_repository_path


class ContentIdentityProvider(Protocol):
    def identity(self, relative_path: str) -> str: ...


class GitContentIdentityProvider:
    """Use Git's no-filter blob identity for present tracked or untracked files."""

    def __init__(self, repository_root: Path) -> None:
        self._root = repository_root.resolve()

    def identity(self, relative_path: str) -> str:
        path = (self._root / relative_path).resolve()
        if not path.is_relative_to(self._root) or not path.is_file():
            raise DomainError(f"cannot fingerprint non-file path: {relative_path}")
        try:
            completed = subprocess.run(
                ("git", "hash-object", "--no-filters", "--", relative_path),
                cwd=self._root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            # A missing or unlaunchable git binary must surface as the
            # environment failure the engine escalates on, not a raw traceback.
            raise DomainError(
                f"git hash-object failed for {relative_path}: {exc}"
            ) from exc
        identity = completed.stdout.strip()
        if completed.returncode != 0 or not identity:
            raise DomainError(
                f"git hash-object failed for {relative_path}: {completed.stderr.strip()}"
            )
        return identity


class FingerprintService:
    ALGORITHM = "implementation-fingerprint-v1"
    DELETED_SENTINEL = "DELETED"

    def __init__(
        self, repository_root: Path, identities: ContentIdentityProvider
    ) -> None:
        self._root = repository_root.resolve()
        self._identities = identities

    def capture(self, scope: tuple[str, ...]) -> ImplementationFingerprint:
        normalized = tuple(sorted({normalize_repository_path(path) for path in scope}))
        if not normalized:
            raise DomainError("fingerprint scope must not be empty")
        manifest: list[str] = []
        for relative_path in normalized:
            resolved = (self._root / relative_path).resolve()
            if not resolved.is_relative_to(self._root):
                raise DomainError(f"fingerprint path escaped repository: {relative_path}")
            if resolved.is_file():
                state = "present"
                content_identity = self._identities.identity(relative_path)
            elif not resolved.exists():
                state = "deleted"
                content_identity = self.DELETED_SENTINEL
            else:
                raise DomainError(
                    f"fingerprint scope path is not a file: {relative_path}"
                )
            manifest.append(f"{state}\t{relative_path}\t{content_identity}")
        canonical = "\n".join(manifest).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        return ImplementationFingerprint(
            self.ALGORITHM, digest, normalized, tuple(manifest)
        )

    def is_current(self, fingerprint: ImplementationFingerprint) -> bool:
        return self.capture(fingerprint.scope).digest == fingerprint.digest
