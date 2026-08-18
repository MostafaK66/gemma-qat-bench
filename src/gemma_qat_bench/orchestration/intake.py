"""Repository-aware natural-language intake and deterministic TaskSpec compilation."""

from __future__ import annotations

import json
import re
import secrets
import subprocess
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from .domain import (
    CommandId,
    DomainError,
    FailureKind,
    OutputHandling,
    RequiredCommand,
    RiskLevel,
    TaskId,
    TaskSpec,
    TransportStatus,
    normalize_repository_path,
)
from .intake_artifacts import IntakeAnalysisError, parse_intake_analysis
from .intake_domain import (
    CompiledTask,
    IntakeAmbiguity,
    IntakeRiskSignals,
    NaturalLanguageTaskRequest,
    TaskIntakeAnalysis,
    TaskIntakeProviderResult,
    TaskIntentAnalyzer,
    VerificationCommandProposal,
)
from .routing import RoutingPolicy


class IntakeProviderFailure(DomainError):
    """Provider transport or schema failure before deterministic compilation."""

    def __init__(self, failure_kind: FailureKind, message: str) -> None:
        super().__init__(message)
        self.failure_kind = failure_kind


class IntakeClarificationRequired(DomainError):
    """Raised only for unresolved consequential product decisions."""

    def __init__(self, ambiguities: tuple[IntakeAmbiguity, ...]) -> None:
        super().__init__("natural-language task requires a product clarification")
        self.ambiguities = ambiguities


class TaskIdGenerator:
    """Generate human-readable task IDs behind injected time and entropy seams."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        entropy: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._entropy = entropy or (lambda: secrets.token_hex(3).upper())

    def generate(self) -> TaskId:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise DomainError("task ID clock must return a timezone-aware datetime")
        suffix = self._entropy().upper()
        if re.fullmatch(r"[A-Z0-9]{6,12}", suffix) is None:
            raise DomainError(
                "task ID entropy must contain 6-12 uppercase letters/digits"
            )
        return TaskId(f"V3-{now.astimezone(UTC):%Y%m%d-%H%M%S}-{suffix}")


class GitRepositoryLocator:
    """Resolve the actual Git root from cwd or an explicit candidate directory."""

    def resolve(self, candidate: Path | None = None) -> Path:
        start = (candidate or Path.cwd()).expanduser().resolve()
        if not start.is_dir():
            raise DomainError(f"repository candidate is not a directory: {start}")
        try:
            completed = subprocess.run(
                ("git", "-C", str(start), "rev-parse", "--show-toplevel"),
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise DomainError(
                f"cannot discover a Git repository from {start}: {exc}"
            ) from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "git rev-parse failed"
            raise DomainError(f"cannot discover a Git repository from {start}: {detail}")
        raw_root = completed.stdout.strip()
        if not raw_root:
            raise DomainError(f"Git returned an empty repository root for {start}")
        root = Path(raw_root).expanduser()
        if not root.is_absolute():
            root = start / root
        root = root.resolve()
        if not root.is_dir() or not start.is_relative_to(root):
            raise DomainError(
                f"Git returned an invalid repository root {root} for {start}"
            )
        return root


class IntakeRiskPolicy:
    """Convert validated semantic facts into conservative risk and FAST eligibility."""

    def classify(
        self, signals: IntakeRiskSignals, *, scope_size: int
    ) -> tuple[RiskLevel, bool]:
        high_risk = any(
            (
                signals.security_or_privacy_impact,
                signals.data_impact,
                signals.operational_impact,
            )
        )
        semantic_impact = any(
            (
                signals.public_contract_impact,
                signals.configuration_impact,
                signals.architecture_or_ownership_impact,
                signals.dependency_impact,
                signals.compatibility_impact,
                signals.uncertainty_present,
            )
        )
        no_disqualifying_impact = not high_risk and not semantic_impact
        fast_eligible = all(
            (
                signals.exact_outcome,
                signals.unique_repository_evidence,
                signals.cohesive_scope,
                signals.focused_verification_available,
                scope_size <= 3,
                no_disqualifying_impact,
            )
        )
        if fast_eligible:
            return RiskLevel.TRIVIAL_MECHANICAL, True
        if high_risk:
            return RiskLevel.HIGH_RISK, False
        if semantic_impact:
            return RiskLevel.STANDARD, False
        if signals.exact_outcome and signals.unique_repository_evidence:
            return RiskLevel.LOW_RISK, False
        return RiskLevel.STANDARD, False


class VerificationCommandPolicy:
    """Reject unsafe model-proposed argv before it reaches human authorization."""

    _BLOCKED_EXECUTABLES = frozenset(
        {
            "bash",
            "cmd",
            "cmd.exe",
            "curl",
            "del",
            "erase",
            "format",
            "powershell",
            "powershell.exe",
            "pwsh",
            "reboot",
            "rm",
            "rmdir",
            "sh",
            "shutdown",
            "sudo",
            "su",
            "wget",
            "zsh",
        }
    )
    _SHELL_TOKENS = frozenset({"&&", "||", ";", "|", ">", ">>", "<", "<<"})
    _READ_ONLY_GIT = frozenset(
        {"diff", "grep", "ls-files", "rev-parse", "show", "status"}
    )
    _BLOCKED_GIT_ARGUMENTS = frozenset(
        {"--ext-diff", "--open-files-in-pager", "--output", "--textconv"}
    )

    def compile(
        self,
        proposal: VerificationCommandProposal,
        *,
        command_id: CommandId,
        repository_root: Path,
    ) -> RequiredCommand:
        argv = proposal.argv
        if not argv or any(not part for part in argv):
            raise DomainError("generated verification command argv must not be empty")
        if any("\0" in part or "\n" in part or "\r" in part for part in argv):
            raise DomainError("generated command argv contains a control character")
        if any(part in self._SHELL_TOKENS for part in argv):
            raise DomainError("generated command contains shell control syntax")

        executable = argv[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
        if executable in self._BLOCKED_EXECUTABLES:
            raise DomainError(
                f"generated verification executable is not permitted: {argv[0]}"
            )
        is_python = (
            re.fullmatch(r"(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?", executable)
            is not None
        )
        if is_python and "-c" in argv[1:]:
            raise DomainError("inline Python is not a permitted verification command")
        if executable in {"git", "git.exe"} and (
            len(argv) < 2 or argv[1] not in self._READ_ONLY_GIT
        ):
            raise DomainError("generated Git command must be an approved read-only form")
        if executable in {"git", "git.exe"} and any(
            part in self._BLOCKED_GIT_ARGUMENTS or part.startswith("--output=")
            for part in argv[2:]
        ):
            raise DomainError("generated Git command contains a write/exec option")

        command_cwd = self._normalize_cwd(proposal.cwd)
        command = RequiredCommand(
            command_id=command_id,
            argv=argv,
            cwd=command_cwd,
            required=True,
            rationale=proposal.rationale,
            output_handling=OutputHandling.STATUS_ONLY,
        )
        cwd = (repository_root / command.cwd).resolve()
        if not cwd.is_relative_to(repository_root) or not cwd.is_dir():
            raise DomainError(
                f"generated command cwd is not a repository directory: {command.cwd}"
            )
        return command

    @staticmethod
    def _normalize_cwd(value: str) -> str:
        raw = value.replace("\\", "/")
        path = PurePosixPath(raw)
        if (
            not raw
            or any(character in raw for character in "\0\n\r\t")
            or path.is_absolute()
            or raw.startswith("//")
            or re.match(r"^[A-Za-z]:", raw) is not None
            or ".." in path.parts
        ):
            raise DomainError("generated command cwd must be repository-relative")
        return "." if path == PurePosixPath(".") else path.as_posix()


class TaskCompiler:
    """Compile provider-derived facts into the existing complete strict TaskSpec."""

    def __init__(
        self,
        *,
        risk_policy: IntakeRiskPolicy | None = None,
        command_policy: VerificationCommandPolicy | None = None,
        routing: RoutingPolicy | None = None,
    ) -> None:
        self._risk = risk_policy or IntakeRiskPolicy()
        self._commands = command_policy or VerificationCommandPolicy()
        self._routing = routing or RoutingPolicy()

    def compile(
        self,
        request: NaturalLanguageTaskRequest,
        analysis: TaskIntakeAnalysis,
        task_id: TaskId,
    ) -> CompiledTask:
        if analysis.ambiguities:
            raise IntakeClarificationRequired(analysis.ambiguities)
        scope = self._scope(analysis.candidate_scope, request.repository_root)
        if not analysis.verification_commands:
            raise DomainError("intake analysis produced no focused verification commands")
        commands = tuple(
            self._commands.compile(
                proposal,
                command_id=CommandId(f"CMD-{index:03d}"),
                repository_root=request.repository_root,
            )
            for index, proposal in enumerate(analysis.verification_commands, start=1)
        )
        risk, fast_eligible = self._risk.classify(
            analysis.risk_signals, scope_size=len(scope)
        )
        spec = TaskSpec(
            task_id=task_id,
            description=request.description.strip(),
            acceptance_criteria=analysis.acceptance_criteria,
            risk=risk,
            fast_eligible=fast_eligible,
            repository_root=request.repository_root,
            required_commands=commands,
            fingerprint_scope=scope,
        )
        return CompiledTask(spec, analysis, self._routing.decide(spec))

    @staticmethod
    def _scope(paths: tuple[str, ...], repository_root: Path) -> tuple[str, ...]:
        if not paths:
            raise DomainError("intake analysis produced an empty authorized file scope")
        normalized = tuple(normalize_repository_path(path) for path in paths)
        if len(normalized) != len(set(normalized)):
            raise DomainError("generated file scope contains duplicate paths")
        for path in normalized:
            if any(character in path for character in "*?["):
                raise DomainError(
                    f"generated file scope must not contain wildcards: {path}"
                )
            parts = PurePosixPath(path).parts
            if any(part.lower() == ".git" for part in parts):
                raise DomainError("generated file scope must not include Git metadata")
            resolved = (repository_root / path).resolve()
            if not resolved.is_relative_to(repository_root):
                raise DomainError(f"generated scope escaped repository: {path}")
            if resolved.exists() and not resolved.is_file():
                raise DomainError(f"generated scope path is not a file: {path}")
        return normalized


class TaskIntakeService:
    """Coordinate read-only analysis, local validation, identity, and compilation."""

    def __init__(
        self,
        analyzer: TaskIntentAnalyzer,
        *,
        task_ids: TaskIdGenerator | None = None,
        compiler: TaskCompiler | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._task_ids = task_ids or TaskIdGenerator()
        self._compiler = compiler or TaskCompiler()

    def compile(self, request: NaturalLanguageTaskRequest) -> CompiledTask:
        result = self._analyzer.analyze(request)
        if result.status is TransportStatus.FAILED or result.raw_response is None:
            raise IntakeProviderFailure(
                result.failure_kind or FailureKind.INVOCATION_FAILED,
                result.error_message or "intake provider returned no analysis",
            )
        try:
            analysis = parse_intake_analysis(result.raw_response)
        except IntakeAnalysisError as exc:
            raise IntakeProviderFailure(
                FailureKind.MALFORMED_ARTIFACT,
                f"intake provider returned malformed analysis ({exc.code.value})",
            ) from exc
        return self._compiler.compile(request, analysis, self._task_ids.generate())


@dataclass(frozen=True, slots=True)
class ScriptedIntakeResponse:
    raw_response: str | None = None
    failure_kind: FailureKind | None = None
    error_message: str | None = None


class ScriptedTaskIntentAnalyzer:
    """FIFO offline intake fake whose invocation count and request are observable."""

    def __init__(self, responses: list[ScriptedIntakeResponse]) -> None:
        self._responses = deque(responses)
        self.requests: list[NaturalLanguageTaskRequest] = []

    def analyze(self, request: NaturalLanguageTaskRequest) -> TaskIntakeProviderResult:
        self.requests.append(request)
        if not self._responses:
            return TaskIntakeProviderResult(
                TransportStatus.FAILED,
                None,
                FailureKind.INVOCATION_FAILED,
                "scripted intake responses exhausted",
            )
        response = self._responses.popleft()
        if response.failure_kind is not None:
            return TaskIntakeProviderResult(
                TransportStatus.FAILED,
                None,
                response.failure_kind,
                response.error_message or "scripted intake failure",
            )
        return TaskIntakeProviderResult(
            TransportStatus.SUCCEEDED,
            response.raw_response,
            provider_request_id=f"scripted-intake-{len(self.requests)}",
            usage={"input_tokens": 0, "output_tokens": 0},
        )

    @property
    def remaining(self) -> int:
        return len(self._responses)


def build_intake_prompt(request: NaturalLanguageTaskRequest) -> str:
    """Build a read-only repository-analysis prompt without orchestration authority."""
    context = {
        "user_description": request.description,
        "human_clarifications": request.clarifications,
        "repository_root": str(request.repository_root),
    }
    return "\n\n".join(
        (
            "You are the read-only V3 task-intake analyst.",
            "Inspect repository instructions, source, tests, configuration, and "
            "documentation relevant to the user's exact request. Use only read-only "
            "inspection operations. Do not edit files, execute proposed verification "
            "commands, authorize commands, choose FAST/FULL, or generate IDs.",
            "Return exactly one JSON object matching the supplied schema. Candidate "
            "scope must be narrow repository-relative file paths with no globs. "
            "Verification commands must be repository-supported shell-free argv with "
            "repository-relative cwd. Report only consequential product ambiguities; "
            "do not convert ordinary engineering investigation into a user question.",
            "Risk signals are facts, not a routing verdict. Set uncertainty_present "
            "whenever evidence does not justify a confident fact. The original user "
            "description remains authoritative and unrelated requirements must not be "
            "invented.",
            "Task-scoped context:\n" + json.dumps(context, indent=2, sort_keys=True),
        )
    )


__all__ = [
    "GitRepositoryLocator",
    "IntakeClarificationRequired",
    "IntakeProviderFailure",
    "IntakeRiskPolicy",
    "ScriptedIntakeResponse",
    "ScriptedTaskIntentAnalyzer",
    "TaskCompiler",
    "TaskIdGenerator",
    "TaskIntakeService",
    "VerificationCommandPolicy",
    "build_intake_prompt",
]
