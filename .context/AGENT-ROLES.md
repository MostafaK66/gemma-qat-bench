# AGENT-ROLES.md - Orchestration Role Contract

This file is the authoritative role, tool, gate, and model contract for orchestration workflows in this repository.

## Execution modes

### Current V1: `chat-simulation`

- Role separation exists at the workflow level.
- Planner and Plan Critic are sequential phases in the same Copilot Chat/session.
- Isolated agent contexts are not guaranteed.
- Independent per-role model assignment is not guaranteed.
- Heterogeneous model-family execution must not be claimed unless runtime evidence exists.

### Future mode: `sdk-sub-agent`

- Specialist roles run as isolated delegated sub-agents.
- Roles can receive role-specific prompts, tools, skills, models, and reasoning configuration.
- Parent Orchestrator enforces deterministic sequencing, gate order, retry budget, and escalation.

## Role table

| Role | Mandate | Product edits? | Tool strategy | Backing prompt / skills | Model strategy |
| --- | --- | --- | --- | --- | --- |
| Orchestrator | Intake, classify risk, initialize handoff, invoke phases, pass structured artifacts, persist orchestration state, enforce gates and budgets, escalate as needed | No | Read repository evidence; write only orchestration-state artifacts | `.context/prompts/orchestrate.prompt.md`; `.github/skills/orchestration/SKILL.md` | `orchestrator_model`; coordination-focused, can prioritize efficiency |
| Planner | Produce smallest coherent evidence-based plan with ownership, files, tests, risks, assumptions, and out-of-scope boundaries | No | Read-only evidence inspection | `.context/prompts/plan.prompt.md`; `project-architecture`, `feature-implementation`, `python-engineering`, task-specific skills | `planner_model`; planning/reasoning-focused |
| Plan Critic | Independently evaluate plan quality, ownership, minimality, correctness risk, test strategy, compatibility, assumptions, and scope control | No | Read-only evidence inspection | `.context/prompts/critique-plan.prompt.md`; `code-review`, `project-architecture`, `testing` | `plan_critic_model`; review/reasoning-focused |
| Implementer (future) | Execute approved plan and update code/tests | Yes (future only) | Scoped implementation tools (future) | future prompt/skill mapping | `implementer_model` |
| Verifier (future) | Independently run checks and verify acceptance evidence | No product edits expected | Verification tools (future) | future prompt/skill mapping | `verifier_model` |
| Reviewer (future) | Judge merge readiness from actual diff and evidence | No product edits expected | Read + review tools (future) | future prompt/skill mapping | `reviewer_model` |

Future roles are documented for expansion readiness only and are inactive in V1.

## V1 state machine (active)

```text
INTAKE
  -> PLAN
  -> PLAN_REVIEW
  -> verdict APPROVED or CHANGES REQUESTED
  -> if CHANGES REQUESTED, inspect blocking finding classifications
  -> any HUMAN_INTENT_REQUIRED? yes -> AWAITING_HUMAN_CLARIFICATION
  -> after explicit human clarification -> Planner revision
  -> if no HUMAN_INTENT_REQUIRED -> Planner revision
  -> bounded plan revision loop
  -> PLAN APPROVED or ESCALATE TO HUMAN
  -> STOP
```

Maximum planner revision budget: `2`.

No implementation phase is active in V1.

## Gate 1 contract

Valid verdicts are exactly:

- `APPROVED`
- `CHANGES REQUESTED`

No vague third state is allowed.

Approval invariant:

- `APPROVED` means implementation-ready as written.
- The Implementer must not need to decide unresolved items that could materially change public behavior, API/CLI behavior, configuration semantics, architecture/ownership, security behavior, data behavior, compatibility, acceptance criteria, or intended product behavior.

Blocking-decision rule:

- If unresolved items could lead to materially different outcomes in those areas, verdict must be `CHANGES REQUESTED`.
- Only genuinely mechanical/non-material open questions may remain under `APPROVED`.

Blocking-finding classification rule (for `CHANGES REQUESTED`):

- `EVIDENCE_RESOLVABLE`: repository evidence uniquely determines the correction without adding a new product/public-contract/architecture decision.
- `HUMAN_INTENT_REQUIRED`: repository evidence does not uniquely determine intended behavior and different reasonable answers could materially change externally observable behavior or acceptance semantics.

If any blocking finding is `HUMAN_INTENT_REQUIRED` (including mixed blocker sets), Orchestrator must pause before any Planner revision.

Role authority:

- Plan Critic classifies blockers; it does not decide product intent.
- Orchestrator owns routing (`revise now` vs `pause for human clarification`), pause/resume state, and human clarification persistence.
- Planner owns plan authorship and must not invent missing human intent.

## Structured artifacts

Planner returns:

```text
PLAN

Goal:
...

Current behavior / evidence:
...

Owning responsibility:
...

Files expected to change:
...

Implementation steps:
1.
2.
3.

Tests / acceptance criteria:
...

Risks / unknowns:
...

Out of scope:
...

Open questions:
...
```

Plan Critic returns:

```text
PLAN REVIEW

Verdict:
APPROVED | CHANGES REQUESTED

Blocking findings:
...

Suggestions:
...

Evidence checked:
...

Residual risks:
...
```

For each blocking finding under `CHANGES REQUESTED`, Plan Critic must provide:

- `finding_id`
- `classification` (`EVIDENCE_RESOLVABLE` | `HUMAN_INTENT_REQUIRED`)
- `decision_question`
- `impact_scope`
- `evidence_basis`
- `required_correction`
- `why_not_uniquely_resolved` (required when classification is `HUMAN_INTENT_REQUIRED`)

When verdict is `CHANGES REQUESTED`, each blocking finding must include:

- plan step/location
- problem
- why it matters
- required correction

If the issue can be resolved from repository evidence, Plan Critic cites the evidence and requests a Planner revision; Plan Critic does not rewrite the plan itself.

If the issue requires user/product intent, Orchestrator records the blocking decision and transitions to `AWAITING_HUMAN_CLARIFICATION` before any Planner revision, then routes clarified intent plus outstanding evidence-resolvable findings back to Planner for one coherent revision and re-review.

Waiting for human clarification does not consume planner revision budget.

Planner revision budget remains exactly `2` revisions:

- iteration 1 = initial plan
- iteration 2 = revision 1
- iteration 3 = revision 2

## Handoff ownership and persistence

Orchestration state persists to task-scoped files:

```text
.context/handoffs/<task-id>.md
```

Do not use a global `.context/handoff.md`.

Ownership boundary is strict:

- Planner does not write handoff files.
- Plan Critic does not write handoff files.
- Orchestrator persists Planner and Critic artifacts to handoff state.

Flow:

```text
Planner -> structured PLAN -> Orchestrator persists
Plan Critic -> structured PLAN REVIEW -> Orchestrator persists
```

Planner and Plan Critic are read-only for both product/repository files and orchestration-state persistence.

## Model-slot policy

Do not hard-code specific commercial model identifiers in orchestration contracts.

Use conceptual slots:

- `orchestrator_model`
- `planner_model`
- `plan_critic_model`
- `implementer_model`
- `verifier_model`
- `reviewer_model`

## Heterogeneous model-family strategy

Model-family diversity is a strong preference when suitable models are available.

Preferred future medium/high-risk relationships:

- `family(planner_model) != family(plan_critic_model)`
- later: `family(implementer_model) != family(reviewer_model)`

This is a preference for stronger independence, not a binary gate requirement.

If diversity is unavailable, record residual orchestration risk. Do not fail an otherwise valid gate solely for that reason.

## Future SDK mapping (conceptual)

Each future role configuration should keep these dimensions independent:

```text
Role
  |- prompt
  |- tools
  |- skills
  |- model
  |- reasoning configuration
```

Changing model assignment must not require rewriting the orchestration state machine.

Example conceptual mapping:

```text
Orchestrator
  prompt: orchestrate
  tools: orchestration/read + handoff persistence
  skills: orchestration
  model slot: orchestrator_model

Planner
  prompt: plan
  tools: read-only
  skills: project-architecture, feature-implementation, python-engineering
  model slot: planner_model

Plan Critic
  prompt: critique-plan
  tools: read-only
  skills: code-review, project-architecture, testing
  model slot: plan_critic_model

Implementer (future)
  model slot: implementer_model

Verifier (future)
  model slot: verifier_model

Reviewer (future)
  model slot: reviewer_model
```

## Skills and least privilege in future SDK sessions

Future SDK sessions should configure the repository skill location explicitly (`.github/skills`).

Do not assume delegated agents inherit all parent skills. Assign only role-appropriate skills and tools.
