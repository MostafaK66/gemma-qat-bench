from __future__ import annotations

import json
from dataclasses import replace
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
    RiskLevel,
    TaskId,
    TaskSpec,
    WorkflowDepth,
    WorkflowState,
)
from gemma_qat_bench.orchestration.persistence import (
    JsonFileWorkflowStore,
    StoredEvidence,
    WorkflowSnapshot,
    restore_task_spec,
    store_task_spec,
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


def resumable_task_spec(tmp_path: Path) -> TaskSpec:
    return TaskSpec(
        task_id=TaskId("T-1"),
        description="make the exact tested change",
        acceptance_criteria=("the focused check passes",),
        risk=RiskLevel.TRIVIAL_MECHANICAL,
        fast_eligible=True,
        repository_root=tmp_path.resolve(),
        required_commands=(
            RequiredCommand(
                CommandId("CMD-001"),
                ("pytest", "-q"),
                rationale="focused test",
                output_handling=OutputHandling.STATUS_ONLY,
            ),
        ),
        fingerprint_scope=("product.py",),
    )


def test_schema_v2_round_trips_complete_protected_task_spec(tmp_path: Path) -> None:
    spec = resumable_task_spec(tmp_path)
    expected = replace(snapshot(), schema_version=2, task_spec=store_task_spec(spec))
    store = JsonFileWorkflowStore(tmp_path / "state")
    store.save(expected)

    loaded = store.load(spec.task_id)
    assert loaded == expected
    assert loaded is not None and loaded.task_spec is not None
    assert restore_task_spec(spec.task_id, loaded.task_spec) == spec


def test_schema_v2_rejects_coerced_task_spec_boolean(tmp_path: Path) -> None:
    spec = resumable_task_spec(tmp_path)
    state_dir = tmp_path / "state"
    store = JsonFileWorkflowStore(state_dir)
    store.save(replace(snapshot(), schema_version=2, task_spec=store_task_spec(spec)))
    path = state_dir / "T-1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["task_spec"]["fast_eligible"] = "false"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DomainError, match="fast_eligible must be a boolean"):
        store.load(spec.task_id)
