# Orchestration Handoff - <task title>

Task ID:
Created:
Requested execution mode: `chat-simulation` | `ide-custom-agent` | `sdk-sub-agent`
Actual execution mode: `chat-simulation` | `ide-custom-agent` | `sdk-sub-agent`
Source branch/context:
Current state: `INTAKE` | `PLAN` | `PLAN_REVIEW` | `AWAITING_HUMAN_CLARIFICATION` | `PLAN APPROVED` | `ESCALATE TO HUMAN`

## Task

- User request:
- Intended outcome:
- In scope:
- Out of scope:

## Classification

Type:
Risk:
Orchestration depth:

## Execution / model metadata

Record known metadata only; do not invent runtime details.

| Role | Custom-agent profile (if used) | `configured_model` (if known) | `actual_model` (if runtime/UI known) | `model_family` (if runtime/UI known) | Reasoning config (if known) |
| --- | --- | --- | --- | --- | --- |
| Orchestrator |  | `orchestrator_model` |  |  |  |
| Planner |  | `planner_model` |  |  |  |
| Plan Critic |  | `plan_critic_model` |  |  |  |

| `delegation_verified` (yes/no/unknown) | `configured_model_family_diversity` (yes/no/unknown) | `heterogeneous_execution_verified` (yes/no/unknown) | `fallback_used` (yes/no/not applicable) | `fallback_reason` |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

For V1 chat simulation, explicit placeholders are acceptable, for example:

- actual isolated model: not independently controlled
- model family: not independently controlled / unknown
- fallback used: not applicable

For V1.5 IDE custom agents, record `configured_model` from the profile and `actual_model`/`model_family` only from runtime/UI evidence. A configured profile property alone does not verify actual delegated execution or serving-model use. Record `configured_model_family_diversity: yes` only when configured families are known and distinct; different identifiers alone are insufficient. Record `heterogeneous_execution_verified: yes` only when runtime/UI evidence proves actual delegated executions used distinct model families. The validated JetBrains mechanism is `run_subagent`, but delegation mechanism names are runtime-specific.

## Context

- Key repository evidence reviewed:
- Applicable instructions/skills:
- Constraints:

## Iteration semantics

- Iteration 1 = initial plan
- Iteration 2 = revision 1
- Iteration 3 = revision 2 (final allowed revision within V1)

Budget invariant:

- Only creation of a revised `PLAN` consumes revision budget.
- Entering/waiting/exiting `AWAITING_HUMAN_CLARIFICATION` does not consume revision budget.

## Plan iteration 1

```text
PLAN

Goal:

Current behavior / evidence:

Owning responsibility:

Files expected to change:

Implementation steps:
1.
2.
3.

Tests / acceptance criteria:

Risks / unknowns:

Out of scope:

Open questions:
```

## Plan review iteration 1

```text
PLAN REVIEW

Verdict:
APPROVED | CHANGES REQUESTED

Blocking findings:

Suggestions:

Evidence checked:

Residual risks:
```

## Plan iteration 2

(Use only if revision is required.)

## Plan review iteration 2

(Use only if revision is required.)

## Plan iteration 3

(Use only if revision 2 is required.)

## Plan review iteration 3

(Use only if revision 2 is required.)

## Pending human clarification

State:
`AWAITING_HUMAN_CLARIFICATION` | `not applicable`

Trigger plan-review iteration:

Blocking finding IDs requiring human intent:

Blocking classifications:
`HUMAN_INTENT_REQUIRED`

Decision question(s):

Why repository evidence is insufficient:

Clarification request:

Revision count before wait:

## Human clarification response

Status:
`pending` | `received` | `not applicable`

Response source:
`human`

Decision:

Received at:

Revision count after wait:

## Resume mapping

Human decision(s) passed to Planner:

Outstanding evidence-resolvable findings also passed to Planner:

Next plan iteration:

After Plan review iteration 3:

- `APPROVED` -> `PLAN APPROVED`
- `CHANGES REQUESTED` -> revision budget exhausted -> `ESCALATE TO HUMAN`

## Gate history

| Iteration | Gate | Verdict | Blocking findings summary | Blocking classifications | Resulting state |
| --- | --- | --- | --- | --- | --- |
| 1 | Gate 1 (Plan Review) |  |  |  |  |
| 2 | Gate 1 (Plan Review) |  |  |  |  |
| 3 | Gate 1 (Plan Review) |  |  |  |  |

Maximum planner revision budget: `2` (initial plan + up to 2 revisions = up to 3 plan/review cycles).

## Open questions

-

## Final V1 handoff

- Final state: `PLAN APPROVED` | `ESCALATE TO HUMAN`
- Revision count used:
- Why stopped:
- Residual risks:
- Human follow-up requested:

## Reserved future sections

The sections below are inactive in V1 and reserved for future expansion.

### Implementation (inactive in V1)

### Verification (inactive in V1)

### Code review (inactive in V1)
