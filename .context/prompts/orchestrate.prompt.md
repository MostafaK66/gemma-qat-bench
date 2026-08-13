# Orchestrate a Planning Workflow (V1)

Use this prompt to run Orchestration V1 for a non-trivial task when you want an evidence-based plan plus independent plan review before implementation.

## Task

Orchestrate planning for: `<task description>`

## Required loading

1. `AGENTS.md`
2. `llms.txt`
3. `.context/AGENT-ROLES.md`
4. `.github/skills/orchestration/SKILL.md`

## V1 boundary

V1 performs planning and independent plan review only, then stops.

It does not implement product/source changes.

## Required workflow

Intake
-> Planner phase
-> Plan Critic phase
-> Gate 1 verdict
-> if `CHANGES REQUESTED`, classify blockers for routing
-> bounded revision when needed (maximum planner revisions: `2`)
-> `PLAN APPROVED` or `ESCALATE TO HUMAN`
-> STOP

## Orchestrator responsibilities

- classify task type and risk
- right-size orchestration depth
- initialize task-scoped handoff from `.context/handoff-TEMPLATE.md`
- persist orchestration state in `.context/handoffs/<task-id>.md`
- invoke Planner and Plan Critic phases
- pass structured artifacts between phases
- enforce gate semantics and retry budget
- enforce blocker-class routing (`EVIDENCE_RESOLVABLE` vs `HUMAN_INTENT_REQUIRED`)
- record gate history and available execution/model metadata
- escalate when required by contract

## Trivial-task handling

If task is trivial (for example typo or obvious one-line mechanical fix), explain that full orchestration is unnecessary and recommend a lighter workflow.

Do not silently modify files in this mode.

## Gate 1 verdict contract

Allowed verdicts are exactly:

- `APPROVED`
- `CHANGES REQUESTED`

No third state.

Approval invariant:

- `APPROVED` means implementation-ready as written.
- The Implementer must not need to decide unresolved items that could materially change public behavior, API/CLI behavior, configuration semantics, architecture/ownership, security behavior, data behavior, compatibility, acceptance criteria, or intended product behavior.

If unresolved blocking decisions exist, verdict must be `CHANGES REQUESTED`.

If only genuinely non-material/mechanical questions remain, `APPROVED` is allowed and suggestions are recorded separately.

## Revision loop contract

- Plan Critic must evaluate the latest revised plan.
- Planner must address each blocking finding explicitly.
- Preserve valid prior plan content; avoid unnecessary rewrites.
- Maximum planner revision budget is `2`.
- If not approved within budget, escalate to human.

Orchestrator enforcement:

- Orchestrator must enforce the Plan Critic verdict and must not convert `CHANGES REQUESTED` into approval.
- If all blocking findings are `EVIDENCE_RESOLVABLE`, return findings to Planner for revision.
- If any blocking finding is `HUMAN_INTENT_REQUIRED` (including mixed blocker sets), transition to `AWAITING_HUMAN_CLARIFICATION` before any Planner revision.
- In `AWAITING_HUMAN_CLARIFICATION`, ask the human only for unresolved intent decisions, keep evidence-resolvable findings recorded as outstanding, and wait.
- After human clarification, pass explicit human decision(s) plus outstanding evidence-resolvable findings to Planner as revision requirements, then run Critic re-review.
- Waiting for human clarification does not consume planner revision budget by itself.
- Planner must not run while orchestration is in `AWAITING_HUMAN_CLARIFICATION`; normal flow blocks Planner invocation until clarification is recorded.

Revision accounting remains:

- iteration 1 = initial plan
- iteration 2 = revision 1
- iteration 3 = revision 2

## Execution mode and model metadata

Record only what is known from runtime evidence.

For `chat-simulation`, explicitly allow metadata such as:

- execution mode: `chat-simulation`
- actual isolated model: not independently controlled
- model family: not independently controlled / unknown
- fallback used: not applicable

Do not claim isolated agents or heterogeneous model-family execution unless runtime evidence confirms it.

## Output

Return:

- final V1 state: `PLAN APPROVED` or `ESCALATE TO HUMAN`
- iteration count used
- structured plan and plan-review artifacts
- blocking findings and resolutions across iterations
- any pause/resume transitions and human clarification decisions used for resume
- residual risks and open questions
- handoff path used: `.context/handoffs/<task-id>.md`

`PLAN APPROVED` is allowed only after a revised-or-initial `PLAN` receives Plan Critic `APPROVED` under the approval invariant above.
