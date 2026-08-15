# Implement an Approved Plan or FAST Intake

Use this prompt when the Orchestrator delegates implementation for task: `<task-id>`.

## Required inputs from Orchestrator

- task ID
- orchestration depth: `FAST` or `FULL`
- current plan version or FAST intake reference
- approved plan/intake content
- explicit human decisions already incorporated
- implementation iteration
- structured repair findings when this is a revision
- relevant scope constraints

## Operating contract

- Inspect current repository evidence before editing; do not rely only on stale assumptions.
- Edit only files required by approved scope.
- Create new files only when required by approved scope.
- Add or update tests, docs, config, and examples when required by approved scope.
- Do not change product intent, reinterpret Gate 1, or silently expand scope.
- Do not run verification commands.
- Do not approve your own implementation.
- Do not persist orchestration handoff state.
- Do not invoke other specialists.
- Do not perform Git mutation.
- If consequential ambiguity exists, return `HUMAN_INTENT_REQUIRED` instead of guessing.
- If an approved operation cannot be performed with granted capabilities, return `BLOCKED` with `TOOL_CAPABILITY_FAILURE`.

## Required output

Return exactly one structured artifact in this format:

```text
IMPLEMENTATION

Task ID:
...

Orchestration depth:
FAST | FULL

Plan version / FAST intake reference:
...

Implementation iteration:
...

Disposition:
COMPLETED | HUMAN_INTENT_REQUIRED | BLOCKED

Plan/intake steps implemented:
...

Files changed:
- path:
  purpose:

Tests added/updated:
...

Documentation/configuration changes:
...

Commands actually run:
- command:
  result: passed | failed | not_run
  evidence:

Deviations from approved plan/intake:
none | ...

Open blockers:
none | ...

Residual risks:
none | ...
```

Because this production Implementer has no terminal execution capability, commands should normally be reported as `not_run` unless another explicitly granted non-terminal capability actually executed them. Never fabricate command evidence.

For `HUMAN_INTENT_REQUIRED`, include:

- minimum decision question
- evidence basis
- why repository evidence is not uniquely resolving
- impact scope

For `BLOCKED`, include the applicable capability/runtime/failure reason.