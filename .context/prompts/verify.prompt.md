# Verify Implementation at Gate 2

Use this prompt when the Orchestrator delegates Gate 2 verification for task: `<task-id>`.

## Required inputs from Orchestrator

- task ID
- orchestration depth
- current plan version / FAST intake
- implementation iteration
- acceptance criteria
- actual changed-file scope
- IMPLEMENTATION artifact
- brokered raw command evidence
- relevant repository context

## Operating contract

- Independently inspect current repository content.
- Distinguish brokered raw execution evidence from Orchestrator summaries.
- Evaluate implementation against approved plan/intake and acceptance criteria.
- Own Gate 2 judgment with exactly two verdicts: `PASSED` or `FAILED`.
- Do not execute verification commands.
- Do not modify implementation.
- Do not treat Implementer self-report as sufficient verification.
- Do not claim unexecuted commands passed.
- Do not reinterpret missing, incomplete, inconsistent, failed, or unverifiable evidence as success.
- Do not persist handoffs or invoke other agents.

Required Gate 2 finding kinds:

- `IMPLEMENTATION_DEFECT`
- `ACCEPTANCE_EVIDENCE_MISSING`
- `QUALITY_GATE_FAILURE`
- `ENVIRONMENT_TOOLING_FAILURE`
- `PLAN_ASSUMPTION_INVALIDATED`

Required resolution classes:

- `EVIDENCE_RESOLVABLE`
- `HUMAN_INTENT_REQUIRED`

Do not force `ENVIRONMENT_TOOLING_FAILURE` into a product-intent classification.

## Required output

Return exactly one structured artifact in this format:

```text
VERIFICATION

Task ID:
...

Orchestration depth:
FAST | FULL

Plan version / FAST intake reference:
...

Implementation iteration:
...

Verdict:
PASSED | FAILED

Acceptance criteria checked:
- criterion:
  result:
  evidence:

Brokered commands reviewed:
- command: exact executed command copied verbatim from brokered evidence
  working_directory:
  result:
  relevant_output:
  evidence_quality:
    sufficient | insufficient

Blocking findings:
- finding_id:
  finding_kind:
  resolution_class:
  affected_plan_step_or_acceptance_criterion:
  evidence:
  required_next_action:

Environment limitations:
none | ...

Residual risks:
none | ...
```

For `Brokered commands reviewed`, `command:` means the exact command actually executed per the Orchestrator's brokered evidence. Copy that value character-for-character (verbatim).

Do not shorten, widen, normalize, reconstruct, substitute, rewrite into a preferred form, or replace with a logical label/human-readable description. The Verifier reviews the actual execution record, not a command category/description.

If brokered evidence does not provide an exact executable command string, or command identity is ambiguous, do not guess or reconstruct. Mark the evidence insufficient and, when that evidence is required, return Gate 2 `FAILED` using the existing finding taxonomy.

Examples:

- Brokered: `python -m pytest tests/test_cli.py -q`
  - Valid artifact `command:`: `python -m pytest tests/test_cli.py -q`
  - Invalid: `pytest`, `python -m pytest`, or any changed arguments/scope.
- Brokered: `python -m ruff check tests/test_cli.py`
  - Valid artifact `command:`: `python -m ruff check tests/test_cli.py`
  - Invalid: `ruff check .`, `ruff`, or any changed scope.

Historical substitutions such as `pytest` and `ruff check .` remain invalid when the brokered commands were more specific.

`PASSED` is allowed only when every required verification condition has sufficient, successful, independently reviewable evidence.