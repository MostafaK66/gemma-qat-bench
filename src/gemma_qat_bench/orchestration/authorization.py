"""Explicit human authorization boundary for orchestration side effects."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .domain import AuthorizationStatus, RequiredCommand


class AuthorizationAction(StrEnum):
    COMMAND_EXECUTION = "COMMAND_EXECUTION"
    GIT_MUTATION = "GIT_MUTATION"
    DEGRADED_MODE = "DEGRADED_MODE"


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    action: AuthorizationAction
    resource_id: str
    summary: str


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    status: AuthorizationStatus
    reason: str


class AuthorizationPort(Protocol):
    def decide(self, request: AuthorizationRequest) -> AuthorizationDecision: ...


class StaticAuthorization:
    """Injectable non-interactive authorization policy for CLI and tests."""

    def __init__(
        self,
        *,
        commands: AuthorizationStatus = AuthorizationStatus.REQUIRED,
        git: AuthorizationStatus = AuthorizationStatus.DENIED,
        degraded_mode: AuthorizationStatus = AuthorizationStatus.DENIED,
    ) -> None:
        self._statuses = {
            AuthorizationAction.COMMAND_EXECUTION: commands,
            AuthorizationAction.GIT_MUTATION: git,
            AuthorizationAction.DEGRADED_MODE: degraded_mode,
        }
        self.requests: list[AuthorizationRequest] = []

    def decide(self, request: AuthorizationRequest) -> AuthorizationDecision:
        self.requests.append(request)
        status = self._statuses[request.action]
        return AuthorizationDecision(status, f"static policy: {status.value}")


class InteractiveCommandAuthorization:
    """Ask once for the complete compiled command set and cache the decision."""

    def __init__(
        self,
        commands: tuple[RequiredCommand, ...],
        *,
        reader: Callable[[str], str] | None = None,
        writer: Callable[[str], None] | None = None,
        display_commands: bool = True,
    ) -> None:
        self._commands = commands
        self._reader = reader or input
        self._writer = writer or print
        self._display_commands = display_commands
        self._command_decision: AuthorizationDecision | None = None
        self.requests: list[AuthorizationRequest] = []

    @property
    def command_decision(self) -> AuthorizationDecision | None:
        """Expose the cached decision for truthful final CLI observability."""
        return self._command_decision

    def decide(self, request: AuthorizationRequest) -> AuthorizationDecision:
        self.requests.append(request)
        if request.action is not AuthorizationAction.COMMAND_EXECUTION:
            return AuthorizationDecision(
                AuthorizationStatus.DENIED,
                f"interactive policy does not authorize {request.action.value}",
            )
        if self._command_decision is None:
            if self._display_commands:
                self._writer(
                    "Verification commands requiring one authorization decision:"
                )
                for command in self._commands:
                    command_id = json.dumps(str(command.command_id), ensure_ascii=False)
                    argv = json.dumps(list(command.argv), ensure_ascii=False)
                    cwd = json.dumps(command.cwd, ensure_ascii=False)
                    self._writer(f"  {command_id}  {argv}  (cwd: {cwd})")
            try:
                answer = self._reader("Authorize all displayed commands? [y/N] ")
            except EOFError:
                answer = ""
            authorized = answer.strip().lower() in {"y", "yes"}
            status = (
                AuthorizationStatus.AUTHORIZED
                if authorized
                else AuthorizationStatus.DENIED
            )
            reason = (
                "human authorized the complete compiled command set"
                if authorized
                else "human did not authorize the complete compiled command set"
            )
            self._command_decision = AuthorizationDecision(status, reason)
        return self._command_decision
