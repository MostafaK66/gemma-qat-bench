from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from gemma_qat_bench.orchestration.domain import (
    DomainError,
    FailureKind,
    OutputHandling,
    RiskLevel,
    TaskId,
    TaskSpec,
    TransportStatus,
    WorkflowDepth,
)
from gemma_qat_bench.orchestration.intake import (
    GitRepositoryLocator,
    IntakeClarificationRequired,
    IntakeProviderFailure,
    ScriptedIntakeResponse,
    ScriptedTaskIntentAnalyzer,
    TaskCompiler,
    TaskIdGenerator,
    TaskIntakeService,
)
from gemma_qat_bench.orchestration.intake_artifacts import (
    IntakeAnalysisError,
    intake_analysis_json_schema,
    parse_intake_analysis,
)
from gemma_qat_bench.orchestration.intake_domain import (
    NaturalLanguageTaskRequest,
)


def risk_signals(**updates: bool) -> dict[str, bool]:
    values = {
        "exact_outcome": True,
        "unique_repository_evidence": True,
        "cohesive_scope": True,
        "focused_verification_available": True,
        "public_contract_impact": False,
        "configuration_impact": False,
        "architecture_or_ownership_impact": False,
        "security_or_privacy_impact": False,
        "data_impact": False,
        "dependency_impact": False,
        "operational_impact": False,
        "compatibility_impact": False,
        "uncertainty_present": False,
    }
    values.update(updates)
    return values


def analysis(**updates: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "normalized_description": "Update the product message.",
        "acceptance_criteria": [
            "The message is updated.",
            "The focused test passes.",
        ],
        "candidate_scope": ["src/product.py", "tests/test_product.py"],
        "verification_commands": [
            {
                "argv": ["python", "-m", "pytest", "-q", "tests/test_product.py"],
                "cwd": ".",
                "rationale": "focused product behavior",
            },
            {
                "argv": ["ruff", "check", "src/product.py", "tests/test_product.py"],
                "cwd": ".",
                "rationale": "focused lint policy",
            },
        ],
        "risk_signals": risk_signals(),
        "ambiguities": [],
        "assumptions": ["Existing public behavior remains compatible."],
        "repository_evidence": [
            "src/product.py owns the message",
            "tests/test_product.py covers the behavior",
        ],
    }
    value.update(updates)
    return value


def repository(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "product.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_product.py").write_text(
        "def test_value(): pass\n", encoding="utf-8"
    )
    return tmp_path.resolve()


def request(root: Path) -> NaturalLanguageTaskRequest:
    return NaturalLanguageTaskRequest("Change the exact product message.", root)


def parsed(**updates: Any) -> Any:
    return parse_intake_analysis(json.dumps(analysis(**updates)))


def compiler_task(root: Path, **updates: Any) -> Any:
    return TaskCompiler().compile(request(root), parsed(**updates), TaskId("V3-TEST"))


def test_intake_schema_is_closed_at_every_provider_object() -> None:
    schema = intake_analysis_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["properties"]["risk_signals"]["additionalProperties"] is False
    command = schema["properties"]["verification_commands"]["items"]
    assert command["additionalProperties"] is False
    assert "command_id" not in command["properties"]


@pytest.mark.parametrize(
    "raw",
    [
        "preamble " + json.dumps(analysis()),
        json.dumps(analysis()) + " epilogue",
        json.dumps(analysis()) + " {}",
        '{"normalized_description":"one","normalized_description":"two"}',
    ],
)
def test_intake_parser_rejects_wrappers_multiple_roots_and_duplicates(raw: str) -> None:
    with pytest.raises(IntakeAnalysisError):
        parse_intake_analysis(raw)


def test_intake_parser_rejects_unknown_and_incorrectly_typed_fields() -> None:
    unknown = analysis(unexpected="not permitted")
    with pytest.raises(IntakeAnalysisError, match="UNKNOWN_FIELD"):
        parse_intake_analysis(json.dumps(unknown))

    invalid = analysis()
    invalid["risk_signals"]["exact_outcome"] = "yes"
    with pytest.raises(IntakeAnalysisError, match="INVALID_FIELD_TYPE"):
        parse_intake_analysis(json.dumps(invalid))


def test_compiler_generates_ids_commands_scope_and_fast_routing(tmp_path: Path) -> None:
    compiled = compiler_task(repository(tmp_path))
    assert isinstance(compiled.spec, TaskSpec)
    assert compiled.spec.description == "Change the exact product message."
    assert compiled.spec.acceptance_criteria == (
        "The message is updated.",
        "The focused test passes.",
    )
    assert compiled.spec.risk is RiskLevel.TRIVIAL_MECHANICAL
    assert compiled.spec.fast_eligible
    assert compiled.routing.native_depth is WorkflowDepth.FAST
    assert [str(item.command_id) for item in compiled.spec.required_commands] == [
        "CMD-001",
        "CMD-002",
    ]
    assert all(item.required for item in compiled.spec.required_commands)
    assert all(
        item.output_handling is OutputHandling.STATUS_ONLY
        for item in compiled.spec.required_commands
    )


def test_uncertainty_and_semantic_impact_route_conservatively(tmp_path: Path) -> None:
    root = repository(tmp_path)
    uncertain = compiler_task(
        root,
        risk_signals=risk_signals(uncertainty_present=True),
    )
    assert uncertain.spec.risk is RiskLevel.STANDARD
    assert uncertain.routing.native_depth is WorkflowDepth.FULL
    assert not uncertain.spec.fast_eligible

    public = compiler_task(
        root,
        risk_signals=risk_signals(public_contract_impact=True),
    )
    assert public.spec.risk is RiskLevel.STANDARD
    assert public.routing.native_depth is WorkflowDepth.FULL


def test_high_risk_signal_is_never_downgraded(tmp_path: Path) -> None:
    compiled = compiler_task(
        repository(tmp_path),
        risk_signals=risk_signals(security_or_privacy_impact=True),
    )
    assert compiled.spec.risk is RiskLevel.HIGH_RISK
    assert compiled.routing.native_depth is WorkflowDepth.FULL


def test_more_than_three_files_cannot_be_fast(tmp_path: Path) -> None:
    root = repository(tmp_path)
    for name in ("one.py", "two.py"):
        (root / name).write_text("", encoding="utf-8")
    compiled = compiler_task(
        root,
        candidate_scope=(
            "src/product.py",
            "tests/test_product.py",
            "one.py",
            "two.py",
        ),
    )
    assert compiled.spec.risk is RiskLevel.LOW_RISK
    assert compiled.routing.native_depth is WorkflowDepth.FULL


@pytest.mark.parametrize(
    "scope",
    [
        ["."],
        ["**/*"],
        ["../outside.py"],
        ["/absolute.py"],
        [r"C:\outside.py"],
        [r"C:outside.py"],
        [r"\\server\share\outside.py"],
        ["src/control\nname.py"],
        ["src/product.py", "src/product.py"],
        ["src"],
        [".git/config"],
        ["src/.GIT/config"],
    ],
)
def test_compiler_rejects_broad_unsafe_or_duplicate_scope(
    tmp_path: Path, scope: list[str]
) -> None:
    with pytest.raises(DomainError):
        compiler_task(repository(tmp_path), candidate_scope=scope)


def test_windows_style_repository_relative_paths_are_normalized(tmp_path: Path) -> None:
    compiled = compiler_task(
        repository(tmp_path),
        candidate_scope=[r"src\product.py", r"tests\test_product.py"],
    )
    assert compiled.spec.fingerprint_scope == (
        "src/product.py",
        "tests/test_product.py",
    )


@pytest.mark.parametrize(
    "proposal",
    [
        {"argv": ["rm", "-rf", "build"], "cwd": ".", "rationale": "unsafe"},
        {"argv": ["pytest", "&&", "rm"], "cwd": ".", "rationale": "shell"},
        {"argv": ["python", "-c", "print(1)"], "cwd": ".", "rationale": "inline"},
        {
            "argv": [r"C:\Python312\python3.12.exe", "-c", "print(1)"],
            "cwd": ".",
            "rationale": "inline Windows Python",
        },
        {"argv": ["git", "commit", "-am", "x"], "cwd": ".", "rationale": "write"},
        {
            "argv": ["git", "diff", "--output=diff.txt"],
            "cwd": ".",
            "rationale": "writes output",
        },
        {"argv": ["pytest"], "cwd": "../outside", "rationale": "escape"},
        {"argv": ["pytest"], "cwd": r"C:\outside", "rationale": "absolute"},
        {"argv": ["pytest"], "cwd": r"C:outside", "rationale": "drive relative"},
        {"argv": ["pytest"], "cwd": "tests\nunit", "rationale": "control"},
        {"argv": ["pytest"], "cwd": "missing", "rationale": "missing cwd"},
    ],
)
def test_compiler_rejects_unsafe_command_proposals(
    tmp_path: Path, proposal: dict[str, Any]
) -> None:
    with pytest.raises(DomainError):
        compiler_task(repository(tmp_path), verification_commands=[proposal])


def test_read_only_git_verification_is_permitted(tmp_path: Path) -> None:
    compiled = compiler_task(
        repository(tmp_path),
        verification_commands=[
            {
                "argv": ["git", "diff", "--check"],
                "cwd": ".",
                "rationale": "repository whitespace policy",
            }
        ],
    )
    assert compiled.spec.required_commands[0].argv == ("git", "diff", "--check")


def test_windows_style_command_cwd_is_normalized(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "tests" / "unit").mkdir()
    compiled = compiler_task(
        root,
        verification_commands=[
            {
                "argv": ["pytest", "-q"],
                "cwd": r"tests\unit",
                "rationale": "focused unit suite",
            }
        ],
    )
    assert compiled.spec.required_commands[0].cwd == "tests/unit"


def test_genuine_ambiguity_requests_only_product_clarification(tmp_path: Path) -> None:
    value = parsed(
        candidate_scope=[],
        verification_commands=[],
        ambiguities=[
            {
                "question": "Should invalid input preserve the old exit code?",
                "impact": "This changes the public CLI contract.",
            }
        ],
    )
    with pytest.raises(IntakeClarificationRequired) as raised:
        TaskCompiler().compile(request(repository(tmp_path)), value, TaskId("V3-TEST"))
    assert raised.value.ambiguities[0].question.startswith("Should invalid input")


def test_task_id_generation_is_deterministic_under_injected_dependencies() -> None:
    generator = TaskIdGenerator(
        clock=lambda: datetime(2026, 8, 18, 16, 5, 1, tzinfo=UTC),
        entropy=lambda: "A1B2C3",
    )
    assert str(generator.generate()) == "V3-20260818-160501-A1B2C3"


def test_task_id_generator_rejects_nondeterministic_test_seam_errors() -> None:
    naive = TaskIdGenerator(
        clock=lambda: datetime(2026, 8, 18, 16, 5, 1),
        entropy=lambda: "A1B2C3",
    )
    with pytest.raises(DomainError, match="timezone-aware"):
        naive.generate()


def test_git_repository_locator_discovers_root_from_nested_directory(
    tmp_path: Path,
) -> None:
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    nested = tmp_path / "one" / "two"
    nested.mkdir(parents=True)
    locator = GitRepositoryLocator()
    assert locator.resolve(nested) == tmp_path.resolve()
    assert locator.resolve(tmp_path) == tmp_path.resolve()


def test_git_repository_locator_fails_clearly_outside_git(tmp_path: Path) -> None:
    with pytest.raises(DomainError, match="cannot discover a Git repository"):
        GitRepositoryLocator().resolve(tmp_path)


def test_intake_service_classifies_provider_and_schema_failures(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    provider_failure = ScriptedTaskIntentAnalyzer(
        [ScriptedIntakeResponse(failure_kind=FailureKind.INVOCATION_FAILED)]
    )
    with pytest.raises(IntakeProviderFailure) as transport:
        TaskIntakeService(provider_failure).compile(request(root))
    assert transport.value.failure_kind is FailureKind.INVOCATION_FAILED

    malformed = ScriptedTaskIntentAnalyzer([ScriptedIntakeResponse("not json")])
    with pytest.raises(IntakeProviderFailure) as schema:
        TaskIntakeService(malformed).compile(request(root))
    assert schema.value.failure_kind is FailureKind.MALFORMED_ARTIFACT


def test_scripted_intake_is_offline_deterministic_and_observable(tmp_path: Path) -> None:
    root = repository(tmp_path)
    analyzer = ScriptedTaskIntentAnalyzer(
        [ScriptedIntakeResponse(json.dumps(analysis()))]
    )
    service = TaskIntakeService(
        analyzer,
        task_ids=TaskIdGenerator(
            clock=lambda: datetime(2026, 8, 18, tzinfo=UTC),
            entropy=lambda: "ABC123",
        ),
    )
    compiled = service.compile(request(root))
    assert compiled.spec.task_id == TaskId("V3-20260818-000000-ABC123")
    assert analyzer.requests == [request(root)]
    assert analyzer.remaining == 0
    assert compiled.routing.native_depth is WorkflowDepth.FAST


def test_provider_result_success_literal_is_preserved() -> None:
    result = ScriptedTaskIntentAnalyzer(
        [ScriptedIntakeResponse(json.dumps(analysis()))]
    ).analyze(NaturalLanguageTaskRequest("task", Path.cwd().resolve()))
    assert result.status is TransportStatus.SUCCEEDED
