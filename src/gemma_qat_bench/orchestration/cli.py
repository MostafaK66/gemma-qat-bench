"""Command-line execution, intake, resume, and inspection surface for V3."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TextIO, cast

from .authorization import InteractiveCommandAuthorization, StaticAuthorization
from .codex_adapter import CodexSdkSpecialistClient, CodexSdkTaskIntentAnalyzer
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
from .intake import (
    GitRepositoryLocator,
    IntakeClarificationRequired,
    IntakeProviderFailure,
    ScriptedIntakeResponse,
    ScriptedTaskIntentAnalyzer,
    TaskIdGenerator,
    TaskIntakeService,
)
from .intake_domain import CompiledTask, NaturalLanguageTaskRequest, TaskIntentAnalyzer
from .persistence import JsonFileWorkflowStore, restore_task_spec
from .specialists import (
    ScriptedResponse,
    ScriptedSpecialistClient,
    SpecialistClient,
)


@dataclass(frozen=True, slots=True)
class CliEnvironment:
    """Injected terminal and identity dependencies for deterministic CLI tests."""

    stdin: TextIO
    stdout: TextIO
    stderr: TextIO
    cwd: Callable[[], Path]
    task_ids: TaskIdGenerator
    interactive: bool

    @classmethod
    def system(cls) -> CliEnvironment:
        return cls(
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            cwd=Path.cwd,
            task_ids=TaskIdGenerator(),
            interactive=sys.stdin.isatty(),
        )


@dataclass(frozen=True, slots=True)
class _ProviderBundle:
    intake: TaskIntentAnalyzer
    specialists_for: Callable[[TaskId], SpecialistClient]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gemma-qat-orchestrate",
        description=(
            "Run deterministic V3 coding orchestration from natural language or an "
            "advanced explicit task specification."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="start from --description, --stdin, or an advanced task JSON"
    )
    run_parser.add_argument(
        "task",
        nargs="?",
        type=Path,
        help="advanced explicit task specification JSON",
    )
    natural_group = run_parser.add_mutually_exclusive_group()
    natural_group.add_argument("--description", help="natural-language task description")
    natural_group.add_argument(
        "--stdin",
        action="store_true",
        help="read the natural-language task description from standard input",
    )
    run_parser.add_argument(
        "--repository-root",
        type=Path,
        help="override automatic Git-root discovery for natural-language intake",
    )
    run_parser.add_argument(
        "--clarification",
        action="append",
        default=[],
        help="supply one product clarification to the read-only intake analyzer",
    )
    _add_execution_options(run_parser)

    resume_parser = subparsers.add_parser(
        "resume", help="resume by generated task ID or legacy task JSON"
    )
    resume_parser.add_argument(
        "task",
        help="generated task ID, or an existing task specification JSON path",
    )
    _add_execution_options(resume_parser)

    inspect_parser = subparsers.add_parser("inspect", help="inspect a task checkpoint")
    inspect_parser.add_argument("task_id")
    inspect_parser.add_argument("--state-dir", type=Path, default=_default_state_dir())
    return parser


def _add_execution_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", choices=("codex", "scripted"), default="codex")
    parser.add_argument("--model", default=None, help="optional Codex model name")
    parser.add_argument(
        "--responses",
        type=Path,
        help=(
            "scripted provider response JSON; natural-language mode uses "
            "INTAKE_ANALYZER entries before specialist entries"
        ),
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=_default_state_dir(),
        help="protected workflow checkpoint directory",
    )
    parser.add_argument(
        "--authorize-commands",
        action="store_true",
        help="authorize only the exact compiled or task-file command set",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="never prompt; pause before commands unless explicitly authorized",
    )


def main(
    argv: list[str] | None = None,
    *,
    environment: CliEnvironment | None = None,
) -> int:
    env = environment or CliEnvironment.system()
    args = build_parser().parse_args(argv)
    try:
        state_dir = args.state_dir.resolve()
        store = JsonFileWorkflowStore(state_dir)
        if args.command == "inspect":
            snapshot = store.load(TaskId(args.task_id))
            if snapshot is None:
                raise DomainError(f"workflow {args.task_id} does not exist")
            print(
                json.dumps(asdict(snapshot), indent=2, default=str, sort_keys=True),
                file=env.stdout,
            )
            return 0

        providers = _provider_bundle(args.provider, args.responses, args.model)
        compiled: CompiledTask | None = None
        task_id_resume = False
        if args.command == "run":
            spec, compiled = _run_spec(args, providers.intake, env)
        else:
            task_id_resume = not Path(str(args.task)).expanduser().is_file()
            spec = _resume_spec(str(args.task), store)

        authorization, authorization_label = _authorization(
            args,
            spec,
            interactive_confirmation=compiled is not None or task_id_resume,
            commands_already_displayed=compiled is not None,
            env=env,
        )
        if compiled is not None:
            _print_intake_summary(compiled, authorization_label, env.stderr)

        runner = SubprocessCommandRunner(spec.repository_root)
        broker = CommandBroker(runner, authorization)
        fingerprints = FingerprintService(
            spec.repository_root, GitContentIdentityProvider(spec.repository_root)
        )
        engine = Orchestrator(
            providers.specialists_for(spec.task_id),
            broker,
            fingerprints,
            store=store,
            events=InMemoryEventSink(),
        )
        result = engine.run(spec) if args.command == "run" else engine.resume(spec)
        payload = _completion_dict(result)
        if compiled is not None:
            payload["intake"] = _intake_dict(
                compiled,
                _final_authorization_label(authorization, authorization_label),
            )
        print(json.dumps(payload, indent=2, sort_keys=True), file=env.stdout)
        return 0 if result.status.value == "CHANGE_COMPLETE" else 2
    except IntakeClarificationRequired as exc:
        print(
            json.dumps(
                {
                    "status": "CLARIFICATION_REQUIRED",
                    "questions": [
                        {"question": item.question, "impact": item.impact}
                        for item in exc.ambiguities
                    ],
                    "next_step": (
                        "rerun with --clarification for each supplied product decision"
                    ),
                },
                indent=2,
                sort_keys=True,
            ),
            file=env.stdout,
        )
        return 2
    except IntakeProviderFailure as exc:
        print(
            json.dumps(
                {
                    "status": "INTAKE_FAILED",
                    "failure_kind": exc.failure_kind.value,
                    "message": str(exc),
                },
                indent=2,
                sort_keys=True,
            ),
            file=env.stdout,
        )
        return 2
    except (DomainError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=env.stderr)
        return 1


def _run_spec(
    args: argparse.Namespace,
    analyzer: TaskIntentAnalyzer,
    env: CliEnvironment,
) -> tuple[TaskSpec, CompiledTask | None]:
    source_count = sum(
        (args.task is not None, args.description is not None, bool(args.stdin))
    )
    if source_count != 1:
        raise DomainError(
            "run requires exactly one of --description, --stdin, or a task JSON path"
        )
    if args.task is not None:
        if args.repository_root is not None or args.clarification:
            raise DomainError(
                "--repository-root and --clarification apply only to "
                "natural-language intake"
            )
        return _load_task(args.task.resolve()), None

    description = args.description
    if args.stdin:
        description = env.stdin.read()
    if description is None or not description.strip():
        raise DomainError("natural-language task description must not be empty")
    candidate = args.repository_root if args.repository_root is not None else env.cwd()
    repository_root = GitRepositoryLocator().resolve(candidate)
    request = NaturalLanguageTaskRequest(
        description=description.strip(),
        repository_root=repository_root,
        clarifications=tuple(args.clarification),
    )
    compiled = TaskIntakeService(analyzer, task_ids=env.task_ids).compile(request)
    return compiled.spec, compiled


def _resume_spec(task: str, store: JsonFileWorkflowStore) -> TaskSpec:
    candidate = Path(task).expanduser()
    if candidate.is_file():
        return _load_task(candidate.resolve())
    task_id = TaskId(task)
    snapshot = store.load(task_id)
    if snapshot is None:
        raise DomainError(f"workflow {task_id} does not exist")
    if snapshot.task_spec is None:
        raise DomainError(
            "this legacy checkpoint has no persisted TaskSpec; resume it with the "
            "original task JSON path"
        )
    return restore_task_spec(task_id, snapshot.task_spec)


def _authorization(
    args: argparse.Namespace,
    spec: TaskSpec,
    *,
    interactive_confirmation: bool,
    commands_already_displayed: bool,
    env: CliEnvironment,
) -> tuple[StaticAuthorization | InteractiveCommandAuthorization, str]:
    if args.authorize_commands:
        return (
            StaticAuthorization(commands=AuthorizationStatus.AUTHORIZED),
            AuthorizationStatus.AUTHORIZED.value,
        )
    if interactive_confirmation and env.interactive and not args.non_interactive:
        return (
            InteractiveCommandAuthorization(
                spec.required_commands,
                reader=lambda prompt: _read_line(prompt, env),
                writer=lambda message: print(message, file=env.stderr),
                display_commands=not commands_already_displayed,
            ),
            "INTERACTIVE_CONFIRMATION_REQUIRED",
        )
    return (
        StaticAuthorization(commands=AuthorizationStatus.REQUIRED),
        AuthorizationStatus.REQUIRED.value,
    )


def _final_authorization_label(
    authorization: StaticAuthorization | InteractiveCommandAuthorization,
    initial_label: str,
) -> str:
    if not isinstance(authorization, InteractiveCommandAuthorization):
        return initial_label
    decision = authorization.command_decision
    return initial_label if decision is None else decision.status.value


def _read_line(prompt: str, env: CliEnvironment) -> str:
    env.stderr.write(prompt)
    env.stderr.flush()
    value = env.stdin.readline()
    if not value:
        raise EOFError
    return value


def _provider_bundle(
    provider: str, responses: Path | None, model: str | None
) -> _ProviderBundle:
    if provider == "codex":
        specialists = CodexSdkSpecialistClient(model=model)
        return _ProviderBundle(
            CodexSdkTaskIntentAnalyzer(model=model),
            lambda _task_id: specialists,
        )
    if responses is None:
        raise DomainError("--responses is required for the scripted provider")
    intake_responses, specialist_responses = _load_scripted_responses(responses)
    return _ProviderBundle(
        ScriptedTaskIntentAnalyzer(intake_responses),
        lambda task_id: ScriptedSpecialistClient(
            _bind_scripted_task_id(specialist_responses, task_id)
        ),
    )


def _bind_scripted_task_id(
    responses: list[ScriptedResponse], task_id: TaskId
) -> list[ScriptedResponse]:
    """Resolve the documented deterministic placeholder after intake creates identity."""
    marker = "{{TASK_ID}}"
    return [
        ScriptedResponse(
            role=response.role,
            raw_response=(
                None
                if response.raw_response is None
                else response.raw_response.replace(marker, str(task_id))
            ),
            failure_kind=response.failure_kind,
            error_message=response.error_message,
        )
        for response in responses
    ]


def _load_scripted_responses(
    path: Path,
) -> tuple[list[ScriptedIntakeResponse], list[ScriptedResponse]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise DomainError("scripted responses root must be an array")
    intake: list[ScriptedIntakeResponse] = []
    specialists: list[ScriptedResponse] = []
    for item in raw:
        if not isinstance(item, dict):
            raise DomainError("each scripted response must be an object")
        data = cast(dict[str, Any], item)
        role = _required_string(data.get("role"), "role")
        response = data.get("response")
        raw_response = (
            response
            if isinstance(response, str)
            else json.dumps(response, sort_keys=True)
        )
        failure_raw = data.get("failure_kind")
        failure = None if failure_raw is None else FailureKind(str(failure_raw))
        error = None if data.get("error_message") is None else str(data["error_message"])
        if role == "INTAKE_ANALYZER":
            intake.append(
                ScriptedIntakeResponse(
                    raw_response=None if failure is not None else raw_response,
                    failure_kind=failure,
                    error_message=error,
                )
            )
        else:
            specialists.append(
                ScriptedResponse(
                    role=_specialist_role(role),
                    raw_response=None if failure is not None else raw_response,
                    failure_kind=failure,
                    error_message=error,
                )
            )
    return intake, specialists


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


def _print_intake_summary(
    compiled: CompiledTask, authorization: str, stream: TextIO
) -> None:
    spec = compiled.spec
    print("Task analyzed.", file=stream)
    print(f"Task ID: {spec.task_id}", file=stream)
    print(f"Repository: {_display_text(str(spec.repository_root))}", file=stream)
    print(
        f"Description: {_display_text(compiled.analysis.normalized_description)}",
        file=stream,
    )
    print("Acceptance criteria:", file=stream)
    for criterion in spec.acceptance_criteria:
        print(f"  - {_display_text(criterion)}", file=stream)
    print(f"Risk: {spec.risk.value}", file=stream)
    print(f"Depth: {compiled.routing.native_depth.value}", file=stream)
    print(f"Routing: {compiled.routing.reason}", file=stream)
    print("Expected file scope:", file=stream)
    for path in spec.fingerprint_scope:
        print(f"  - {_display_text(path)}", file=stream)
    print("Verification commands:", file=stream)
    for command in spec.required_commands:
        argv = json.dumps(list(command.argv), ensure_ascii=False)
        print(
            f"  {command.command_id}  {argv}  (cwd: {_display_text(command.cwd)})",
            file=stream,
        )
    print(f"Command authorization: {authorization}", file=stream)


def _display_text(value: str) -> str:
    """Quote provider/local text so terminal control characters remain inert."""
    return json.dumps(value, ensure_ascii=False)


def _intake_dict(compiled: CompiledTask, authorization: str) -> dict[str, Any]:
    spec = compiled.spec
    return {
        "task_id": str(spec.task_id),
        "repository_root": str(spec.repository_root),
        "normalized_description": compiled.analysis.normalized_description,
        "acceptance_criteria": list(spec.acceptance_criteria),
        "risk": spec.risk.value,
        "depth": compiled.routing.native_depth.value,
        "routing_reason": compiled.routing.reason,
        "fingerprint_scope": list(spec.fingerprint_scope),
        "verification_commands": [
            {
                "command_id": str(command.command_id),
                "argv": list(command.argv),
                "cwd": command.cwd,
                "required": command.required,
                "rationale": command.rationale,
                "output_handling": command.output_handling.value,
            }
            for command in spec.required_commands
        ],
        "authorization_status": authorization,
        "assumptions": list(compiled.analysis.assumptions),
        "repository_evidence": list(compiled.analysis.repository_evidence),
    }


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


__all__ = ["CliEnvironment", "build_parser", "main"]
