from __future__ import annotations

from pathlib import Path

import pytest

from gemma_qat_bench.orchestration.authorization import StaticAuthorization
from gemma_qat_bench.orchestration.commands import CommandBroker, RunnerResult
from gemma_qat_bench.orchestration.domain import (
    AuthorizationStatus,
    CommandId,
    CommandStatus,
    DomainError,
    OutputHandling,
    RequiredCommand,
    TaskId,
    WorkflowDepth,
    WorkflowState,
)
from gemma_qat_bench.orchestration.persistence import (
    JsonFileWorkflowStore,
    StoredEvidence,
    WorkflowSnapshot,
)


class Runner:
    def __init__(self, result: RunnerResult) -> None:
        self.result = result
        self.commands: list[RequiredCommand] = []

    def run(self, command: RequiredCommand) -> RunnerResult:
        self.commands.append(command)
        return self.result


def command() -> RequiredCommand:
    return RequiredCommand(CommandId("CMD-001"), ("pytest", "-q"))


def test_command_broker_requires_explicit_authorization() -> None:
    runner = Runner(RunnerResult(0, "passed"))
    broker = CommandBroker(runner, StaticAuthorization())
    result = broker.execute((command(),), fingerprint="abc")
    assert result[0].status is CommandStatus.AUTHORIZATION_REQUIRED
    assert not runner.commands


def test_command_broker_distinguishes_product_and_environment_failure() -> None:
    authorized = StaticAuthorization(commands=AuthorizationStatus.AUTHORIZED)
    failed = CommandBroker(Runner(RunnerResult(1, stderr="test failed")), authorized)
    assert (
        failed.execute((command(),), fingerprint="abc")[0].status is CommandStatus.FAILED
    )

    environment = CommandBroker(
        Runner(RunnerResult(None, environment_error="executable missing")), authorized
    )
    assert environment.execute((command(),), fingerprint="abc")[0].status is (
        CommandStatus.ENVIRONMENT_ERROR
    )


def test_subprocess_runner_tolerates_undecodable_command_output(
    tmp_path: Path,
) -> None:
    """Regression: non-UTF-8 stdout/stderr raised UnicodeDecodeError out of the
    runner, crashing the workflow on every run and every resume."""
    import sys

    from gemma_qat_bench.orchestration.commands import SubprocessCommandRunner

    runner = SubprocessCommandRunner(tmp_path)
    binary_command = RequiredCommand(
        CommandId("CMD-BIN"),
        (
            sys.executable,
            "-c",
            "import sys;"
            "sys.stdout.buffer.write(b'\\xff\\xfe ok');"
            "sys.stderr.buffer.write(b'\\xff err')",
        ),
    )
    result = runner.run(binary_command)
    assert result.environment_error is None
    assert result.exit_code == 0
    assert "ok" in result.stdout
    assert "err" in result.stderr


def test_command_output_requires_explicit_excerpt_policy() -> None:
    authorization = StaticAuthorization(commands=AuthorizationStatus.AUTHORIZED)
    status_only = CommandBroker(Runner(RunnerResult(0, "secret")), authorization)
    assert (
        "secret"
        not in status_only.execute((command(),), fingerprint="abc")[0].output_excerpt
    )

    excerpt_command = RequiredCommand(
        CommandId("CMD-001"),
        ("pytest", "-q"),
        output_handling=OutputHandling.EXCERPT,
    )
    excerpt = CommandBroker(Runner(RunnerResult(0, "permitted")), authorization)
    assert (
        "permitted"
        in excerpt.execute((excerpt_command,), fingerprint="abc")[0].output_excerpt
    )


def snapshot() -> WorkflowSnapshot:
    return WorkflowSnapshot(
        1,
        TaskId("T-1"),
        WorkflowState.COMMAND_VERIFICATION,
        WorkflowDepth.FULL,
        "STANDARD",
        1,
        1,
        1,
        {"plan_revision": {"limit": 2, "consumed": 1}},
        "APPROVED",
        None,
        None,
        (),
        (),
        (
            StoredEvidence(
                "CMD-001",
                ("pytest", "-q"),
                ".",
                "SUCCEEDED",
                0,
                "passed",
                False,
                True,
                "abc",
            ),
        ),
        "abc",
        ("product.py",),
        {},
        None,
        (),
        0,
    )


def test_json_store_round_trip_and_mode(tmp_path: Path) -> None:
    store = JsonFileWorkflowStore(tmp_path)
    expected = snapshot()
    store.save(expected)
    assert store.load(TaskId("T-1")) == expected
    assert (tmp_path / "T-1.json").stat().st_mode & 0o777 == 0o600


def test_json_store_rejects_corruption(tmp_path: Path) -> None:
    path = tmp_path / "T-1.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(DomainError, match="invalid workflow snapshot"):
        JsonFileWorkflowStore(tmp_path).load(TaskId("T-1"))


def test_json_store_rejects_wrong_shaped_snapshot_values(tmp_path: Path) -> None:
    """Regression: a mapping field persisted as a list (for example budgets)
    raised a raw AttributeError instead of the DomainError corruption signal."""
    import json

    store = JsonFileWorkflowStore(tmp_path)
    store.save(snapshot())
    payload = json.loads((tmp_path / "T-1.json").read_text(encoding="utf-8"))
    payload["budgets"] = []
    (tmp_path / "T-1.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DomainError, match="invalid workflow snapshot"):
        store.load(TaskId("T-1"))


def test_json_store_creates_a_private_state_directory(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    JsonFileWorkflowStore(state_dir).save(snapshot())
    assert state_dir.stat().st_mode & 0o777 == 0o700
