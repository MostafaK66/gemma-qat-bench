"""Authorized, injected execution of task-scoped verification commands."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .authorization import (
    AuthorizationAction,
    AuthorizationPort,
    AuthorizationRequest,
)
from .domain import (
    AuthorizationStatus,
    CommandEvidence,
    CommandStatus,
    DomainError,
    OutputHandling,
    RequiredCommand,
)


@dataclass(frozen=True, slots=True)
class RunnerResult:
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    environment_error: str | None = None


class CommandRunner(Protocol):
    def run(self, command: RequiredCommand) -> RunnerResult: ...


class SubprocessCommandRunner:
    """Run argv without a shell and confine the working directory to the repository."""

    def __init__(self, repository_root: Path, *, timeout_seconds: float = 900.0) -> None:
        self._root = repository_root.resolve()
        self._timeout = timeout_seconds

    def run(self, command: RequiredCommand) -> RunnerResult:
        cwd = (self._root / command.cwd).resolve()
        if not cwd.is_relative_to(self._root):
            return RunnerResult(None, environment_error="command cwd escaped repository")
        try:
            completed = subprocess.run(
                command.argv,
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                # A verification command may legitimately emit non-UTF-8 bytes;
                # strict decoding would crash the workflow instead of recording
                # evidence, and every resume would crash the same way.
                errors="replace",
                timeout=self._timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return RunnerResult(None, environment_error=f"{type(exc).__name__}: {exc}")
        return RunnerResult(completed.returncode, completed.stdout, completed.stderr)


class CommandBroker:
    """Own canonical execution state; specialists receive only projections."""

    def __init__(
        self,
        runner: CommandRunner,
        authorization: AuthorizationPort,
        *,
        output_limit: int = 4_000,
    ) -> None:
        if output_limit < 1:
            raise DomainError("output limit must be positive")
        self._runner = runner
        self._authorization = authorization
        self._output_limit = output_limit

    def execute(
        self, commands: tuple[RequiredCommand, ...], *, fingerprint: str
    ) -> tuple[CommandEvidence, ...]:
        evidence: list[CommandEvidence] = []
        for command in commands:
            decision = self._authorization.decide(
                AuthorizationRequest(
                    AuthorizationAction.COMMAND_EXECUTION,
                    str(command.command_id),
                    "execute required verification argv",
                )
            )
            if decision.status is not AuthorizationStatus.AUTHORIZED:
                status = (
                    CommandStatus.AUTHORIZATION_REQUIRED
                    if decision.status is AuthorizationStatus.REQUIRED
                    else CommandStatus.DENIED
                )
                evidence.append(
                    CommandEvidence(
                        command.command_id,
                        command.argv,
                        command.cwd,
                        status,
                        None,
                        decision.reason,
                        False,
                        command.required,
                        fingerprint,
                        command.output_handling,
                    )
                )
                continue
            result = self._runner.run(command)
            if result.environment_error is not None:
                status = CommandStatus.ENVIRONMENT_ERROR
                output = result.environment_error
            else:
                status = (
                    CommandStatus.SUCCEEDED
                    if result.exit_code == 0
                    else CommandStatus.FAILED
                )
                output = (
                    _combine_output(result.stdout, result.stderr)
                    if command.output_handling is OutputHandling.EXCERPT
                    else "command output withheld by task policy"
                )
            truncated = len(output) > self._output_limit
            evidence.append(
                CommandEvidence(
                    command.command_id,
                    command.argv,
                    command.cwd,
                    status,
                    result.exit_code,
                    output[: self._output_limit],
                    truncated,
                    command.required,
                    fingerprint,
                    command.output_handling,
                )
            )
        return tuple(evidence)


def _combine_output(stdout: str, stderr: str) -> str:
    sections = []
    if stdout:
        sections.append("stdout:\n" + stdout)
    if stderr:
        sections.append("stderr:\n" + stderr)
    return "\n".join(sections) or "command produced no output"
