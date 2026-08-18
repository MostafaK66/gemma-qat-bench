"""Isolated adapter for the optional OpenAI Codex Python SDK."""

from __future__ import annotations

from contextlib import suppress
from typing import Any

from .domain import FailureKind, TransportStatus
from .specialists import (
    ProviderCapabilities,
    SpecialistRequest,
    SpecialistResult,
)


class CodexSdkSpecialistClient:
    """Invoke one schema-bound Codex thread per specialist boundary.

    The deterministic core still parses and validates ``final_response``. Provider-level
    schema enforcement reduces malformed responses but never replaces local validation.
    """

    def __init__(self, *, model: str | None = None) -> None:
        self._model = model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            structured_output=True,
            raw_response_access=True,
            tool_calls=True,
            streaming=True,
            usage_metadata=True,
        )

    def invoke(self, request: SpecialistRequest) -> SpecialistResult:
        try:
            from openai_codex import ApprovalMode, Codex, Sandbox
        except ImportError:
            return SpecialistResult(
                TransportStatus.FAILED,
                None,
                FailureKind.PROFILE_UNAVAILABLE,
                "install the 'v3-codex' optional dependency to use the Codex adapter",
            )

        sandbox = (
            Sandbox.workspace_write if request.may_write_workspace else Sandbox.read_only
        )
        client: Any | None = None
        try:
            client = Codex()
            thread = client.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=str(request.repository_root),
                model=self._model,
                sandbox=sandbox,
                ephemeral=True,
            )
            result = thread.run(
                request.prompt,
                approval_mode=ApprovalMode.deny_all,
                output_schema=request.output_schema,
                sandbox=sandbox,
            )
            if result.final_response is None:
                error = "Codex turn completed without a final response"
                if result.error is not None:
                    error += f" ({type(result.error).__name__})"
                return SpecialistResult(
                    TransportStatus.FAILED,
                    None,
                    FailureKind.INVOCATION_FAILED,
                    error,
                    provider_request_id=result.id,
                    usage=_usage_dict(result.usage),
                )
            return SpecialistResult(
                TransportStatus.SUCCEEDED,
                result.final_response,
                provider_request_id=result.id,
                usage=_usage_dict(result.usage),
            )
        except Exception as exc:  # SDK errors are an external transport boundary.
            return SpecialistResult(
                TransportStatus.FAILED,
                None,
                FailureKind.INVOCATION_FAILED,
                f"Codex SDK invocation failed ({type(exc).__name__})",
            )
        finally:
            if client is not None:
                # A cleanup failure must not replace the invocation result/error.
                with suppress(Exception):
                    client.close()


def _usage_dict(value: Any) -> dict[str, int]:
    if value is None:
        return {}
    usage: dict[str, int] = {}
    for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
        item = getattr(value, key, None)
        if isinstance(item, int) and not isinstance(item, bool):
            usage[key] = item
    return usage
