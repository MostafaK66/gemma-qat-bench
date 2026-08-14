# Orchestrate a V1/V1.5 Planning or V2.1 Coding Workflow

Use this prompt to coordinate: `<task description>`.

## Required loading

1. `AGENTS.md`
2. `llms.txt`
3. `.context/AGENT-ROLES.md` (authoritative contract)
4. `.github/skills/orchestration/SKILL.md`
5. Relevant source/tests/config/docs and task-specific skills

## Non-negotiable boundaries

- Create one Orchestrator-owned `.context/handoffs/<task-id>.md` from the template. Specialists return artifacts; they never persist handoffs.
- Keep `STATE SNAPSHOT` current on every transition, using `not_started`, `not_applicable`, or `unknown` rather than invented data. It is observability only, not a machine-authoritative V2 state store.
- Preserve V1/V1.5 planning-only behavior: it may end at `PLAN_APPROVED` after Gate 1 and must not implement product code.
- V2.1 encodes the coding protocol but does not create/activate V2.2 Implementer, Verifier, or Reviewer profiles/prompts. If a mandatory V2 specialist is unavailable, fail closed unless the human explicitly authorizes a documented degraded workflow.
- Do not silently substitute Orchestrator judgment for a required specialist judgment.

## INTAKE and routing

Persist the exact `INTAKE` fields from the handoff template. Select `FAST` only for `TRIVIAL_MECHANICAL` when all contract conditions are true: exact request, uniquely determined repository evidence, at most three cohesive files including paired tests/docs, no public API/CLI/config semantics, architecture/ownership, security/data/privacy/operational, or dependency impact, and focused deterministic verification. Route `LOW_RISK`, `STANDARD`, and `HIGH_RISK` to `FULL`; apply heightened clarification/evidence scrutiny to HIGH_RISK.

Immediately escalate FAST to FULL if scope grows; a public/output/config/compatibility/security/data/lifecycle/operational concern emerges; an architecture/ownership/dependency decision appears; `HUMAN_INTENT_REQUIRED` arises; evidence ceases to be unique; verification exposes a non-mechanical regression; or a second independent judgment is required. Preserve current FAST work only as evidence, then run PLAN/Gate 1; it is not automatically approved. FAST/FULL calibration is provisional pending V2.5 evidence.

## Flows

**V1/V1.5 planning-only:**

```text
INTAKE -> PLAN -> PLAN_REVIEW -> Gate 1 -> PLAN_APPROVED | AWAITING_HUMAN_CLARIFICATION | ESCALATE_TO_HUMAN
```

**V2.1 FAST:**

```text
INTAKE -> IMPLEMENTING -> VERIFYING -> Gate 2 -> CHANGE_COMPLETE
```

**V2.1 FULL:**

```text
INTAKE -> PLAN -> PLAN_REVIEW -> Gate 1 -> PLAN_APPROVED
       -> IMPLEMENTING -> VERIFYING -> Gate 2 -> REVIEWING -> Gate 3 -> CHANGE_COMPLETE
```

Gate 1 stays exactly `APPROVED | CHANGES REQUESTED`, with Planner author, Plan Critic judge, and Planner revision budget `2`. Any human-intent blocker pauses before planning revision.

Gate 2 is exactly `PASSED | FAILED`; Verifier alone judges it. A pass requires all concrete plan/intake, acceptance, targeted/regression-test, required-quality-gate, docs/config/help/public-contract, and no-blocker evidence. Record `finding_kind` separately from `resolution_class`; missing/failed/incomplete/unverifiable required command evidence fails Gate 2.

Gate 3 is exactly `APPROVED | CHANGES REQUESTED`; Reviewer independently judges the verified implementation and never fixes findings. FAST records Gate 3 `not_applicable`.

## Verification execution broker

The future production Verifier is read/search-only and receives no `run_in_terminal`, `get_terminal_output`, edit tool, Git mutation, or `run_subagent`. Under current JetBrains evidence, the main Orchestrator may broker exact repository-prescribed commands only through its observable human approval boundary. Capture and transfer exact command, working directory, exit/result, and relevant unmodified raw stdout/stderr (or equivalent). Do not omit, reinterpret, fabricate, or silently skip evidence; do not substitute an Orchestrator Gate 2 verdict.

V2 preserves independent verification judgment, not fully independent verification execution. Do not claim SDK-enforced least privilege equivalence.

## Revisions, human intent, and failure routing

Implementation repairs have a separate shared Gate 2/Gate 3 budget of `2` per approved plan version; initial implementation is `0`. Increment only for delegated repairs that may change implementation files. Do not charge human/environment waits, no-change verification reruns, review-only reruns, or schema-only retries. A material clarification routes `PLAN_INVALIDATED -> AWAITING_HUMAN_CLARIFICATION -> PLAN -> PLAN_REVIEW -> Gate 1`, then resets only the new plan version's implementation counter.

Raise `HUMAN_INTENT_REQUIRED` only for non-unique evidence plus materially consequential alternative public/acceptance/API/CLI/config/architecture/compatibility/security/data/privacy behavior. Consolidate questions. Implementer never silently changes an approved plan.

Every implementation change, including a reviewer-requested repair, routes:

```text
Implementer revision -> Verifier -> Gate 2 -> Reviewer
```

Handle `PROFILE_UNAVAILABLE`, `INVOCATION_FAILED`, `MALFORMED_ARTIFACT`, `AGENT_LOOP_TIMEOUT_OR_LIMIT`, and `TOOL_CAPABILITY_FAILURE` per the authoritative contract: preserve evidence/state, fail closed where mandatory, never infer an approval, allow only one no-product-change schema retry, and do not blindly replay possibly changed implementation.

## Context, artifacts, and final output

Minimize specialist context and require the exact IMPLEMENTATION, VERIFICATION, and IMPLEMENTATION REVIEW fields in the authoritative contract/template. Artifacts must be concise, self-contained, evidence-linked, and explicit about unknown/unrun/failed facts.

At `CHANGE_COMPLETE`, persist usage accounting and `FINAL COMMIT-PREPARATION SUMMARY`. It means workflow completion and human handoff readiness only—not staging, committing, pushing, merging, or deploying. Never invoke version-control preparation automatically; it requires later explicit human intent and independent Git inspection.

Return the final state, selected depth, gate verdicts, handoff path, required evidence actually observed, residual risks, any escalation/wait, and the statement that Git is not authorized by orchestration outcome.
