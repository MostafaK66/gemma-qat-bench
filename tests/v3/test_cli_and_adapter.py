from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from gemma_qat_bench.orchestration.cli import build_parser, main
from gemma_qat_bench.orchestration.codex_adapter import CodexSdkSpecialistClient


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


def verification(task_id: str) -> dict[str, Any]:
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
                "command_id": "CMD-001",
                "evidence_quality": "sufficient",
                "evidence_assessment": "successful",
                "rationale": "the canonical command result succeeded",
            }
        ],
        "blocking_findings": [],
        "environment_limitations": [],
        "residual_risks": [],
    }


def test_parser_exposes_run_resume_and_inspect() -> None:
    help_text = build_parser().format_help()
    assert "run" in help_text
    assert "resume" in help_text
    assert "inspect" in help_text


def test_codex_adapter_reports_actual_boundary_capabilities() -> None:
    capabilities = CodexSdkSpecialistClient().capabilities
    assert capabilities.structured_output
    assert capabilities.raw_response_access
    assert capabilities.tool_calls


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
