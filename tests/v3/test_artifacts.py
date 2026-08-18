from __future__ import annotations

import json
from typing import Any

import pytest

from gemma_qat_bench.orchestration.artifacts import (
    DefectCode,
    VerificationArtifact,
    artifact_json_schema,
    validate_artifact,
)
from gemma_qat_bench.orchestration.domain import ArtifactKind


def verification(**updates: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "task_id": "T-1",
        "depth": "FAST",
        "plan_reference": "FAST-INTAKE",
        "implementation_iteration": 1,
        "verification_iteration": 1,
        "verdict": "PASSED",
        "acceptance_checks": ["criterion satisfied"],
        "command_assessments": [
            {
                "command_id": "CMD-001",
                "evidence_quality": "sufficient",
                "evidence_assessment": "passed",
                "rationale": "canonical evidence is successful",
            }
        ],
        "blocking_findings": [],
        "environment_limitations": [],
        "residual_risks": [],
    }
    value.update(updates)
    return value


def defect(raw: str) -> str:
    result = validate_artifact(
        ArtifactKind.VERIFICATION, raw, expected_command_ids=("CMD-001",)
    )
    assert not result.valid
    return result.defects[0].code


def test_valid_verification_is_typed() -> None:
    result = validate_artifact(
        ArtifactKind.VERIFICATION,
        json.dumps(verification()),
        expected_command_ids=("CMD-001",),
    )
    assert result.valid
    assert isinstance(result.artifact, VerificationArtifact)
    assert result.artifact.verdict.value == "PASSED"


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("preamble " + json.dumps(verification()), DefectCode.OUTSIDE_ARTIFACT_TEXT),
        (json.dumps(verification()) + " epilogue", DefectCode.OUTSIDE_ARTIFACT_TEXT),
        (json.dumps(verification()) + " {}", DefectCode.MULTIPLE_ARTIFACTS),
        ('{"task_id":"T","task_id":"T2"}', DefectCode.DUPLICATE_FIELD),
    ],
)
def test_wrapper_and_multiple_artifact_regressions(raw: str, code: DefectCode) -> None:
    assert defect(raw) == code.value


def test_missing_field_is_not_inferred() -> None:
    value = verification()
    del value["verdict"]
    assert defect(json.dumps(value)) == DefectCode.MISSING_REQUIRED_FIELD.value


def test_invalid_enum_is_rejected() -> None:
    assert defect(json.dumps(verification(verdict="MAYBE"))) == (
        DefectCode.INVALID_ENUM_LITERAL.value
    )


def test_assessment_fields_must_be_exact() -> None:
    value = verification()
    value["command_assessments"][0]["exit_code"] = 0
    assert (
        defect(json.dumps(value)) == DefectCode.PROHIBITED_CANONICAL_RECONSTRUCTION.value
    )

    value = verification()
    del value["command_assessments"][0]["rationale"]
    assert defect(json.dumps(value)) == DefectCode.INVALID_ASSESSMENT_FIELD_SET.value


@pytest.mark.parametrize(
    "assessments",
    [
        [],
        [
            {
                "command_id": "CMD-UNKNOWN",
                "evidence_quality": "sufficient",
                "evidence_assessment": "passed",
                "rationale": "wrong command",
            }
        ],
        [
            {
                "command_id": "CMD-001",
                "evidence_quality": "sufficient",
                "evidence_assessment": "passed",
                "rationale": "one",
            },
            {
                "command_id": "CMD-001",
                "evidence_quality": "sufficient",
                "evidence_assessment": "passed",
                "rationale": "duplicate",
            },
        ],
    ],
)
def test_command_ids_match_current_set_exactly_once(
    assessments: list[dict[str, str]],
) -> None:
    assert defect(json.dumps(verification(command_assessments=assessments))) == (
        DefectCode.MISSING_DUPLICATE_UNKNOWN_OR_STALE_COMMAND_ID.value
    )


def test_provider_schema_is_closed_and_command_bound() -> None:
    schema = artifact_json_schema(
        ArtifactKind.VERIFICATION, expected_command_ids=("CMD-001",)
    )
    assert schema["additionalProperties"] is False
    assessment = schema["properties"]["command_assessments"]
    assert assessment["minItems"] == 1
    assert assessment["items"]["properties"]["command_id"]["enum"] == ["CMD-001"]
