# V3 requirements freeze and V2 migration map

This document freezes the repository evidence used to implement V3. It is a migration
record, not a continuation of the V2.5 single-agent versus multi-agent evaluation.

## Authoritative V2 inputs

The following existing files define the behavior V3 preserves:

- `.context/AGENT-ROLES.md` — role ownership, conservative FAST eligibility, Gates,
  evidence boundaries, revisions, fingerprints, and Git non-authorization.
- `.context/prompts/orchestrate.prompt.md` — FAST/FULL sequencing, ledger ownership,
  implementation fingerprint, and failure routing.
- `.context/prompts/plan.prompt.md` and `critique-plan.prompt.md` — Planner and Plan
  Critic ownership and Gate 1 semantics.
- `.context/prompts/implement.prompt.md`, `verify.prompt.md`, and
  `review-implementation.prompt.md` — implementation, Gate 2, and Gate 3 role
  contracts.
- `.context/prompts/repair-verification-schema.prompt.md` — one schema-only Verifier
  retry, unchanged-content precondition, and second-malformed fail-closed behavior.
- `.github/skills/orchestration/SKILL.md` — repository-level orchestration procedure.
- `.github/agents/*.agent.md` — specialist profile descriptions.
- `tests/test_agent_framework_contract.py` — V2 asset-level contract regression suite.

V3 does not modify prior V2/V2.5 evaluation outputs or resume model bake-off work.

## Frozen behavioral invariants

| Concern | Frozen requirement | V3 authority |
| --- | --- | --- |
| Routing | FAST only for explicitly eligible `TRIVIAL_MECHANICAL`; all other risk classes start FULL | `routing.RoutingPolicy` |
| Sequencing | Deterministic software chooses every next state | `state_machine.WorkflowMachine`, `engine.Orchestrator` |
| Gate 1 | Plan Critic owns `APPROVED` or `CHANGES_REQUESTED` | typed `PLAN_CRITIQUE` artifact plus engine |
| Gate 2 | Verifier owns semantic `PASSED` or `FAILED`; malformed output is not a verdict | strict artifact validation plus engine |
| Gate 3 | FULL Reviewer owns `APPROVED` or `CHANGES_REQUESTED`; FAST records no Gate 3 | strict `REVIEW` artifact plus engine |
| Verification | Only the command broker owns authoritative execution state | `commands.CommandBroker` and `evidence.EvidenceLedger` |
| Evidence | One fingerprint-bound ledger exists per attempt | `EvidenceBinding` and `EvidenceLedger` |
| Freshness | Drift invalidates evidence before Verifier, schema repair, or Reviewer | `FingerprintService` and engine checkpoints |
| Schema repair | One no-product-change Verifier repair; second malformed response escalates | `verifier_schema_repair` budget |
| Revisions | At most two plan revisions and two shared implementation revisions | typed `RevisionBudget` values |
| Failure | Provider transport, malformed artifact, product failure, and environment failure remain distinct | `FailureKind` and machine-readable escalation |
| Human authority | Commands, Git, and degraded mode are explicit authorization actions | `authorization` port |
| Git | `CHANGE_COMPLETE` never authorizes stage, commit, push, merge, or deployment | completion result and CLI output |

Natural-language convenience is an outer boundary, not an exception to these
invariants. A read-only analyzer returns strict semantic facts; deterministic Python
validates those facts and compiles the same complete `TaskSpec` consumed by the existing
engine. The engine never parses or interprets raw natural-language intake.

## V2 defects converted to regression coverage

| V2 problem | V3 behavior | Regression location |
| --- | --- | --- |
| Verifier returned prose or malformed structure repeatedly | Exactly one JSON root is parsed; one bounded Verifier schema repair; second malformed escalates | `tests/v3/test_artifacts.py`, `test_engine.py` |
| JetBrains combined wrapper obscured the raw payload boundary | Provider adapter returns one explicit `raw_response`; wrapper stripping is forbidden | `specialists.py`, `codex_adapter.py` |
| Command evidence could become stale after file changes | Content fingerprint is checked before Gate 2, repair, and Gate 3; stale ledger is invalidated | fingerprint drift engine tests |
| Incomplete implementation was followed by a failed required check | A failed required command deterministically re-enters IMPLEMENTATION and consumes the shared budget | command-revision engine test |
| A malformed repair could be interpreted as a result | Repair output is validated through the same strict parser and fails closed | double-malformed engine test |
| Model prose could omit an unexpected changed file | Git task-start identities produce an actual delta that is folded into fingerprint scope before a scope violation is raised | scope tests |
| Canonical command fields leaked into a specialist verdict | Recursive prohibited-field validation rejects competing ledger reconstruction | artifact tests |

## Migration clarifications

- V2 prose artifacts remain useful human templates. V3 specialist boundaries use JSON
  with closed schemas so provider structured output can enforce the same shape.
- `ENVIRONMENT_TOOLING_FAILURE` appeared as a Gate 2 finding kind in V2 and is also
  explicitly required as a V3 failure kind. V3 makes it a machine failure category and
  retains the same literal for migration clarity.
- The V2 JetBrains `run_subagent` transport is not part of the V3 core. V3 uses a
  provider-independent `SpecialistClient` protocol.
- Provider schema enforcement reduces malformed responses but never becomes the local
  source of truth. V3 always validates the captured final response again.
- Prior orchestration handoffs and world-state files are not product fingerprint scope.
  A compiled or explicit task specification authorizes product scope, while the Git
  delta detector prevents undeclared task changes from being omitted.
- Natural-language users do not select a risk enum or FAST eligibility. Structured risk
  facts feed deterministic `IntakeRiskPolicy`; uncertainty and semantic impact route
  FULL, and high-risk facts are never downgraded for convenience.
- Natural-language verification commands are proposals until local policy validates
  their shell-free argv and repository-contained cwd. The broker still requires a
  separate human authorization decision before execution.
- Checkpoint schema v2 stores the complete validated `TaskSpec` for task-ID-only resume.
  Schema v1 remains readable and resumes through its original explicit task file.

## Requirement traceability

| V3 requirement area | Implementation |
| --- | --- |
| Typed domain and budgets | `domain.py` |
| Natural-language intake domain and provider port | `intake_domain.py` |
| Strict intake schema and local parsing | `intake_artifacts.py` |
| Repository discovery and deterministic task compilation | `intake.py` |
| State machine and routing | `state_machine.py`, `routing.py` |
| Specialist protocol and SDK | `specialists.py`, `codex_adapter.py` |
| Artifact schemas | `artifacts.py` |
| Authorization and command broker | `authorization.py`, `commands.py` |
| Canonical evidence | `evidence.py` |
| Fingerprints and actual scope | `fingerprint.py`, `scope.py` |
| Persistence and resume | `persistence.py`, `runtime.py`, `Orchestrator.resume` |
| Observability | `events.py` and engine events |
| Natural-language and advanced explicit CLI | `orchestration/cli.py`, `configs/v3-task.example.json` |
| Offline verification | `tests/v3/` |
