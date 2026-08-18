"""Explicit human authorization boundary for orchestration side effects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .domain import AuthorizationStatus


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
