"""Closed schema and local parser for natural-language intake analysis."""

from __future__ import annotations

import json
from enum import StrEnum
from json import JSONDecodeError
from typing import Any, cast

from .domain import DomainError
from .intake_domain import (
    IntakeAmbiguity,
    IntakeRiskSignals,
    TaskIntakeAnalysis,
    VerificationCommandProposal,
)


class IntakeDefectCode(StrEnum):
    OUTSIDE_ANALYSIS_TEXT = "OUTSIDE_ANALYSIS_TEXT"
    MULTIPLE_ANALYSES = "MULTIPLE_ANALYSES"
    DUPLICATE_FIELD = "DUPLICATE_FIELD"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    INVALID_FIELD_TYPE = "INVALID_FIELD_TYPE"


class IntakeAnalysisError(DomainError):
    """Raised when provider output is not one valid closed intake artifact."""

    def __init__(self, code: IntakeDefectCode, detail: str) -> None:
        super().__init__(f"{code.value}: {detail}")
        self.code = code
        self.detail = detail


class _DuplicateField(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateField(key)
        result[key] = value
    return result


_ROOT_FIELDS = frozenset(
    {
        "normalized_description",
        "acceptance_criteria",
        "candidate_scope",
        "verification_commands",
        "risk_signals",
        "ambiguities",
        "assumptions",
        "repository_evidence",
    }
)
_RISK_FIELDS = frozenset(
    {
        "exact_outcome",
        "unique_repository_evidence",
        "cohesive_scope",
        "focused_verification_available",
        "public_contract_impact",
        "configuration_impact",
        "architecture_or_ownership_impact",
        "security_or_privacy_impact",
        "data_impact",
        "dependency_impact",
        "operational_impact",
        "compatibility_impact",
        "uncertainty_present",
    }
)
_COMMAND_FIELDS = frozenset({"argv", "cwd", "rationale"})
_AMBIGUITY_FIELDS = frozenset({"question", "impact"})


def parse_intake_analysis(raw: str) -> TaskIntakeAnalysis:
    """Parse exactly one provider artifact and reject all schema drift locally."""
    data = _decode_single_object(raw)
    _require_fields(data, _ROOT_FIELDS, "intake analysis")
    risk = _object(data, "risk_signals")
    _require_fields(risk, _RISK_FIELDS, "risk_signals")

    proposals: list[VerificationCommandProposal] = []
    for index, item in enumerate(_objects(data, "verification_commands"), start=1):
        _require_fields(item, _COMMAND_FIELDS, f"verification_commands[{index}]")
        proposals.append(
            VerificationCommandProposal(
                _strings(item, "argv", allow_empty=False),
                _string(item, "cwd"),
                _string(item, "rationale"),
            )
        )

    ambiguities: list[IntakeAmbiguity] = []
    for index, item in enumerate(_objects(data, "ambiguities"), start=1):
        _require_fields(item, _AMBIGUITY_FIELDS, f"ambiguities[{index}]")
        ambiguities.append(
            IntakeAmbiguity(_string(item, "question"), _string(item, "impact"))
        )

    return TaskIntakeAnalysis(
        normalized_description=_string(data, "normalized_description"),
        acceptance_criteria=_strings(data, "acceptance_criteria", allow_empty=False),
        candidate_scope=_strings(data, "candidate_scope", allow_empty=True),
        verification_commands=tuple(proposals),
        risk_signals=IntakeRiskSignals(
            **{name: _boolean(risk, name) for name in sorted(_RISK_FIELDS)}
        ),
        ambiguities=tuple(ambiguities),
        assumptions=_strings(data, "assumptions", allow_empty=True),
        repository_evidence=_strings(data, "repository_evidence", allow_empty=False),
    )


def _decode_single_object(raw: str) -> dict[str, Any]:
    decoder = json.JSONDecoder(object_pairs_hook=_unique_object)
    stripped = raw.lstrip()
    if not stripped:
        raise IntakeAnalysisError(
            IntakeDefectCode.OUTSIDE_ANALYSIS_TEXT, "provider response was empty"
        )
    try:
        value, end = decoder.raw_decode(stripped)
    except _DuplicateField as exc:
        raise IntakeAnalysisError(
            IntakeDefectCode.DUPLICATE_FIELD, f"duplicate field: {exc}"
        ) from exc
    except JSONDecodeError as exc:
        raise IntakeAnalysisError(
            IntakeDefectCode.OUTSIDE_ANALYSIS_TEXT,
            f"response does not begin with one JSON object: {exc.msg}",
        ) from exc
    remainder = stripped[end:].strip()
    if remainder:
        try:
            decoder.raw_decode(remainder)
        except (JSONDecodeError, _DuplicateField) as exc:
            raise IntakeAnalysisError(
                IntakeDefectCode.OUTSIDE_ANALYSIS_TEXT,
                "non-whitespace text follows the intake analysis",
            ) from exc
        raise IntakeAnalysisError(
            IntakeDefectCode.MULTIPLE_ANALYSES,
            "more than one root JSON value was returned",
        )
    if not isinstance(value, dict):
        raise IntakeAnalysisError(
            IntakeDefectCode.INVALID_FIELD_TYPE,
            "intake analysis root must be an object",
        )
    return cast(dict[str, Any], value)


def _require_fields(
    data: dict[str, Any], required: frozenset[str], location: str
) -> None:
    missing = sorted(required - data.keys())
    unknown = sorted(data.keys() - required)
    if missing:
        raise IntakeAnalysisError(
            IntakeDefectCode.MISSING_REQUIRED_FIELD,
            f"{location} is missing: {', '.join(missing)}",
        )
    if unknown:
        raise IntakeAnalysisError(
            IntakeDefectCode.UNKNOWN_FIELD,
            f"{location} contains unknown fields: {', '.join(unknown)}",
        )


def _string(data: dict[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise IntakeAnalysisError(
            IntakeDefectCode.INVALID_FIELD_TYPE,
            f"{key} must be a non-empty string",
        )
    return value.strip()


def _strings(data: dict[str, Any], key: str, *, allow_empty: bool) -> tuple[str, ...]:
    value = data[key]
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        qualifier = (
            "an array of non-empty strings"
            if allow_empty
            else "a non-empty array of non-empty strings"
        )
        raise IntakeAnalysisError(
            IntakeDefectCode.INVALID_FIELD_TYPE, f"{key} must be {qualifier}"
        )
    return tuple(item.strip() for item in value)


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data[key]
    if not isinstance(value, dict):
        raise IntakeAnalysisError(
            IntakeDefectCode.INVALID_FIELD_TYPE, f"{key} must be an object"
        )
    return cast(dict[str, Any], value)


def _objects(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data[key]
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise IntakeAnalysisError(
            IntakeDefectCode.INVALID_FIELD_TYPE, f"{key} must be an array of objects"
        )
    return cast(list[dict[str, Any]], value)


def _boolean(data: dict[str, Any], key: str) -> bool:
    value = data[key]
    if not isinstance(value, bool):
        raise IntakeAnalysisError(
            IntakeDefectCode.INVALID_FIELD_TYPE, f"{key} must be a boolean"
        )
    return value


def intake_analysis_json_schema() -> dict[str, Any]:
    """Return the strict provider-level schema for read-only intake analysis."""
    string = {"type": "string", "minLength": 1}
    strings = {"type": "array", "items": string}
    command = _object_schema(
        {
            "argv": {"type": "array", "items": string, "minItems": 1},
            "cwd": string,
            "rationale": string,
        },
        _COMMAND_FIELDS,
    )
    ambiguity = _object_schema({"question": string, "impact": string}, _AMBIGUITY_FIELDS)
    return _object_schema(
        {
            "normalized_description": string,
            "acceptance_criteria": {**strings, "minItems": 1},
            "candidate_scope": strings,
            "verification_commands": {"type": "array", "items": command},
            "risk_signals": _object_schema(
                {name: {"type": "boolean"} for name in _RISK_FIELDS},
                _RISK_FIELDS,
            ),
            "ambiguities": {"type": "array", "items": ambiguity},
            "assumptions": strings,
            "repository_evidence": {**strings, "minItems": 1},
        },
        _ROOT_FIELDS,
    )


def _object_schema(
    properties: dict[str, Any], required: frozenset[str]
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
        "additionalProperties": False,
    }


__all__ = [
    "IntakeAnalysisError",
    "IntakeDefectCode",
    "intake_analysis_json_schema",
    "parse_intake_analysis",
]
