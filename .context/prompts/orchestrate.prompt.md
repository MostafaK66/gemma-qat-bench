# Orchestrate a V1/V1.5 Planning or V2.2 Coding Workflow

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
- V2.2 activates production Implementer, Verifier, and Reviewer specialist profiles/prompts. If a mandatory specialist is unavailable, fail closed unless the human explicitly authorizes a documented degraded workflow.
- In `ide-custom-agent` mode, delegate every required specialist phase through `run_subagent`; do not allow nested specialist delegation.
- Do not silently substitute Orchestrator judgment for a required specialist judgment.

## INTAKE and routing

Persist the exact `INTAKE` fields from the handoff template. Select `FAST` only for `TRIVIAL_MECHANICAL` when all contract conditions are true: exact request, uniquely determined repository evidence, at most three cohesive files including paired tests/docs, no public API/CLI/config semantics, architecture/ownership, security/data/privacy/operational, or dependency impact, and focused deterministic verification. Route `LOW_RISK`, `STANDARD`, and `HIGH_RISK` to `FULL`; apply heightened clarification/evidence scrutiny to HIGH_RISK.

Immediately escalate FAST to FULL if scope grows; a public/output/config/compatibility/security/data/lifecycle/operational concern emerges; an architecture/ownership/dependency decision appears; `HUMAN_INTENT_REQUIRED` arises; evidence ceases to be unique; verification exposes a non-mechanical regression; or a second independent judgment is required. Preserve current FAST work only as evidence, then run PLAN/Gate 1; it is not automatically approved. FAST/FULL calibration is provisional pending V2.5 evidence.

## Flows

**V1/V1.5 planning-only:**

```text
INTAKE -> PLAN -> PLAN_REVIEW -> Gate 1 -> PLAN_APPROVED | AWAITING_HUMAN_CLARIFICATION | ESCALATE_TO_HUMAN
```

**V2.2 FAST:**

```text
INTAKE -> Implementer -> verification-command broker (Orchestrator) -> Verifier -> Gate 2 -> CHANGE_COMPLETE
```

**V2.2 FULL:**

```text
INTAKE -> Planner -> Plan Critic -> Gate 1 -> PLAN_APPROVED
       -> Implementer -> verification-command broker (Orchestrator) -> Verifier -> Gate 2 -> Reviewer -> Gate 3 -> CHANGE_COMPLETE
```

Gate 1 stays exactly `APPROVED | CHANGES REQUESTED`, with Planner author, Plan Critic judge, and Planner revision budget `2`. Any human-intent blocker pauses before planning revision.

Gate 2 is exactly `PASSED | FAILED`; Verifier alone judges it. A pass requires all concrete plan/intake, acceptance, targeted/regression-test, required-quality-gate, docs/config/help/public-contract, and no-blocker evidence. Record `finding_kind` separately from `resolution_class`; missing/failed/incomplete/unverifiable required command evidence fails Gate 2.

Gate 3 is exactly `APPROVED | CHANGES REQUESTED`; Reviewer independently judges the verified implementation and never fixes findings. FAST records Gate 3 `not_applicable`.

## Verification execution broker

The production Verifier is read/search-only and receives no `run_in_terminal`, `get_terminal_output`, edit tool, Git mutation, or `run_subagent`. Under current JetBrains evidence, the main Orchestrator may broker exact repository-prescribed commands only through its observable human approval boundary.

Use the canonical V2 evidence labels exactly: `required_command_set_source`, `exact_executed_command`, `execution_result`, `output_handling`, and `permitted_evidence_material`.

Maintain one Orchestrator-owned task-scoped local/gitignored ledger per verification attempt, bound to task ID, plan version/FAST intake reference, implementation iteration, verification iteration, and `required_command_set_source`. Each stable `CMD-001` record includes `command_id`, character-for-character `exact_executed_command`, working directory, `execution_result`, exit code, required flag, `output_handling`, `permitted_evidence_material`, and `required_command_rationale_or_source`. A new implementation iteration requires a new ledger; prior implementation evidence cannot satisfy the new Gate 2 attempt.

Before delegating Verifier, structurally validate ledger completeness and exact current bindings including `required_command_set_source`.

After Verifier returns, validate artifact/reference integrity only: every required `command_id` appears exactly once; no missing/duplicate/unknown/stale IDs; all required assessment fields exist (`command_id`, `evidence_quality`, `evidence_assessment`, `rationale`); and no canonical evidence recreation/overwrite appears. Do not determine evidence sufficiency or Gate 2 verdict.

Allow one schema-only retry only when no product files changed; second malformed artifact escalates. Never infer verdicts, reconstruct evidence, or blindly rerun verification after possibly changed implementation.

Sensitive policy: do not persist full stdout/stderr by default. Persist only minimal exact character-preserving non-sensitive excerpts or supplied protected references. For suspected-sensitive output, never persist raw sensitive content in prompts/artifacts; record `output_handling: WITHHELD_SENSITIVE` plus a non-sensitive reason. Do not use free-form LLM redaction as authoritative raw evidence, and never invent opaque references. If a command embeds secrets, require a safe equivalent or human resolution. Withholding alone is not a Gate 2 verdict, but insufficient remaining permitted evidence cannot support `PASSED`.

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

Minimize specialist context and require the exact IMPLEMENTATION, VERIFICATION, and IMPLEMENTATION REVIEW fields in the authoritative contract/template. For Verifier, pass task-scoped read-only review context containing relevant current canonical records plus permitted evidence material (not only IDs). Verifier must inspect but neither own nor persist/modify/execute/reconstruct the ledger. Verifier artifacts must not reproduce authoritative `exact_executed_command`, working directories, `execution_result`, raw output, `output_handling`, `permitted_evidence_material`, or protected references.

At `CHANGE_COMPLETE`, persist usage accounting and `FINAL COMMIT-PREPARATION SUMMARY`. It means workflow completion and human handoff readiness only—not staging, committing, pushing, merging, or deploying. Never invoke version-control preparation automatically; it requires later explicit human intent and independent Git inspection.

Return the final state, selected depth, gate verdicts, handoff path, required evidence actually observed, residual risks, any escalation/wait, and the statement that Git is not authorized by orchestration outcome.
