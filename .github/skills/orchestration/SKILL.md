---
name: orchestration
description: Coordinate specialized agent roles through structured handoffs, independent review gates, bounded retry loops, heterogeneous model strategies, and explicit escalation for non-trivial software changes.
---

# Orchestration

Use this skill to coordinate multi-role workflows where planning quality and review independence matter more than immediate implementation speed.

## Scope and intent

Orchestration composes existing repository skills and prompts. It does not replace them.

Core principles:

- author and critic roles are separate
- roles use least-privilege tools
- handoffs use structured artifacts
- gates return explicit verdicts
- retry loops are bounded
- evidence decides gate outcomes
- unresolved consequential ambiguity escalates to a human

## Execution modes

### Mode A: `chat-simulation` (current V1)

- Role separation is enforced by workflow phase and contract.
- Planner and Plan Critic run sequentially in one chat/session.
- Isolated sub-agent context is not guaranteed.
- Independent per-role model assignment is not guaranteed.
- Do not claim heterogeneous model execution unless runtime evidence exists.

### Mode B: `sdk-sub-agent` (future)

- Parent orchestrator delegates to isolated specialist agents.
- Each role may receive role-specific prompt, tools, skills, model, and reasoning configuration.
- Parent enforces role order, gate order, retry budget, and escalation.

## Right-sizing policy

- `trivial`: avoid full orchestration; recommend a lighter workflow and stop.
- `standard`: run V1 planning workflow.
- `high-risk`: run V1 planning workflow and explicitly escalate unresolved consequential decisions.

Do not run maximum orchestration ceremony for every task.

## V1 active workflow

V1 is planning-only orchestration:

1. Intake
2. Planner produces structured `PLAN`
3. Plan Critic produces structured `PLAN REVIEW`
4. Gate 1 verdict is evaluated
5. If needed, bounded revision loop (maximum planner revisions: `2`)
6. End at `PLAN APPROVED` or `ESCALATE TO HUMAN`
7. Stop

V1 must not implement product/source code.

## Gate 1 contract

Valid verdicts are exactly:

- `APPROVED`
- `CHANGES REQUESTED`

No other verdict strings are valid.

Approval invariant:

- `APPROVED` means the plan is implementation-ready as written.
- The Implementer must not need to make unresolved decisions that could materially change public behavior, API/CLI behavior, configuration semantics, architecture/ownership, security behavior, data behavior, compatibility, acceptance criteria, or intended product behavior.

Blocking-decision rule:

- If an unresolved item could produce materially different outcomes in those areas, it is blocking and verdict must be `CHANGES REQUESTED`.
- A non-blocking open question may remain under `APPROVED` only when resolving it is mechanical and cannot materially change the approved behavior/design.

Blocking-finding classification (required for every blocking finding):

- `finding_id`
- `classification` (`EVIDENCE_RESOLVABLE` | `HUMAN_INTENT_REQUIRED`)
- `decision_question`
- `impact_scope`
- `evidence_basis`
- `required_correction`

Additional required field for `HUMAN_INTENT_REQUIRED`:

- `why_not_uniquely_resolved`

Classification rule:

- `EVIDENCE_RESOLVABLE`: repository evidence uniquely determines the correction without introducing a new product/public-contract/architecture decision.
- `HUMAN_INTENT_REQUIRED`: repository evidence may constrain options but does not uniquely determine intended behavior, and different reasonable answers could materially change public behavior, contracts, architecture, compatibility, security/data behavior, or acceptance semantics.

## Planner contract

Planner output format:

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

Planner constraints:

- read-only for repository/product files
- no implementation
- no self-approval
- do not invent missing evidence

## Plan Critic contract

Plan Critic output format:

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

Plan Critic constraints:

- read-only for repository/product files
- no implementation
- no silent plan rewrite
- no confidence-based approvals

Plan Critic must classify every blocking finding using the required fields above.

Plan Critic must explicitly inspect the plan's `Risks / unknowns`, `Open questions`, assumptions, and `Tests / acceptance criteria` before returning `APPROVED`.

For each unresolved item, apply this check:

- Could different reasonable answers cause meaningfully different externally observable behavior, architecture/ownership, compatibility, security/data behavior, or acceptance semantics?

If yes:

- return `CHANGES REQUESTED`
- record the blocking question
- cite relevant repository evidence
- explain why the current plan is not implementation-ready
- specify the required correction

If repository evidence appears sufficient to resolve the question, Plan Critic still must not rewrite the plan itself; it returns `CHANGES REQUESTED` so Planner can revise the `PLAN`.

If human/product intent is required, Plan Critic must classify that blocker as `HUMAN_INTENT_REQUIRED` and explain why repository evidence is not uniquely resolving.

## Handoff ownership and persistence

Use task-scoped files:

```text
.context/handoffs/<task-id>.md
```

Do not use a single shared `.context/handoff.md`.

Ownership boundary:

- Planner returns structured plan artifact.
- Plan Critic returns structured review artifact.
- Orchestrator writes orchestration state and artifacts to handoff file.

Specialist roles do not write orchestration-state files.

## Model strategy

Use conceptual model slots, not hard-coded model names:

- `orchestrator_model`
- `planner_model`
- `plan_critic_model`
- `implementer_model`
- `verifier_model`
- `reviewer_model`

Selection order for future SDK execution:

1. role fitness
2. author/critic independence preference
3. required capability
4. availability
5. cost/latency
6. explicit fallback recording

Preferred medium/high-risk relationships when suitable models are available:

- `family(planner_model) != family(plan_critic_model)`
- later: `family(implementer_model) != family(reviewer_model)`

If family diversity is unavailable, record reduced independence as residual risk. Do not fail a sound gate for that reason alone.

## Deterministic orchestration invariant

Custom agents alone do not enforce workflow correctness.

The orchestrator must enforce deterministic:

- role order
- gate order
- retry limits
- state transitions
- escalation paths

Routing rule after `CHANGES REQUESTED`:

- If any blocking finding is `HUMAN_INTENT_REQUIRED` (including mixed blocker sets), Orchestrator must transition to `AWAITING_HUMAN_CLARIFICATION` before any Planner revision.
- During `AWAITING_HUMAN_CLARIFICATION`, Orchestrator records pending human decision questions and preserves all outstanding `EVIDENCE_RESOLVABLE` findings for later revision.
- Orchestrator resumes Planner revision only after explicit human clarification is captured and passed to Planner as authoritative requirement(s), together with outstanding `EVIDENCE_RESOLVABLE` findings.
- Only the creation of a revised `PLAN` consumes revision budget; waiting/routing/clarification handling does not.

When `CHANGES REQUESTED` depends on missing user/product intent rather than missing repository inspection, the orchestrator must pause and request human clarification before the next Planner revision.

Waiting for human clarification does not consume planner revision budget by itself.

Revision budget accounting remains:

- iteration 1 = initial plan
- iteration 2 = revision 1
- iteration 3 = revision 2

## Failure handling

If a role fails:

1. capture failure evidence
2. record failure in handoff state
3. retry only within configured budget
4. otherwise escalate

Never continue as if a failed phase succeeded.

## Boundaries

Do not:

- mutate product/source files in V1 orchestration
- bypass blocked gates to make progress
- fabricate model/runtime metadata
- claim checks succeeded without evidence

Orchestration is a control layer; it must not become the deliverable.
