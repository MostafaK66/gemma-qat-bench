"""Optional read-only live smoke test; excluded from deterministic acceptance gates."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from gemma_qat_bench.orchestration.artifacts import validate_artifact
from gemma_qat_bench.orchestration.codex_adapter import CodexSdkSpecialistClient
from gemma_qat_bench.orchestration.domain import (
    ArtifactKind,
    SpecialistInvocation,
    SpecialistRole,
    TransportStatus,
)
from gemma_qat_bench.orchestration.specialists import build_specialist_request

pytestmark = pytest.mark.v3_live


@pytest.mark.skipif(
    os.getenv("RUN_CODEX_LIVE") != "1",
    reason="set RUN_CODEX_LIVE=1 to authorize the optional read-only provider smoke test",
)
def test_codex_planner_live_schema_boundary() -> None:
    repository = Path(os.environ["V3_LIVE_REPOSITORY_ROOT"]).resolve()
    invocation = SpecialistInvocation(
        "LIVE-SMOKE-planner-1", SpecialistRole.PLANNER, ArtifactKind.PLAN, 1
    )
    request = build_specialist_request(
        invocation=invocation,
        repository_root=repository,
        context={
            "task_id": "LIVE-SMOKE",
            "description": "Read the repository and propose a no-change smoke-test plan.",
            "acceptance_criteria": ["No repository files are changed."],
            "plan_version": 1,
        },
    )
    result = CodexSdkSpecialistClient().invoke(request)
    assert result.status is TransportStatus.SUCCEEDED
    assert result.raw_response is not None
    validation = validate_artifact(ArtifactKind.PLAN, result.raw_response)
    assert validation.valid
