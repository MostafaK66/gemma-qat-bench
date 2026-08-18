"""Deterministic Git workspace delta detection for fingerprint scope integrity."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from .domain import DomainError, normalize_repository_path
from .fingerprint import GitContentIdentityProvider

ScopeBaseline = dict[str, str]


class WorkspaceChangeDetector(Protocol):
    def capture(self) -> ScopeBaseline: ...


class GitWorkspaceChangeDetector:
    """Capture changed tracked, staged, deleted, and untracked file identities."""

    def __init__(self, repository_root: Path) -> None:
        self._root = repository_root.resolve()
        self._identities = GitContentIdentityProvider(self._root)

    def capture(self) -> ScopeBaseline:
        tracked = self._git_paths(
            ("git", "diff", "--name-only", "--no-renames", "-z", "HEAD", "--")
        )
        untracked = self._git_paths(
            ("git", "ls-files", "--others", "--exclude-standard", "-z", "--")
        )
        result: ScopeBaseline = {}
        for relative_path in sorted(tracked | untracked):
            path = (self._root / relative_path).resolve()
            if not path.is_relative_to(self._root):
                raise DomainError(
                    f"Git reported a path outside the repository: {relative_path}"
                )
            result[relative_path] = (
                self._identities.identity(relative_path) if path.is_file() else "DELETED"
            )
        return result

    def _git_paths(self, argv: tuple[str, ...]) -> set[str]:
        completed = subprocess.run(
            argv,
            cwd=self._root,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            message = completed.stderr.decode("utf-8", errors="replace").strip()
            raise DomainError(f"Git workspace inspection failed: {message}")
        return {
            normalize_repository_path(raw.decode("utf-8"))
            for raw in completed.stdout.split(b"\0")
            if raw
        }


def changed_since(baseline: ScopeBaseline, current: ScopeBaseline) -> tuple[str, ...]:
    """Return paths whose final identity differs from task-start workspace state."""
    return tuple(
        sorted(
            path
            for path in baseline.keys() | current.keys()
            if baseline.get(path) != current.get(path)
        )
    )
