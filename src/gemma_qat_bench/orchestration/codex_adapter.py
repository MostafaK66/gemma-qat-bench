"""Isolated adapter for the optional OpenAI Codex Python SDK."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .domain import FailureKind, TransportStatus
from .intake import build_intake_prompt
from .intake_artifacts import intake_analysis_json_schema
from .intake_domain import (
    NaturalLanguageTaskRequest,
    TaskIntakeProviderResult,
)
from .specialists import (
    ProviderCapabilities,
    SpecialistRequest,
    SpecialistResult,
)


@dataclass(frozen=True, slots=True)
class _StructuredInvocationResult:
    status: TransportStatus
    raw_response: str | None
    failure_kind: FailureKind | None = None
    error_message: str | None = None
    provider_request_id: str | None = None
    usage: dict[str, int] | None = None


class _CodexStructuredInvoker:
    """Share one schema-bound Codex transport implementation across read-only roles."""

    def __init__(self, *, model: str | None = None) -> None:
        self._model = model

    def invoke(
        self,
        *,
        repository_root: Path,
        prompt: str,
        output_schema: dict[str, Any],
        may_write_workspace: bool,
    ) -> _StructuredInvocationResult:
        try:
            from openai_codex import (
                ApprovalMode,
                Codex,
                Sandbox,
            )
        except ImportError:
            return _StructuredInvocationResult(
                TransportStatus.FAILED,
                None,
                FailureKind.PROFILE_UNAVAILABLE,
                "install the 'v3-codex' optional dependency to use the Codex adapter",
            )

        sandbox = Sandbox.workspace_write if may_write_workspace else Sandbox.read_only
        client: Any | None = None
        try:
            client = Codex()
            thread = client.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=str(repository_root),
                model=self._model,
                sandbox=sandbox,
                ephemeral=True,
            )
            result = thread.run(
                prompt,
                approval_mode=ApprovalMode.deny_all,
                output_schema=output_schema,
                sandbox=sandbox,
            )
            if result.final_response is None:
                error = "Codex turn completed without a final response"
                if result.error is not None:
                    error += f" ({type(result.error).__name__})"
                return _StructuredInvocationResult(
                    TransportStatus.FAILED,
                    None,
                    FailureKind.INVOCATION_FAILED,
                    error,
                    provider_request_id=result.id,
                    usage=_usage_dict(result.usage),
                )
            return _StructuredInvocationResult(
                TransportStatus.SUCCEEDED,
                result.final_response,
                provider_request_id=result.id,
                usage=_usage_dict(result.usage),
            )
        except Exception as exc:  # SDK errors are an external transport boundary.
            return _StructuredInvocationResult(
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


class CodexSdkSpecialistClient:
    """Invoke one schema-bound Codex thread per specialist boundary.

    The deterministic core still parses and validates ``final_response``. Provider-level
    schema enforcement reduces malformed responses but never replaces local validation.
    """

    def __init__(self, *, model: str | None = None) -> None:
        self._invoker = _CodexStructuredInvoker(model=model)

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
        result = self._invoker.invoke(
            repository_root=request.repository_root,
            prompt=request.prompt,
            output_schema=request.output_schema,
            may_write_workspace=request.may_write_workspace,
        )
        return SpecialistResult(
            result.status,
            result.raw_response,
            result.failure_kind,
            result.error_message,
            result.provider_request_id,
            result.usage or {},
        )


class CodexSdkTaskIntentAnalyzer:
    """Run natural-language intake in a schema-bound read-only Codex sandbox."""

    def __init__(self, *, model: str | None = None) -> None:
        self._invoker = _CodexStructuredInvoker(model=model)

    def analyze(self, request: NaturalLanguageTaskRequest) -> TaskIntakeProviderResult:
        result = self._invoker.invoke(
            repository_root=request.repository_root,
            prompt=build_intake_prompt(request),
            output_schema=intake_analysis_json_schema(),
            may_write_workspace=False,
        )
        return TaskIntakeProviderResult(
            result.status,
            result.raw_response,
            result.failure_kind,
            result.error_message,
            result.provider_request_id,
            result.usage or {},
        )


def _usage_dict(value: Any) -> dict[str, int]:
    if value is None:
        return {}
    usage: dict[str, int] = {}
    for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
        item = getattr(value, key, None)
        if isinstance(item, int) and not isinstance(item, bool):
            usage[key] = item
    return usage
