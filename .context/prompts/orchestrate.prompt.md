# Orchestrate a Planning Workflow (V1 / V1.5)

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

## Execution mode, delegation, and model metadata

Record only what is known from runtime evidence.

Choose and record a requested execution mode before invoking specialist phases:

- `chat-simulation`: Planner and Plan Critic run sequentially in this main Copilot conversation/session; independent model control is not guaranteed.
- `ide-custom-agent`: use `.github/agents/planner.agent.md` and `.github/agents/plan-critic.agent.md` when custom-agent discovery and delegation are available. The mechanism name is runtime-specific; in the validated JetBrains environment it is `run_subagent`. The profiles provide repository read/search capability only through `list_dir`, `read_file`, `file_search`, and `grep_search`. The main Copilot Agent/chat remains Orchestrator: invoke Planner, receive `PLAN`, persist it, invoke Plan Critic with the PLAN, receive `PLAN REVIEW`, persist it, then enforce Gate 1.
- `sdk-sub-agent`: future programmatic mode only; do not claim or emulate SDK-level isolated contexts in V1.5.

For `ide-custom-agent`, concrete profile `model:` values are human-selected runtime configuration and may vary by environment or organization; retain conceptual model slots in generic contracts. Prefer different suitable Planner and Plan Critic model families for medium/high-risk work. Record `configured_model`, `actual_model`, `model_family`, `delegation_verified`, `configured_model_family_diversity`, and `heterogeneous_execution_verified` separately. Configured diversity is `yes` only when configured families are known and distinct; heterogeneous execution is `yes` only when runtime/UI evidence proves actual delegated executions used distinct families. Never infer actual model use from a configured profile value.

If custom-agent discovery or delegated invocation is unavailable, set actual execution mode to `chat-simulation`; record fallback used and its reason; record model independence as unknown/not independently controlled; and continue the existing sequential Planner/Critic workflow. Do not fail Gate 1 solely because heterogeneous execution is unavailable.

For `chat-simulation`, explicitly allow metadata such as:

- execution mode: `chat-simulation`
- actual isolated model: not independently controlled
- model family: not independently controlled / unknown
- fallback used: not applicable

Do not claim isolated agents, actual serving models, or heterogeneous model-family execution unless runtime/UI evidence confirms them.

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
