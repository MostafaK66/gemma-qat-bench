"""Strict specialist artifact schemas and deterministic JSON validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, StrEnum
from json import JSONDecodeError
from typing import Any, cast

from .domain import (
    ArtifactDefect,
    ArtifactKind,
    ArtifactValidationResult,
    EvidenceQuality,
    Gate1Verdict,
    Gate2Verdict,
    Gate3Verdict,
    ResolutionClass,
    TaskId,
    WorkflowDepth,
)


class DefectCode(StrEnum):
    OUTSIDE_ARTIFACT_TEXT = "OUTSIDE_ARTIFACT_TEXT"
    MULTIPLE_ARTIFACTS = "MULTIPLE_ARTIFACTS"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    DUPLICATE_FIELD = "DUPLICATE_FIELD"
    INVALID_FIELD_TYPE = "INVALID_FIELD_TYPE"
    INVALID_ENUM_LITERAL = "INVALID_ENUM_LITERAL"
    INVALID_ASSESSMENT_FIELD_SET = "INVALID_ASSESSMENT_FIELD_SET"
    MISSING_DUPLICATE_UNKNOWN_OR_STALE_COMMAND_ID = (
        "MISSING_DUPLICATE_UNKNOWN_OR_STALE_COMMAND_ID"
    )
    PROHIBITED_CANONICAL_RECONSTRUCTION = "PROHIBITED_CANONICAL_RECONSTRUCTION"


class ImplementationDisposition(StrEnum):
    COMPLETED = "COMPLETED"
    HUMAN_INTENT_REQUIRED = "HUMAN_INTENT_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class PlanArtifact:
    task_id: TaskId
    goal: str
    current_behavior: str
    owning_responsibility: str
    files_expected_to_change: tuple[str, ...]
    implementation_steps: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    risks: tuple[str, ...]
    out_of_scope: tuple[str, ...]
    open_questions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanFinding:
    finding_id: str
    classification: ResolutionClass
    decision_question: str
    impact_scope: str
    evidence_basis: str
    required_correction: str
    why_not_uniquely_resolved: str


@dataclass(frozen=True, slots=True)
class PlanCritiqueArtifact:
    task_id: TaskId
    plan_version: int
    verdict: Gate1Verdict
    blocking_findings: tuple[PlanFinding, ...]
    suggestions: tuple[str, ...]
    evidence_checked: tuple[str, ...]
    residual_risks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ImplementationArtifact:
    task_id: TaskId
    depth: WorkflowDepth
    plan_reference: str
    iteration: int
    disposition: ImplementationDisposition
    steps_implemented: tuple[str, ...]
    files_changed: tuple[str, ...]
    tests_changed: tuple[str, ...]
    documentation_changes: tuple[str, ...]
    deviations: tuple[str, ...]
    blockers: tuple[str, ...]
    residual_risks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    command_id: str
    evidence_quality: EvidenceQuality
    evidence_assessment: str
    rationale: str


@dataclass(frozen=True, slots=True)
class VerificationFinding:
    finding_id: str
    finding_kind: str
    resolution_class: ResolutionClass
    affected_criterion: str
    evidence: str
    required_next_action: str


@dataclass(frozen=True, slots=True)
class VerificationArtifact:
    task_id: TaskId
    depth: WorkflowDepth
    plan_reference: str
    implementation_iteration: int
    verification_iteration: int
    verdict: Gate2Verdict
    acceptance_checks: tuple[str, ...]
    command_assessments: tuple[EvidenceAssessment, ...]
    blocking_findings: tuple[VerificationFinding, ...]
    environment_limitations: tuple[str, ...]
    residual_risks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    finding_id: str
    finding_kind: str
    resolution_class: ResolutionClass
    severity: str
    location: str
    problem: str
    impact: str
    evidence_basis: str
    required_next_action: str


@dataclass(frozen=True, slots=True)
class ReviewArtifact:
    task_id: TaskId
    plan_version: int
    implementation_iteration: int
    verdict: Gate3Verdict
    evidence_reviewed: tuple[str, ...]
    blocking_findings: tuple[ReviewFinding, ...]
    scope_assessment: str
    quality_assessment: str
    residual_risks: tuple[str, ...]


SpecialistArtifact = (
    PlanArtifact
    | PlanCritiqueArtifact
    | ImplementationArtifact
    | VerificationArtifact
    | ReviewArtifact
)


_PROHIBITED_CANONICAL_KEYS = frozenset(
    {
        "required_command_set_source",
        "exact_executed_command",
        "exact_argv",
        "working_directory",
        "execution_result",
        "exit_code",
        "output_handling",
        "permitted_evidence_material",
    }
)


class _DuplicateField(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateField(key)
        result[key] = value
    return result


def _defect(code: DefectCode, detail: str) -> ArtifactDefect:
    return ArtifactDefect(code.value, detail)


def _decode_single_object(
    raw: str,
) -> tuple[dict[str, Any] | None, ArtifactDefect | None]:
    decoder = json.JSONDecoder(object_pairs_hook=_unique_object)
    stripped = raw.lstrip()
    if not stripped:
        return None, _defect(DefectCode.OUTSIDE_ARTIFACT_TEXT, "empty provider response")
    try:
        value, end = decoder.raw_decode(stripped)
    except _DuplicateField as exc:
        return None, _defect(DefectCode.DUPLICATE_FIELD, f"duplicate field: {exc}")
    except JSONDecodeError as exc:
        return None, _defect(
            DefectCode.OUTSIDE_ARTIFACT_TEXT,
            f"response does not start with one JSON artifact: {exc.msg}",
        )
    remainder = stripped[end:].strip()
    if remainder:
        try:
            decoder.raw_decode(remainder)
        except (JSONDecodeError, _DuplicateField):
            return None, _defect(
                DefectCode.OUTSIDE_ARTIFACT_TEXT,
                "non-whitespace text follows the JSON artifact",
            )
        return None, _defect(
            DefectCode.MULTIPLE_ARTIFACTS, "more than one root JSON value was returned"
        )
    if not isinstance(value, dict):
        return None, _defect(
            DefectCode.INVALID_FIELD_TYPE, "root artifact must be an object"
        )
    return cast(dict[str, Any], value), None


def _check_field_set(
    data: dict[str, Any], required: frozenset[str]
) -> tuple[ArtifactDefect, ...]:
    defects: list[ArtifactDefect] = []
    missing = sorted(required - data.keys())
    unknown = sorted(data.keys() - required)
    if missing:
        defects.append(
            _defect(
                DefectCode.MISSING_REQUIRED_FIELD,
                "missing fields: " + ", ".join(missing),
            )
        )
    if unknown:
        defects.append(
            _defect(DefectCode.UNKNOWN_FIELD, "unknown fields: " + ", ".join(unknown))
        )
    return tuple(defects)


def _contains_prohibited_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in _PROHIBITED_CANONICAL_KEYS:
                return str(key)
            found = _contains_prohibited_key(nested)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _contains_prohibited_key(nested)
            if found:
                return found
    return None


def _string(data: dict[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{key} must be a non-empty string")
    return str(value)


def _integer(data: dict[str, Any], key: str) -> int:
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise TypeError(f"{key} must be a positive integer")
    return int(value)


def _strings(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data[key]
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise TypeError(f"{key} must be an array of non-empty strings")
    return tuple(value)


def _objects(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data[key]
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise TypeError(f"{key} must be an array of objects")
    return cast(list[dict[str, Any]], value)


def _enum(enum_type: type[Enum], data: dict[str, Any], key: str) -> Any:
    value = data[key]
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string enum literal")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"invalid {key} literal: {value!r}") from exc


_PLAN_FIELDS = frozenset(
    {
        "task_id",
        "goal",
        "current_behavior",
        "owning_responsibility",
        "files_expected_to_change",
        "implementation_steps",
        "acceptance_criteria",
        "risks",
        "out_of_scope",
        "open_questions",
    }
)
_CRITIQUE_FIELDS = frozenset(
    {
        "task_id",
        "plan_version",
        "verdict",
        "blocking_findings",
        "suggestions",
        "evidence_checked",
        "residual_risks",
    }
)
_IMPLEMENTATION_FIELDS = frozenset(
    {
        "task_id",
        "depth",
        "plan_reference",
        "iteration",
        "disposition",
        "steps_implemented",
        "files_changed",
        "tests_changed",
        "documentation_changes",
        "deviations",
        "blockers",
        "residual_risks",
    }
)
_VERIFICATION_FIELDS = frozenset(
    {
        "task_id",
        "depth",
        "plan_reference",
        "implementation_iteration",
        "verification_iteration",
        "verdict",
        "acceptance_checks",
        "command_assessments",
        "blocking_findings",
        "environment_limitations",
        "residual_risks",
    }
)
_REVIEW_FIELDS = frozenset(
    {
        "task_id",
        "plan_version",
        "implementation_iteration",
        "verdict",
        "evidence_reviewed",
        "blocking_findings",
        "scope_assessment",
        "quality_assessment",
        "residual_risks",
    }
)


def _parse_plan(data: dict[str, Any]) -> PlanArtifact:
    return PlanArtifact(
        TaskId(_string(data, "task_id")),
        _string(data, "goal"),
        _string(data, "current_behavior"),
        _string(data, "owning_responsibility"),
        _strings(data, "files_expected_to_change"),
        _strings(data, "implementation_steps"),
        _strings(data, "acceptance_criteria"),
        _strings(data, "risks"),
        _strings(data, "out_of_scope"),
        _strings(data, "open_questions"),
    )


def _parse_critique(data: dict[str, Any]) -> PlanCritiqueArtifact:
    required = frozenset(
        {
            "finding_id",
            "classification",
            "decision_question",
            "impact_scope",
            "evidence_basis",
            "required_correction",
            "why_not_uniquely_resolved",
        }
    )
    findings: list[PlanFinding] = []
    for item in _objects(data, "blocking_findings"):
        defects = _check_field_set(item, required)
        if defects:
            raise TypeError(defects[0].detail)
        findings.append(
            PlanFinding(
                _string(item, "finding_id"),
                _enum(ResolutionClass, item, "classification"),
                _string(item, "decision_question"),
                _string(item, "impact_scope"),
                _string(item, "evidence_basis"),
                _string(item, "required_correction"),
                _string(item, "why_not_uniquely_resolved"),
            )
        )
    return PlanCritiqueArtifact(
        TaskId(_string(data, "task_id")),
        _integer(data, "plan_version"),
        _enum(Gate1Verdict, data, "verdict"),
        tuple(findings),
        _strings(data, "suggestions"),
        _strings(data, "evidence_checked"),
        _strings(data, "residual_risks"),
    )


def _parse_implementation(data: dict[str, Any]) -> ImplementationArtifact:
    return ImplementationArtifact(
        TaskId(_string(data, "task_id")),
        _enum(WorkflowDepth, data, "depth"),
        _string(data, "plan_reference"),
        _integer(data, "iteration"),
        _enum(ImplementationDisposition, data, "disposition"),
        _strings(data, "steps_implemented"),
        _strings(data, "files_changed"),
        _strings(data, "tests_changed"),
        _strings(data, "documentation_changes"),
        _strings(data, "deviations"),
        _strings(data, "blockers"),
        _strings(data, "residual_risks"),
    )


def _parse_verification(
    data: dict[str, Any], expected_command_ids: tuple[str, ...]
) -> VerificationArtifact:
    assessment_fields = frozenset(
        {"command_id", "evidence_quality", "evidence_assessment", "rationale"}
    )
    assessments: list[EvidenceAssessment] = []
    ids: list[str] = []
    for item in _objects(data, "command_assessments"):
        if set(item) != assessment_fields:
            raise _AssessmentFieldSetError(
                "command assessment fields must be exactly: "
                + ", ".join(sorted(assessment_fields))
            )
        command_id = _string(item, "command_id")
        ids.append(command_id)
        assessments.append(
            EvidenceAssessment(
                command_id,
                _enum(EvidenceQuality, item, "evidence_quality"),
                _string(item, "evidence_assessment"),
                _string(item, "rationale"),
            )
        )
    if sorted(ids) != sorted(expected_command_ids) or len(ids) != len(set(ids)):
        raise _CommandIdentityError(
            "assessment command IDs must match the current required set exactly once"
        )

    finding_fields = frozenset(
        {
            "finding_id",
            "finding_kind",
            "resolution_class",
            "affected_criterion",
            "evidence",
            "required_next_action",
        }
    )
    findings: list[VerificationFinding] = []
    for item in _objects(data, "blocking_findings"):
        defects = _check_field_set(item, finding_fields)
        if defects:
            raise TypeError(defects[0].detail)
        findings.append(
            VerificationFinding(
                _string(item, "finding_id"),
                _string(item, "finding_kind"),
                _enum(ResolutionClass, item, "resolution_class"),
                _string(item, "affected_criterion"),
                _string(item, "evidence"),
                _string(item, "required_next_action"),
            )
        )
    return VerificationArtifact(
        TaskId(_string(data, "task_id")),
        _enum(WorkflowDepth, data, "depth"),
        _string(data, "plan_reference"),
        _integer(data, "implementation_iteration"),
        _integer(data, "verification_iteration"),
        _enum(Gate2Verdict, data, "verdict"),
        _strings(data, "acceptance_checks"),
        tuple(assessments),
        tuple(findings),
        _strings(data, "environment_limitations"),
        _strings(data, "residual_risks"),
    )


def _parse_review(data: dict[str, Any]) -> ReviewArtifact:
    finding_fields = frozenset(
        {
            "finding_id",
            "finding_kind",
            "resolution_class",
            "severity",
            "location",
            "problem",
            "impact",
            "evidence_basis",
            "required_next_action",
        }
    )
    findings: list[ReviewFinding] = []
    for item in _objects(data, "blocking_findings"):
        defects = _check_field_set(item, finding_fields)
        if defects:
            raise TypeError(defects[0].detail)
        findings.append(
            ReviewFinding(
                _string(item, "finding_id"),
                _string(item, "finding_kind"),
                _enum(ResolutionClass, item, "resolution_class"),
                _string(item, "severity"),
                _string(item, "location"),
                _string(item, "problem"),
                _string(item, "impact"),
                _string(item, "evidence_basis"),
                _string(item, "required_next_action"),
            )
        )
    return ReviewArtifact(
        TaskId(_string(data, "task_id")),
        _integer(data, "plan_version"),
        _integer(data, "implementation_iteration"),
        _enum(Gate3Verdict, data, "verdict"),
        _strings(data, "evidence_reviewed"),
        tuple(findings),
        _string(data, "scope_assessment"),
        _string(data, "quality_assessment"),
        _strings(data, "residual_risks"),
    )


class _AssessmentFieldSetError(TypeError):
    pass


class _CommandIdentityError(TypeError):
    pass


_FIELD_SETS = {
    ArtifactKind.PLAN: _PLAN_FIELDS,
    ArtifactKind.PLAN_CRITIQUE: _CRITIQUE_FIELDS,
    ArtifactKind.IMPLEMENTATION: _IMPLEMENTATION_FIELDS,
    ArtifactKind.VERIFICATION: _VERIFICATION_FIELDS,
    ArtifactKind.REVIEW: _REVIEW_FIELDS,
}


def validate_artifact(
    kind: ArtifactKind,
    raw: str,
    *,
    expected_command_ids: tuple[str, ...] = (),
) -> ArtifactValidationResult:
    """Parse exactly one JSON artifact and enforce its semantic boundary schema."""
    data, decode_defect = _decode_single_object(raw)
    if decode_defect:
        return ArtifactValidationResult(kind, False, None, (decode_defect,))
    if data is None:  # defensive guard; the decoder contract excludes this branch
        raise RuntimeError("artifact decoder returned neither data nor a defect")
    field_defects = _check_field_set(data, _FIELD_SETS[kind])
    if field_defects:
        return ArtifactValidationResult(kind, False, None, field_defects)
    prohibited = _contains_prohibited_key(data)
    if prohibited and kind in {ArtifactKind.VERIFICATION, ArtifactKind.REVIEW}:
        return ArtifactValidationResult(
            kind,
            False,
            None,
            (
                _defect(
                    DefectCode.PROHIBITED_CANONICAL_RECONSTRUCTION,
                    f"specialist output contains canonical ledger field: {prohibited}",
                ),
            ),
        )
    try:
        if kind is ArtifactKind.PLAN:
            artifact: SpecialistArtifact = _parse_plan(data)
        elif kind is ArtifactKind.PLAN_CRITIQUE:
            artifact = _parse_critique(data)
        elif kind is ArtifactKind.IMPLEMENTATION:
            artifact = _parse_implementation(data)
        elif kind is ArtifactKind.VERIFICATION:
            artifact = _parse_verification(data, expected_command_ids)
        else:
            artifact = _parse_review(data)
    except _AssessmentFieldSetError as exc:
        defect = _defect(DefectCode.INVALID_ASSESSMENT_FIELD_SET, str(exc))
        return ArtifactValidationResult(kind, False, None, (defect,))
    except _CommandIdentityError as exc:
        defect = _defect(
            DefectCode.MISSING_DUPLICATE_UNKNOWN_OR_STALE_COMMAND_ID, str(exc)
        )
        return ArtifactValidationResult(kind, False, None, (defect,))
    except ValueError as exc:
        defect = _defect(DefectCode.INVALID_ENUM_LITERAL, str(exc))
        return ArtifactValidationResult(kind, False, None, (defect,))
    except (KeyError, TypeError) as exc:
        defect = _defect(DefectCode.INVALID_FIELD_TYPE, str(exc))
        return ArtifactValidationResult(kind, False, None, (defect,))
    return ArtifactValidationResult(kind, True, artifact)


def _object_schema(
    properties: dict[str, Any], required: frozenset[str]
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
        "additionalProperties": False,
    }


_STRING = {"type": "string", "minLength": 1}
_STRINGS = {"type": "array", "items": _STRING}
_POSITIVE_INT = {"type": "integer", "minimum": 1}


def artifact_json_schema(
    kind: ArtifactKind, *, expected_command_ids: tuple[str, ...] = ()
) -> dict[str, Any]:
    """Return the provider-level JSON schema for an artifact kind."""
    if kind is ArtifactKind.PLAN:
        return _object_schema(
            {
                "task_id": _STRING,
                "goal": _STRING,
                "current_behavior": _STRING,
                "owning_responsibility": _STRING,
                "files_expected_to_change": _STRINGS,
                "implementation_steps": _STRINGS,
                "acceptance_criteria": _STRINGS,
                "risks": _STRINGS,
                "out_of_scope": _STRINGS,
                "open_questions": _STRINGS,
            },
            _PLAN_FIELDS,
        )
    if kind is ArtifactKind.PLAN_CRITIQUE:
        finding_fields = frozenset(
            {
                "finding_id",
                "classification",
                "decision_question",
                "impact_scope",
                "evidence_basis",
                "required_correction",
                "why_not_uniquely_resolved",
            }
        )
        finding = _object_schema(
            {
                key: (
                    {"type": "string", "enum": [item.value for item in ResolutionClass]}
                    if key == "classification"
                    else _STRING
                )
                for key in finding_fields
            },
            finding_fields,
        )
        return _object_schema(
            {
                "task_id": _STRING,
                "plan_version": _POSITIVE_INT,
                "verdict": {
                    "type": "string",
                    "enum": [item.value for item in Gate1Verdict],
                },
                "blocking_findings": {"type": "array", "items": finding},
                "suggestions": _STRINGS,
                "evidence_checked": _STRINGS,
                "residual_risks": _STRINGS,
            },
            _CRITIQUE_FIELDS,
        )
    if kind is ArtifactKind.IMPLEMENTATION:
        properties: dict[str, Any] = {key: _STRINGS for key in _IMPLEMENTATION_FIELDS}
        properties.update(
            {
                "task_id": _STRING,
                "depth": {
                    "type": "string",
                    "enum": [item.value for item in WorkflowDepth],
                },
                "plan_reference": _STRING,
                "iteration": _POSITIVE_INT,
                "disposition": {
                    "type": "string",
                    "enum": [item.value for item in ImplementationDisposition],
                },
            }
        )
        return _object_schema(properties, _IMPLEMENTATION_FIELDS)
    if kind is ArtifactKind.VERIFICATION:
        assessment_fields = frozenset(
            {"command_id", "evidence_quality", "evidence_assessment", "rationale"}
        )
        command_id_schema: dict[str, Any] = _STRING
        if expected_command_ids:
            command_id_schema = {"type": "string", "enum": list(expected_command_ids)}
        assessment = _object_schema(
            {
                "command_id": command_id_schema,
                "evidence_quality": {
                    "type": "string",
                    "enum": [item.value for item in EvidenceQuality],
                },
                "evidence_assessment": _STRING,
                "rationale": _STRING,
            },
            assessment_fields,
        )
        finding_fields = frozenset(
            {
                "finding_id",
                "finding_kind",
                "resolution_class",
                "affected_criterion",
                "evidence",
                "required_next_action",
            }
        )
        finding = _object_schema(
            {
                key: (
                    {"type": "string", "enum": [item.value for item in ResolutionClass]}
                    if key == "resolution_class"
                    else _STRING
                )
                for key in finding_fields
            },
            finding_fields,
        )
        return _object_schema(
            {
                "task_id": _STRING,
                "depth": {
                    "type": "string",
                    "enum": [item.value for item in WorkflowDepth],
                },
                "plan_reference": _STRING,
                "implementation_iteration": _POSITIVE_INT,
                "verification_iteration": _POSITIVE_INT,
                "verdict": {
                    "type": "string",
                    "enum": [item.value for item in Gate2Verdict],
                },
                "acceptance_checks": _STRINGS,
                "command_assessments": {
                    "type": "array",
                    "items": assessment,
                    "minItems": len(expected_command_ids),
                    "maxItems": len(expected_command_ids),
                },
                "blocking_findings": {"type": "array", "items": finding},
                "environment_limitations": _STRINGS,
                "residual_risks": _STRINGS,
            },
            _VERIFICATION_FIELDS,
        )
    finding_fields = frozenset(
        {
            "finding_id",
            "finding_kind",
            "resolution_class",
            "severity",
            "location",
            "problem",
            "impact",
            "evidence_basis",
            "required_next_action",
        }
    )
    finding = _object_schema(
        {
            key: (
                {"type": "string", "enum": [item.value for item in ResolutionClass]}
                if key == "resolution_class"
                else _STRING
            )
            for key in finding_fields
        },
        finding_fields,
    )
    return _object_schema(
        {
            "task_id": _STRING,
            "plan_version": _POSITIVE_INT,
            "implementation_iteration": _POSITIVE_INT,
            "verdict": {"type": "string", "enum": [item.value for item in Gate3Verdict]},
            "evidence_reviewed": _STRINGS,
            "blocking_findings": {"type": "array", "items": finding},
            "scope_assessment": _STRING,
            "quality_assessment": _STRING,
            "residual_risks": _STRINGS,
        },
        _REVIEW_FIELDS,
    )
