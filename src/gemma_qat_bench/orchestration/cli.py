"""Command-line execution and inspection surface for V3 orchestration."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from .authorization import StaticAuthorization
from .codex_adapter import CodexSdkSpecialistClient
from .commands import CommandBroker, SubprocessCommandRunner
from .domain import (
    AuthorizationStatus,
    CommandId,
    CompletionResult,
    DomainError,
    FailureKind,
    OutputHandling,
    RequiredCommand,
    RiskLevel,
    SpecialistRole,
    TaskId,
    TaskSpec,
)
from .engine import Orchestrator
from .events import InMemoryEventSink
from .fingerprint import FingerprintService, GitContentIdentityProvider
from .persistence import JsonFileWorkflowStore
from .specialists import (
    ScriptedResponse,
    ScriptedSpecialistClient,
    SpecialistClient,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gemma-qat-orchestrate",
        description="Run deterministic V3 coding orchestration.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("run", "start a new task"),
        ("resume", "resume an existing task checkpoint"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("task", type=Path, help="task specification JSON")
        command.add_argument("--provider", choices=("codex", "scripted"), default="codex")
        command.add_argument("--model", default=None, help="optional Codex model name")
        command.add_argument(
            "--responses", type=Path, help="scripted specialist response JSON"
        )
        command.add_argument(
            "--state-dir",
            type=Path,
            default=_default_state_dir(),
            help="local workflow checkpoint directory",
        )
        command.add_argument(
            "--authorize-commands",
            action="store_true",
            help="authorize only the exact required commands in the task file",
        )

    inspect_parser = subparsers.add_parser("inspect", help="inspect a task checkpoint")
    inspect_parser.add_argument("task_id")
    inspect_parser.add_argument("--state-dir", type=Path, default=_default_state_dir())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "inspect":
            store = JsonFileWorkflowStore(args.state_dir.resolve())
            snapshot = store.load(TaskId(args.task_id))
            if snapshot is None:
                raise DomainError(f"workflow {args.task_id} does not exist")
            print(json.dumps(asdict(snapshot), indent=2, default=str, sort_keys=True))
            return 0

        spec = _load_task(args.task.resolve())
        client = _client(args.provider, args.responses, args.model)
        authorization = StaticAuthorization(
            commands=(
                AuthorizationStatus.AUTHORIZED
                if args.authorize_commands
                else AuthorizationStatus.REQUIRED
            )
        )
        runner = SubprocessCommandRunner(spec.repository_root)
        broker = CommandBroker(runner, authorization)
        fingerprints = FingerprintService(
            spec.repository_root, GitContentIdentityProvider(spec.repository_root)
        )
        engine = Orchestrator(
            client,
            broker,
            fingerprints,
            store=JsonFileWorkflowStore(args.state_dir.resolve()),
            events=InMemoryEventSink(),
        )
        result = engine.run(spec) if args.command == "run" else engine.resume(spec)
        print(json.dumps(_completion_dict(result), indent=2, sort_keys=True))
        return 0 if result.status.value == "CHANGE_COMPLETE" else 2
    except (DomainError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _load_task(path: Path) -> TaskSpec:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise DomainError("task specification root must be an object")
    data = cast(dict[str, Any], raw)
    required_fields = {
        "task_id",
        "description",
        "acceptance_criteria",
        "risk",
        "fast_eligible",
        "repository_root",
        "required_commands",
        "fingerprint_scope",
    }
    if set(data) != required_fields:
        missing = sorted(required_fields - data.keys())
        unknown = sorted(data.keys() - required_fields)
        raise DomainError(f"task field mismatch; missing={missing}, unknown={unknown}")
    command_values = data["required_commands"]
    if not isinstance(command_values, list):
        raise DomainError("required_commands must be an array")
    commands = tuple(_required_command(item) for item in command_values)
    criteria = _string_array(data["acceptance_criteria"], "acceptance_criteria")
    scope = _string_array(data["fingerprint_scope"], "fingerprint_scope")
    if not isinstance(data["fast_eligible"], bool):
        raise DomainError("fast_eligible must be a boolean")
    root = Path(_required_string(data["repository_root"], "repository_root")).resolve()
    return TaskSpec(
        TaskId(_required_string(data["task_id"], "task_id")),
        _required_string(data["description"], "description"),
        criteria,
        RiskLevel(_required_string(data["risk"], "risk")),
        data["fast_eligible"],
        root,
        commands,
        scope,
    )


def _required_command(raw: Any) -> RequiredCommand:
    if not isinstance(raw, dict):
        raise DomainError("each required command must be an object")
    data = cast(dict[str, Any], raw)
    allowed = {
        "command_id",
        "argv",
        "cwd",
        "required",
        "rationale",
        "output_handling",
    }
    required = {"command_id", "argv"}
    if not required.issubset(data) or not set(data).issubset(allowed):
        raise DomainError("required command fields are invalid")
    argv = _string_array(data["argv"], "argv")
    is_required = data.get("required", True)
    if not isinstance(is_required, bool):
        raise DomainError("command required must be a boolean")
    return RequiredCommand(
        CommandId(_required_string(data["command_id"], "command_id")),
        argv,
        _required_string(data.get("cwd", "."), "cwd"),
        is_required,
        _required_string(data.get("rationale", "task acceptance criteria"), "rationale"),
        OutputHandling(str(data.get("output_handling", "STATUS_ONLY"))),
    )


def _client(provider: str, responses: Path | None, model: str | None) -> SpecialistClient:
    if provider == "codex":
        return CodexSdkSpecialistClient(model=model)
    if responses is None:
        raise DomainError("--responses is required for the scripted provider")
    raw = json.loads(responses.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise DomainError("scripted responses root must be an array")
    scripted: list[ScriptedResponse] = []
    for item in raw:
        if not isinstance(item, dict):
            raise DomainError("each scripted response must be an object")
        response = item.get("response")
        raw_response = (
            response
            if isinstance(response, str)
            else json.dumps(response, sort_keys=True)
        )
        failure = item.get("failure_kind")
        scripted.append(
            ScriptedResponse(
                role=_specialist_role(item.get("role")),
                raw_response=None if failure else raw_response,
                failure_kind=None if failure is None else FailureKind(str(failure)),
                error_message=(
                    None
                    if item.get("error_message") is None
                    else str(item["error_message"])
                ),
            )
        )
    return ScriptedSpecialistClient(scripted)


def _specialist_role(value: Any) -> SpecialistRole:
    return SpecialistRole(_required_string(value, "role"))


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainError(f"{name} must be a non-empty string")
    return value


def _string_array(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise DomainError(f"{name} must be an array")
    return tuple(_required_string(item, name) for item in value)


def _completion_dict(result: CompletionResult) -> dict[str, Any]:
    return {
        "task_id": str(result.task_id),
        "status": result.status.value,
        "state": result.state.value,
        "depth": result.depth.value,
        "plan_version": result.plan_version.value,
        "implementation_iteration": result.implementation_iteration.value,
        "verification_iteration": result.verification_iteration.value,
        "gate1": None if result.gate1 is None else result.gate1.value,
        "gate2": None if result.gate2 is None else result.gate2.value,
        "gate3": None if result.gate3 is None else result.gate3.value,
        "fingerprint": None if result.fingerprint is None else result.fingerprint.digest,
        "escalation": None
        if result.escalation is None
        else {
            "failure_kind": result.escalation.failure_kind.value,
            "code": result.escalation.code,
            "message": result.escalation.message,
            "resolution_class": None
            if result.escalation.resolution_class is None
            else result.escalation.resolution_class.value,
        },
        "git_authorization": "not implied by CHANGE_COMPLETE",
    }


def _default_state_dir() -> Path:
    base = os.getenv("XDG_STATE_HOME")
    state_root = Path(base) if base else Path.home() / ".local" / "state"
    return state_root / "gemma-qat-bench" / "v3"


__all__ = ["build_parser", "main"]
