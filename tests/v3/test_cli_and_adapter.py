from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from gemma_qat_bench.orchestration.cli import CliEnvironment, build_parser, main
from gemma_qat_bench.orchestration.codex_adapter import (
    CodexSdkSpecialistClient,
    CodexSdkTaskIntentAnalyzer,
)
from gemma_qat_bench.orchestration.intake import TaskIdGenerator


def implementation(task_id: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "depth": "FAST",
        "plan_reference": "FAST-INTAKE",
        "iteration": 1,
        "disposition": "COMPLETED",
        "steps_implemented": ["confirmed scoped file"],
        "files_changed": ["pyproject.toml"],
        "tests_changed": [],
        "documentation_changes": [],
        "deviations": [],
        "blockers": [],
        "residual_risks": [],
    }


def verification(
    task_id: str, *, command_ids: tuple[str, ...] = ("CMD-001",)
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "depth": "FAST",
        "plan_reference": "FAST-INTAKE",
        "implementation_iteration": 1,
        "verification_iteration": 1,
        "verdict": "PASSED",
        "acceptance_checks": ["command passed"],
        "command_assessments": [
            {
                "command_id": command_id,
                "evidence_quality": "sufficient",
                "evidence_assessment": "successful",
                "rationale": "the canonical command result succeeded",
            }
            for command_id in command_ids
        ],
        "blocking_findings": [],
        "environment_limitations": [],
        "residual_risks": [],
    }


def intake_analysis(*, ambiguity: bool = False) -> dict[str, Any]:
    return {
        "normalized_description": "Inspect and preserve the exact requested behavior.",
        "acceptance_criteria": ["The requested behavior is preserved."],
        "candidate_scope": [] if ambiguity else ["pyproject.toml"],
        "verification_commands": []
        if ambiguity
        else [
            {
                "argv": [sys.executable, "--version"],
                "cwd": ".",
                "rationale": "deterministic interpreter smoke check",
            }
        ],
        "risk_signals": {
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
            "uncertainty_present": ambiguity,
        },
        "ambiguities": (
            [
                {
                    "question": "Which public behavior should be preserved?",
                    "impact": "Different answers change the public contract.",
                }
            ]
            if ambiguity
            else []
        ),
        "assumptions": [],
        "repository_evidence": ["pyproject.toml defines the package contract"],
    }


def environment(
    repository_root: Path,
    *,
    task_id_suffix: str,
    stdin: str = "",
    interactive: bool = False,
    working_directory: Path | None = None,
) -> CliEnvironment:
    return CliEnvironment(
        stdin=StringIO(stdin),
        stdout=StringIO(),
        stderr=StringIO(),
        cwd=lambda: working_directory or repository_root,
        task_ids=TaskIdGenerator(
            clock=lambda: datetime(2026, 8, 18, 16, 5, 1, tzinfo=UTC),
            entropy=lambda: task_id_suffix,
        ),
        interactive=interactive,
    )


def test_parser_exposes_run_resume_and_inspect(capsys: Any) -> None:
    help_text = build_parser().format_help()
    assert "run" in help_text
    assert "resume" in help_text
    assert "inspect" in help_text
    with pytest.raises(SystemExit) as raised:
        build_parser().parse_args(["run", "--help"])
    assert raised.value.code == 0
    run_help = capsys.readouterr().out
    assert "--description" in run_help
    assert "--stdin" in run_help
    assert "advanced explicit task specification JSON" in run_help


def test_codex_adapter_reports_actual_boundary_capabilities() -> None:
    capabilities = CodexSdkSpecialistClient().capabilities
    assert capabilities.structured_output
    assert capabilities.raw_response_access
    assert capabilities.tool_calls
    assert CodexSdkTaskIntentAnalyzer is not None


def test_scripted_cli_runs_and_inspects_fast_workflow(
    tmp_path: Path, capsys: Any
) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    task_id = "CLI-FAST-1"
    task_file = tmp_path / "task.json"
    response_file = tmp_path / "responses.json"
    state_dir = tmp_path / "state"
    task_file.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "description": "exercise the V3 CLI deterministically",
                "acceptance_criteria": ["the command succeeds"],
                "risk": "TRIVIAL_MECHANICAL",
                "fast_eligible": True,
                "repository_root": str(repository_root),
                "required_commands": [
                    {
                        "command_id": "CMD-001",
                        "argv": [sys.executable, "-c", "print('ok')"],
                    }
                ],
                "fingerprint_scope": ["pyproject.toml"],
            }
        ),
        encoding="utf-8",
    )
    response_file.write_text(
        json.dumps(
            [
                {"role": "IMPLEMENTER", "response": implementation(task_id)},
                {"role": "VERIFIER", "response": verification(task_id)},
            ]
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "run",
                str(task_file),
                "--provider",
                "scripted",
                "--responses",
                str(response_file),
                "--state-dir",
                str(state_dir),
                "--authorize-commands",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "CHANGE_COMPLETE"
    assert result["git_authorization"] == "not implied by CHANGE_COMPLETE"

    assert main(["inspect", task_id, "--state-dir", str(state_dir)]) == 0
    snapshot = json.loads(capsys.readouterr().out)
    assert snapshot["state"] == "COMPLETE"


def test_description_only_cli_compiles_and_runs_without_task_json(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    task_id = "V3-20260818-160501-A1B2C3"
    responses = tmp_path / "responses.json"
    responses.write_text(
        json.dumps(
            [
                {"role": "INTAKE_ANALYZER", "response": intake_analysis()},
                {"role": "IMPLEMENTER", "response": implementation(task_id)},
                {"role": "VERIFIER", "response": verification(task_id)},
            ]
        ),
        encoding="utf-8",
    )
    env = environment(repository_root, task_id_suffix="A1B2C3")
    state_dir = tmp_path / "state"

    assert (
        main(
            [
                "run",
                "--description",
                "Preserve the exact requested behavior.",
                "--repository-root",
                str(repository_root),
                "--provider",
                "scripted",
                "--responses",
                str(responses),
                "--state-dir",
                str(state_dir),
                "--authorize-commands",
            ],
            environment=env,
        )
        == 0
    )
    payload = json.loads(env.stdout.getvalue())
    assert payload["status"] == "CHANGE_COMPLETE"
    assert payload["task_id"] == task_id
    assert payload["intake"]["verification_commands"][0]["command_id"] == "CMD-001"
    assert payload["intake"]["fingerprint_scope"] == ["pyproject.toml"]
    assert "Task analyzed." in env.stderr.getvalue()


def test_intake_summary_escapes_provider_terminal_controls(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    task_id = "V3-20260818-160501-B8C9D0"
    unsafe_display = intake_analysis()
    unsafe_display["normalized_description"] = "Safe text\u001b[31m"
    unsafe_display["acceptance_criteria"] = ["No terminal\u001b[0m mutation"]
    responses = tmp_path / "responses.json"
    responses.write_text(
        json.dumps(
            [
                {"role": "INTAKE_ANALYZER", "response": unsafe_display},
                {"role": "IMPLEMENTER", "response": implementation(task_id)},
                {"role": "VERIFIER", "response": verification(task_id)},
            ]
        ),
        encoding="utf-8",
    )
    env = environment(repository_root, task_id_suffix="B8C9D0")

    assert (
        main(
            [
                "run",
                "--description",
                "Preserve the exact requested behavior.",
                "--provider",
                "scripted",
                "--responses",
                str(responses),
                "--state-dir",
                str(tmp_path / "state"),
                "--authorize-commands",
            ],
            environment=env,
        )
        == 0
    )
    assert "\u001b" not in env.stderr.getvalue()
    assert r"\u001b" in env.stderr.getvalue()


def test_repository_root_override_does_not_use_unrelated_cwd(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    task_id = "V3-20260818-160501-F6A7B8"
    responses = tmp_path / "responses.json"
    responses.write_text(
        json.dumps(
            [
                {"role": "INTAKE_ANALYZER", "response": intake_analysis()},
                {"role": "IMPLEMENTER", "response": implementation(task_id)},
                {"role": "VERIFIER", "response": verification(task_id)},
            ]
        ),
        encoding="utf-8",
    )
    unrelated = tmp_path / "not-a-repository"
    unrelated.mkdir()
    env = environment(
        repository_root,
        task_id_suffix="F6A7B8",
        working_directory=unrelated,
    )

    assert (
        main(
            [
                "run",
                "--description",
                "Preserve the exact requested behavior.",
                "--repository-root",
                str(repository_root),
                "--provider",
                "scripted",
                "--responses",
                str(responses),
                "--state-dir",
                str(tmp_path / "state"),
                "--authorize-commands",
            ],
            environment=env,
        )
        == 0
    )
    assert json.loads(env.stdout.getvalue())["intake"]["repository_root"] == str(
        repository_root
    )


def test_scripted_natural_mode_binds_generated_task_id_placeholder(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    task_id = "V3-20260818-160501-A7B8C9"
    responses = tmp_path / "responses.json"
    responses.write_text(
        json.dumps(
            [
                {"role": "INTAKE_ANALYZER", "response": intake_analysis()},
                {
                    "role": "IMPLEMENTER",
                    "response": implementation("{{TASK_ID}}"),
                },
                {"role": "VERIFIER", "response": verification("{{TASK_ID}}")},
            ]
        ),
        encoding="utf-8",
    )
    env = environment(repository_root, task_id_suffix="A7B8C9")

    assert (
        main(
            [
                "run",
                "--description",
                "Preserve the exact requested behavior.",
                "--provider",
                "scripted",
                "--responses",
                str(responses),
                "--state-dir",
                str(tmp_path / "state"),
                "--authorize-commands",
            ],
            environment=env,
        )
        == 0
    )
    assert json.loads(env.stdout.getvalue())["task_id"] == task_id


def test_stdin_natural_language_mode_is_equivalent(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    task_id = "V3-20260818-160501-B2C3D4"
    responses = tmp_path / "responses.json"
    responses.write_text(
        json.dumps(
            [
                {"role": "INTAKE_ANALYZER", "response": intake_analysis()},
                {"role": "IMPLEMENTER", "response": implementation(task_id)},
                {"role": "VERIFIER", "response": verification(task_id)},
            ]
        ),
        encoding="utf-8",
    )
    env = environment(
        repository_root,
        task_id_suffix="B2C3D4",
        stdin="Preserve the exact requested behavior.\n",
    )

    assert (
        main(
            [
                "run",
                "--stdin",
                "--provider",
                "scripted",
                "--responses",
                str(responses),
                "--state-dir",
                str(tmp_path / "state"),
                "--authorize-commands",
            ],
            environment=env,
        )
        == 0
    )
    assert json.loads(env.stdout.getvalue())["task_id"] == task_id


def test_natural_workflow_persists_spec_and_resumes_by_task_id(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    task_id = "V3-20260818-160501-C3D4E5"
    initial_responses = tmp_path / "initial.json"
    initial_responses.write_text(
        json.dumps(
            [
                {"role": "INTAKE_ANALYZER", "response": intake_analysis()},
                {"role": "IMPLEMENTER", "response": implementation(task_id)},
            ]
        ),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    initial_env = environment(repository_root, task_id_suffix="C3D4E5")
    assert (
        main(
            [
                "run",
                "--description",
                "Preserve the exact requested behavior.",
                "--provider",
                "scripted",
                "--responses",
                str(initial_responses),
                "--state-dir",
                str(state_dir),
                "--non-interactive",
            ],
            environment=initial_env,
        )
        == 2
    )
    assert json.loads(initial_env.stdout.getvalue())["status"] == "WAITING_AUTHORIZATION"

    resume_responses = tmp_path / "resume.json"
    resume_responses.write_text(
        json.dumps([{"role": "VERIFIER", "response": verification(task_id)}]),
        encoding="utf-8",
    )
    resume_env = environment(
        repository_root,
        task_id_suffix="D4E5F6",
        stdin="yes\n",
        interactive=True,
    )
    assert (
        main(
            [
                "resume",
                task_id,
                "--provider",
                "scripted",
                "--responses",
                str(resume_responses),
                "--state-dir",
                str(state_dir),
            ],
            environment=resume_env,
        )
        == 0
    )
    assert json.loads(resume_env.stdout.getvalue())["status"] == "CHANGE_COMPLETE"
    assert "CMD-001" in resume_env.stderr.getvalue()
    assert "Authorize all displayed commands?" in resume_env.stderr.getvalue()


def test_interactive_natural_mode_asks_once_for_all_commands(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    task_id = "V3-20260818-160501-D4E5F6"
    responses = tmp_path / "responses.json"
    intake = intake_analysis()
    intake["verification_commands"].append(
        {
            "argv": [sys.executable, "-V"],
            "cwd": ".",
            "rationale": "second deterministic interpreter smoke check",
        }
    )
    responses.write_text(
        json.dumps(
            [
                {"role": "INTAKE_ANALYZER", "response": intake},
                {"role": "IMPLEMENTER", "response": implementation(task_id)},
                {
                    "role": "VERIFIER",
                    "response": verification(task_id, command_ids=("CMD-001", "CMD-002")),
                },
            ]
        ),
        encoding="utf-8",
    )
    env = environment(
        repository_root,
        task_id_suffix="D4E5F6",
        stdin="yes\n",
        interactive=True,
    )
    assert (
        main(
            [
                "run",
                "--description",
                "Preserve the exact requested behavior.",
                "--provider",
                "scripted",
                "--responses",
                str(responses),
                "--state-dir",
                str(tmp_path / "state"),
            ],
            environment=env,
        )
        == 0
    )
    assert env.stderr.getvalue().count("Authorize all displayed commands?") == 1
    assert env.stderr.getvalue().count("CMD-001") == 1
    assert env.stderr.getvalue().count("CMD-002") == 1
    assert json.loads(env.stdout.getvalue())["intake"]["authorization_status"] == (
        "AUTHORIZED"
    )


def test_genuine_cli_ambiguity_returns_one_concise_question(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    responses = tmp_path / "responses.json"
    responses.write_text(
        json.dumps(
            [{"role": "INTAKE_ANALYZER", "response": intake_analysis(ambiguity=True)}]
        ),
        encoding="utf-8",
    )
    env = environment(repository_root, task_id_suffix="E5F6A7")
    assert (
        main(
            [
                "run",
                "--description",
                "Improve invalid input behavior.",
                "--provider",
                "scripted",
                "--responses",
                str(responses),
                "--state-dir",
                str(tmp_path / "state"),
            ],
            environment=env,
        )
        == 2
    )
    payload = json.loads(env.stdout.getvalue())
    assert payload["status"] == "CLARIFICATION_REQUIRED"
    assert len(payload["questions"]) == 1
