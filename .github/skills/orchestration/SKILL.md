---
name: orchestration
description: Coordinate V1/V1.5 planning-only and V2.1 FAST/FULL multi-role workflows through structured handoffs, evidence gates, bounded revisions, and explicit escalation.
---

# Orchestration

Use this skill for workflows where role separation, evidence, and review quality matter. It composes repository skills and prompts; it does not replace them. The authoritative roles/states/gates/classifications/capability-boundaries contract is `.context/AGENT-ROLES.md`; the Orchestrator persists a task-scoped observability artifact at `.context/handoffs/<task-id>.md` from `.context/handoff-TEMPLATE.md`, not a machine-authoritative state store.

## Load and inspect

1. Read `AGENTS.md`, `llms.txt`, `.context/AGENT-ROLES.md`, and this skill.
2. Inspect relevant source, tests, configuration, CI, documentation, and applicable skills.
3. Create one Orchestrator-owned task handoff from the template; do not create role-specific handoffs or overwrite local world state.
4. Record only runtime/model/capability facts evidenced by the environment.

## Select workflow

Create and persist the exact `INTAKE` artifact before any specialist work. Classify risk and choose depth according to the authoritative FAST eligibility rule:

- `TRIVIAL_MECHANICAL` may use `FAST` only when every exactness, unique-evidence, <=3 cohesive-file, no-semantic/architecture/security/dependency-impact, and focused-deterministic-verification condition holds.
- `LOW_RISK`, `STANDARD`, and `HIGH_RISK` use `FULL` initially; HIGH_RISK receives heightened ambiguity/evidence scrutiny.
- FAST is provisional pending V2.5 calibration evidence. Do not widen it in V2.1.

If any FAST escalation trigger appears, preserve implementation/evidence only, route into `PLAN -> PLAN_REVIEW -> Gate 1`, and continue FULL. Do not treat prior FAST edits as approved.

## V1/V1.5 planning-only (preserved)

V1/V1.5 remains:

```text
INTAKE -> PLAN -> PLAN_REVIEW -> Gate 1 -> PLAN_APPROVED | AWAITING_HUMAN_CLARIFICATION | ESCALATE_TO_HUMAN
```

It stops at `PLAN_APPROVED`. Gate 1 verdicts are exactly `APPROVED` and `CHANGES REQUESTED`; Planner authors and Plan Critic judges; maximum Planner revisions is `2`. Preserve the existing blocker classification and human-clarification routing. Do not implement product code in a planning-only invocation.

`chat-simulation`, `ide-custom-agent`, and future `sdk-sub-agent` are retained. V1.5's validated JetBrains mechanism is `run_subagent`; Planner/Critic use only `list_dir`, `read_file`, `file_search`, and `grep_search`. If their discovery/delegation is unavailable, record chat-simulation fallback as before; do not fabricate independence evidence.

## V2.1 coding procedure

V2.1 encodes, but does not yet activate, V2.2 production Implementer/Verifier/Reviewer profiles or prompts. Mandatory V2 specialist phases fail closed if their profile/capability is unavailable unless the human explicitly authorizes a documented degraded workflow.

### FAST

```text
INTAKE -> IMPLEMENTING -> VERIFYING -> Gate 2 -> CHANGE_COMPLETE
```

Verification is mandatory. Gate 1 and Gate 3 are `not_applicable` unless the task escalates to FULL.

### FULL

```text
INTAKE -> PLAN -> PLAN_REVIEW -> Gate 1 -> PLAN_APPROVED
       -> IMPLEMENTING -> VERIFYING -> Gate 2 -> REVIEWING -> Gate 3 -> CHANGE_COMPLETE
```

Update the handoff `STATE SNAPSHOT` after every transition. It is observability only, not machine-authoritative; V3 may introduce that authority.

### Context minimization

Do not pass chat transcripts by default. Give Implementer only current plan/FAST intake, human decisions, relevant repository context, and repair findings. Give Verifier plan/intake, actual scope, implementation artifact, criteria, context, and raw brokered evidence. Give Reviewer the approved plan, actual scope/diff, implementation and verification artifacts, and relevant source/tests/docs. Require concise, self-contained, evidence-linked artifacts that identify unknown/unrun/failed evidence.

### Gate 2

Verifier owns the exact `PASSED | FAILED` verdict, not the Orchestrator. A pass requires the complete concrete evidence described in `.context/AGENT-ROLES.md`; absent, unsuccessful, incomplete, or unverifiable required command evidence is `FAILED`. Record finding kind separately from `EVIDENCE_RESOLVABLE | HUMAN_INTENT_REQUIRED`; route environment/tooling failures to `AWAITING_ENVIRONMENT_RESOLUTION` rather than treating them as intent.

The Verifier is production read/search-only: no terminal/get-output, edit tools, Git mutation, or delegation. The main Orchestrator may broker only exact repository-prescribed verification commands through its observable JetBrains approval boundary, then forwards command, working directory, exit/result, and relevant unmodified raw stdout/stderr (or equivalent) to Verifier. Never reinterpret output, omit evidence, silently skip a required command, manufacture output, or substitute an Orchestrator verdict. This preserves independent verification **judgment**, not fully independent verification **execution**, an accepted JetBrains V2 limitation.

### Gate 3 and repair ordering

Reviewer owns the exact `APPROVED | CHANGES REQUESTED` Gate 3 judgment and never fixes findings. It evaluates the actual verified implementation and the required scope/correctness/compatibility/test/docs/evidence criteria. If it requests an implementation change, route:

```text
Orchestrator -> Implementer revision -> Verifier -> Gate 2 -> Reviewer
```

Every implementation change re-verifies; no documentation/mechanical exception exists in V2.1.

### Budgets, human intent, and failures

Keep Planner and implementation budgets separate. The implementation budget is `2` repairs per approved plan version, shared across Gate 2 and Gate 3; initial implementation is count `0`. Increment only for a delegated repair that may change implementation files. Do not charge waits, verification-only/review-only reruns, or schema-only retries. A material human clarification invalidates the plan, obtains clarification, repeats PLAN/Gate 1, and resets the implementation count only for the new approved plan version.

Raise `HUMAN_INTENT_REQUIRED` only for non-unique evidence plus materially consequential alternative behavior/scope. Consolidate questions and never let Implementer patch an approved plan silently.

For `PROFILE_UNAVAILABLE`, `INVOCATION_FAILED`, `MALFORMED_ARTIFACT`, `AGENT_LOOP_TIMEOUT_OR_LIMIT`, and `TOOL_CAPABILITY_FAILURE`, preserve state/evidence, never infer missing verdicts, and fail closed where mandatory. Allow at most one schema-only retry when no product file changed; second malformed output escalates. Never blindly replay a timed-out phase when implementation files may have changed.

## Completion and handoff

At `CHANGE_COMPLETE`, record the template's final commit-preparation summary and usage accounting. FULL completion requires Gates 2 and 3; FAST records Gate 3 `not_applicable` and clearly says completion is based on Gate 2. `CHANGE_COMPLETE` authorizes no Git operation. A later version-control workflow requires explicit human intent and independently checks Git state.

## Capability and model boundaries

Use the V2.0 capability evidence in `.context/AGENT-ROLES.md` exactly: delegated read/search and `insert_edit_into_file` validated; delegated `apply_patch` not validated/capability insufficient; `create_file` not yet validated; delegated terminal execution validated but its approval enforcement was not observed and is insufficient for production Verifier; main-Orchestrator terminal approval was observed. Model-family diversity is independent from correctness and must be recorded only when evidenced.

Do not bypass gates, fabricate runtime/model/command evidence, give a production Verifier delegated terminal access, activate V2.2 profiles/prompts early, or mutate source during V1 planning-only work.
