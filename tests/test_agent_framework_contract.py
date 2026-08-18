"""Validate repository contract consistency only.

These tests validate prose contract consistency only. They do not prove actual
LLM schema compliance, runtime enforcement, immutable provenance, or V3
machine-authoritative behavior.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AGENT_ROLES = ".context/AGENT-ROLES.md"
CONTEXT_README = ".context/README.md"
LLMS = "llms.txt"
ORCHESTRATE_PROMPT = ".context/prompts/orchestrate.prompt.md"
REPAIR_PROMPT = ".context/prompts/repair-verification-schema.prompt.md"
SKILL_ORCHESTRATION = ".github/skills/orchestration/SKILL.md"
VERIFIER_AGENT = ".github/agents/verifier.agent.md"


def _read_asset(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _assert_clause(text: str, asset: str, clause: str, needle: str) -> None:
    assert needle in text, (
        f"{asset}: missing contract clause '{clause}' containing {needle!r}"
    )


def _assert_regex(text: str, asset: str, clause: str, pattern: str) -> None:
    assert re.search(pattern, text, flags=re.MULTILINE | re.DOTALL), (
        f"{asset}: missing contract clause '{clause}' matching /{pattern}/"
    )


def test_scenario_1_valid_artifact_contract_shape() -> None:
    text = _read_asset(AGENT_ROLES)
    _assert_clause(
        text,
        AGENT_ROLES,
        "single plain VERIFICATION",
        "Verifier output must be exactly one plain `VERIFICATION` artifact",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "required command_id exactly once",
        "every required `command_id` exactly once",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "exact four assessment fields",
        "exactly `command_id`, `evidence_quality`, "
        "`evidence_assessment`, and `rationale`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "evidence_quality enum",
        "`evidence_quality` must be exactly `sufficient` or `insufficient`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "canonical reconstruction forbidden",
        "do not recreate, overwrite, or reconstruct authoritative canonical "
        "field values",
    )


def test_scenario_2_invalid_enum_taxonomy_and_retry_bound() -> None:
    text = _read_asset(AGENT_ROLES)
    _assert_clause(
        text,
        AGENT_ROLES,
        "INVALID_ENUM_LITERAL taxonomy",
        "`INVALID_ENUM_LITERAL`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "enum pair",
        "`sufficient` or `insufficient`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "single schema retry with unchanged fingerprint",
        "Allow one schema-only retry only when no product files changed and "
        "the bound implementation fingerprint is unchanged",
    )


def test_scenario_3_missing_field_taxonomy_and_same_retry_bound() -> None:
    text = _read_asset(AGENT_ROLES)
    _assert_clause(
        text,
        AGENT_ROLES,
        "MISSING_REQUIRED_FIELD taxonomy",
        "`MISSING_REQUIRED_FIELD`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "required assessment field set",
        "exactly `command_id`, `evidence_quality`, "
        "`evidence_assessment`, and `rationale`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "bounded schema repair condition",
        "Allow one schema-only retry only when no product files changed and "
        "the bound implementation fingerprint is unchanged",
    )


def test_scenario_4_outside_text_and_no_gate2_inference() -> None:
    text = _read_asset(AGENT_ROLES)
    _assert_clause(
        text,
        AGENT_ROLES,
        "authoritative single plain VERIFICATION output",
        "Verifier output must be exactly one plain `VERIFICATION` artifact",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "no outside text",
        "contain no preamble, epilogue, outside prose",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "OUTSIDE_ARTIFACT_TEXT taxonomy",
        "`OUTSIDE_ARTIFACT_TEXT`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "malformed output has no Gate 2 inference",
        "When malformed, no Gate 2 inference follows the malformed output",
    )


def test_scenario_5_qualitative_language_allowed_but_reconstruction_forbidden(
) -> None:
    text = _read_asset(AGENT_ROLES)
    _assert_clause(
        text,
        AGENT_ROLES,
        "qualitative interpretation limited to assessment and rationale fields",
        "only through `evidence_assessment` and `rationale`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "qualitative interpretation in assessment and rationale is allowed",
        "Compliant qualitative interpretation in `evidence_assessment` and "
        "`rationale`",
    )
    _assert_regex(
        text,
        AGENT_ROLES,
        "qualitative terms explicitly allowed",
        r"including words such as success, failure, absence, completeness, "
        r"sufficiency, or insufficiency\) is allowed",
    )
    _assert_regex(
        text,
        AGENT_ROLES,
        "canonical command/result/exit/output reconstruction forbidden",
        r"must not restate, reconstruct, or create a competing authoritative "
        r"representation.*exact commands.*execution results, exit-code "
        r"values, raw/minimal output excerpts",
    )


def test_scenario_6_post_command_drift_contract() -> None:
    text = _read_asset(AGENT_ROLES)
    _assert_clause(
        text,
        AGENT_ROLES,
        "capture fingerprint before commands",
        "capture fingerprint and bind ledger before any brokered commands",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "post-command pre-verifier recheck",
        "After commands and before Verifier delegation, recalculate "
        "fingerprint",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "mismatch stale and block verifier",
        "mark current ledger stale, preserve history, do not delegate "
        "Verifier",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "fresh verification after scope reconciliation",
        "require fresh authorized verification after scope reconciliation",
    )


def test_scenario_7_post_verifier_drift_contract() -> None:
    text = _read_asset(AGENT_ROLES)
    _assert_clause(
        text,
        AGENT_ROLES,
        "post-verifier pre-gate2 recheck",
        "After Verifier and before Gate 2 acceptance, recalculate "
        "fingerprint",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "mismatch cannot accept verifier result",
        "do not accept its result for current content",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "reviewer consumes identity-stable gate2 evidence",
        "Reviewer may consume only identity-stable Gate 2 accepted evidence",
    )


def test_scenario_8_recovery_drift_contract() -> None:
    text = _read_asset(AGENT_ROLES)
    _assert_clause(
        text,
        AGENT_ROLES,
        "pre-schema-repair recheck",
        "Before schema-repair delegation, recalculate fingerprint",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "mismatch does not repair or consume retry",
        "mark stale, do not repair, do not consume retry budget, fail "
        "closed",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "old verifier evidence kept historical",
        "preserve the returned Verifier artifact historically bound to its "
        "old fingerprint",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "fresh verification required after drift",
        "requires fresh authorized verification after scope reconciliation",
    )


def test_scenario_9_fingerprint_definition_contract() -> None:
    text = _read_asset(AGENT_ROLES)
    _assert_clause(
        text,
        AGENT_ROLES,
        "algorithm identity",
        "Algorithm identity: `implementation-fingerprint-v1`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "sha-256 outer hash",
        "Digest: SHA-256 outer hash",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "normalized slash paths and deterministic lexical sort",
        "Path normalization: repository-relative with `/` separators and "
        "deterministic lexical sort",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "state literals present deleted",
        "`state` literals: `present` or `deleted`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "present working-tree content identity from git hash-object",
        "Present file `content_identity`: read-only Git object hash from "
        "`git hash-object --no-filters -- <path>` where available",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "deleted sentinel",
        "Deleted file `content_identity`: stable explicit sentinel `DELETED`",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "authorized untracked new files included",
        "Include authorized untracked new files",
    )
    _assert_clause(
        text,
        AGENT_ROLES,
        "git hash-object identity",
        "git hash-object --no-filters -- <path>",
    )


def test_cross_file_inventory_includes_repair_schema_prompt() -> None:
    context_readme = _read_asset(CONTEXT_README)
    llms = _read_asset(LLMS)
    _assert_clause(
        context_readme,
        CONTEXT_README,
        "repair prompt inventory",
        "repair-verification-schema.prompt.md",
    )
    _assert_clause(
        llms,
        LLMS,
        "repair prompt inventory",
        "repair-verification-schema.prompt.md",
    )


def test_cross_file_verifier_agent_points_to_verify_prompt() -> None:
    verifier_agent = _read_asset(VERIFIER_AGENT)
    _assert_clause(
        verifier_agent,
        VERIFIER_AGENT,
        "verifier prompt linkage",
        "Follow `.context/prompts/verify.prompt.md`",
    )


def test_cross_file_unchanged_fingerprint_schema_retry_condition_preserved() -> None:
    orchestrate = _read_asset(ORCHESTRATE_PROMPT)
    skill = _read_asset(SKILL_ORCHESTRATION)
    _assert_regex(
        orchestrate,
        ORCHESTRATE_PROMPT,
        "schema retry requires no product change and unchanged fingerprint",
        r"schema-only retry only when no product files changed and "
        r"fingerprint remains unchanged",
    )
    _assert_regex(
        skill,
        SKILL_ORCHESTRATION,
        "schema retry requires no product change and unchanged fingerprint",
        r"schema-only retry only when no product file changed and the "
        r"fingerprint remains unchanged",
    )


def test_cross_file_repair_prompt_keeps_precondition_language() -> None:
    repair_prompt = _read_asset(REPAIR_PROMPT)
    _assert_clause(
        repair_prompt,
        REPAIR_PROMPT,
        "pre-repair fingerprint recalculation",
        "Recalculate implementation fingerprint before repair delegation",
    )
    _assert_clause(
        repair_prompt,
        REPAIR_PROMPT,
        "retry blocked on fingerprint mismatch",
        "If fingerprint changed: mark prior evidence stale, do not run repair, "
        "do not consume schema-retry budget",
    )

