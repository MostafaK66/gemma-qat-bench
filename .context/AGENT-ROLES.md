# AGENT-ROLES.md - Orchestration Role Contract

This file is the authoritative role, tool, gate, state, classification, and capability-boundary contract for orchestration workflows in this repository. The task-scoped handoff is an observability record; neither this prose nor its `STATE SNAPSHOT` is a machine-authoritative state store. V3 may introduce one.

## Versioned workflow boundary

- **V1/V1.5:** planning-only. They may stop at `PLAN_APPROVED` after Gate 1; no product implementation is activated.
- **V2.1:** defines the production coding protocol conceptually, including FAST/FULL routing and Gates 2/3. It does **not** create or activate V2.2 Implementer, Verifier, or Reviewer custom-agent profiles/prompts.
- V2.1 FULL uses the V1/V1.5 plan and Gate 1 contract unchanged, then may proceed only when the required specialist roles are available under the contract. Mandatory V2 specialist phases fail closed; the Orchestrator never silently substitutes its own execution unless the human explicitly authorizes a documented degraded workflow.

## Execution modes

### `chat-simulation`

- Role separation exists at the workflow level; isolated contexts and per-role model control are not guaranteed.
- This remains the V1 planning fallback.

### `ide-custom-agent`

- V1.5 profiles live under `.github/agents/`. The validated Planner and Plan Critic profiles declare exactly `list_dir`, `read_file`, `file_search`, and `grep_search`; they do not edit, execute commands, mutate Git, delegate, or write handoffs.
- In the validated JetBrains environment the main Copilot Agent/chat delegates through `run_subagent`, receives artifacts, and alone persists the handoff and enforces routing.
- V2.1 extends this mode conceptually but does not activate V2 production profiles. If a future mandatory V2 profile is unavailable, fail closed rather than silently replacing that role.

### `sdk-sub-agent` (future)

- Specialist roles can receive isolated role-specific prompts, tools, skills, models, and reasoning configuration. Parent Orchestrator enforces ordering, budgets, and escalation.

## V2.0 JetBrains capability evidence

- Delegated read/search (`list_dir`, `read_file`, `file_search`, `grep_search`): **validated**.
- Delegated `insert_edit_into_file`: **validated** in a controlled edit probe.
- Delegated `apply_patch`: **not validated; capability insufficient in the probe**.
- Delegated `create_file`: **not yet validated**.
- Delegated `run_in_terminal`: execution capability **validated**.
- Delegated terminal human-approval enforcement: **not observed; insufficient for a production Verifier**.
- Main-Orchestrator terminal human approval: **observed**.

Do not generalize beyond this evidence. V2.1's future production Verifier must be read/search-only and receive neither terminal/get-output, edit, Git-mutation, nor `run_subagent` capability.

## Roles and ownership

| Role | Mandate | Product edits? | Tool boundary | Status |
| --- | --- | --- | --- | --- |
| Orchestrator | Own INTAKE, handoff, sequencing, state snapshot, budgets, evidence transfer, gates/routing, and escalation | No, except handoff persistence | Main read/search and handoff persistence; may broker exact repository-prescribed verification commands through the observable JetBrains approval boundary | active |
| Planner | Author the evidence-based plan | No | read/search-only | active V1/V1.5 |
| Plan Critic | Judge the plan at Gate 1 | No | read/search-only | active V1/V1.5 |
| Implementer | Execute approved plan or FAST intake and return implementation artifact | Yes, future V2.2 profile only | scoped implementation tools, not yet provisioned | contract only |
| Verifier | Independently judge Gate 2 from repository, artifacts, and brokered raw evidence | No | read/search-only only; no terminal, edit, Git mutation, or delegation | contract only |
| Reviewer | Independently judge Gate 3 from verified implementation | No | read/search-only; no terminal required | contract only |

Only the Orchestrator writes `.context/handoffs/<task-id>.md`; specialists return concise structured artifacts and never persist handoffs.

## INTAKE and right-sizing

Orchestrator persists this artifact before routing:

```text
INTAKE

Task:
...

Requested outcome:
...

Constraints and explicit out-of-scope:
...

Public-contract / operational impact:
none | ...

Risk classification:
TRIVIAL_MECHANICAL | LOW_RISK | STANDARD | HIGH_RISK

Selected orchestration depth:
FAST | FULL

Evidence-based rationale:
...

Known ambiguities:
none | ...

Human decisions already supplied:
none | ...

Expected changed-file scope:
...

Escalation triggers:
...
```

`FAST` is eligible only for `TRIVIAL_MECHANICAL` where every relevant condition holds: the outcome is exact; evidence uniquely determines the edit; scope is at most three cohesive files including directly paired tests/docs; there is no public API/CLI/config semantic, architecture/ownership, security/data/privacy/operational, or dependency change; and focused deterministic verification is available. `LOW_RISK`, `STANDARD`, and `HIGH_RISK` initially use `FULL`; `HIGH_RISK` adds heightened clarification/evidence scrutiny. FAST/FULL calibration is provisional pending V2.5 representative single-agent vs multi-agent evidence.

Escalate FAST immediately to FULL when scope grows; public contract/output/config semantics, compatibility/security/data/lifecycle/operational, architecture/ownership/dependency decisions, `HUMAN_INTENT_REQUIRED`, non-unique evidence, non-mechanical verification regression, or a second independent judgment is needed. Preserve FAST work as evidence only, then route `PLAN -> PLAN_REVIEW -> Gate 1` and the normal FULL flow; it is not approved merely because it was already changed.

## States and flows

Supported states: `INTAKE`, `PLAN`, `PLAN_REVIEW`, `AWAITING_HUMAN_CLARIFICATION`, `PLAN_APPROVED`, `IMPLEMENTING`, `VERIFYING`, `REVIEWING`, `PLAN_INVALIDATED`, `AWAITING_ENVIRONMENT_RESOLUTION`, `CHANGE_COMPLETE`, and `ESCALATE_TO_HUMAN`.

The V1/V1.5 planning-only flow remains valid:

```text
INTAKE -> PLAN -> PLAN_REVIEW -> Gate 1 -> PLAN_APPROVED | AWAITING_HUMAN_CLARIFICATION | ESCALATE_TO_HUMAN
```

It stops at `PLAN_APPROVED`.

V2.1 FAST:

```text
INTAKE -> IMPLEMENTING -> VERIFYING -> Gate 2 -> CHANGE_COMPLETE
```

V2.1 FULL:

```text
INTAKE -> PLAN -> PLAN_REVIEW -> Gate 1 -> PLAN_APPROVED
       -> IMPLEMENTING -> VERIFYING -> Gate 2 -> REVIEWING -> Gate 3 -> CHANGE_COMPLETE
```

This prose is not machine-authoritative. The compact handoff `STATE SNAPSHOT` is likewise observability only.

## Gate 1 (preserved)

Verdicts are exactly `APPROVED` and `CHANGES REQUESTED`. Planner is author; Plan Critic is judge. `APPROVED` means the plan is implementation-ready as written, without unresolved decisions that could materially affect public/acceptance/API/CLI/config semantics, architecture/ownership, compatibility, security/data/privacy behavior, or intended product behavior.

Every Plan Critic blocking finding contains `finding_id`, `classification`, `decision_question`, `impact_scope`, `evidence_basis`, and `required_correction`. A `HUMAN_INTENT_REQUIRED` finding additionally contains `why_not_uniquely_resolved`. Do not use a competing Gate 1 blocker schema.

- `EVIDENCE_RESOLVABLE` means the blocker can be resolved uniquely from repository evidence, existing requirements, accepted human decisions, or other already-authoritative task evidence without inventing product intent. It normally routes back to Planner for a bounded plan revision.
- `HUMAN_INTENT_REQUIRED` means repository evidence does not uniquely determine the answer **and** different reasonable answers materially affect consequential behavior or scope. It routes through Orchestrator to `AWAITING_HUMAN_CLARIFICATION`; human waiting by itself does not consume Planner revision budget.

Planner revision budget is `2`: iteration 1 is the initial plan, iteration 2 is Planner revision 1, and iteration 3 is Planner revision 2. Therefore, one planning attempt has at most three Planner/Plan Critic cycles. Human clarification waiting by itself does not consume Planner revision budget. Planner revisions remain separate from implementation revisions. A clarification that materially changes requirements may produce a new plan version as defined below.

## Gate 2 — verification

Verdicts are exactly `PASSED` and `FAILED`; no third verdict. `PASSED` requires concrete, verifiable evidence that the implementation matches its approved plan/FAST intake, applicable acceptance criteria and targeted/regression tests passed, required repository quality gates passed, required docs/config/help/public-contract changes are present, and no blocking finding remains. Missing, unsuccessful, incomplete, or unverifiable required command evidence means `FAILED`.

Gate 2 findings use both `finding_kind` and `resolution_class` without conflation. Allowed finding kinds: `IMPLEMENTATION_DEFECT`, `ACCEPTANCE_EVIDENCE_MISSING`, `QUALITY_GATE_FAILURE`, `ENVIRONMENT_TOOLING_FAILURE`, `PLAN_ASSUMPTION_INVALIDATED`. Resolution classes remain `EVIDENCE_RESOLVABLE` and `HUMAN_INTENT_REQUIRED`. Environment/tooling failure routes to `AWAITING_ENVIRONMENT_RESOLUTION`; it is not product intent.

### Execution broker

The future delegated Verifier independently owns Gate 2 judgment but not command execution. The main Orchestrator brokers only exact repository-prescribed quality commands through its observed human approval boundary, captures exact command, working directory, exit/result, and relevant unmodified raw stdout/stderr (or equivalent), and transfers that evidence to Verifier. It must not reinterpret failures, omit evidence, manufacture output, silently skip commands, or substitute its own Gate 2 verdict. V2 preserves independent verification judgment, **not** fully independent verification execution; this accepted JetBrains limitation is not equivalent to future SDK-enforced least privilege.

## Gate 3 — implementation review

Verdicts are exactly `APPROVED` and `CHANGES REQUESTED`. Reviewer judges the actual verified implementation. `APPROVED` requires scope matching approved intent, sufficient verification evidence, no blocking correctness/safety/compatibility/architecture/test/docs issue, no material unapproved expansion, and recorded non-blocking residual risk. `CHANGES REQUESTED` requires a blocking finding. Review findings may be `IMPLEMENTATION_DEFECT`, `VERIFICATION_EVIDENCE_INSUFFICIENT`, `PLAN_SCOPE_DEVIATION`, `PLAN_ASSUMPTION_INVALIDATED`, or `SECURITY_OR_COMPATIBILITY_RISK`. Reviewer never fixes findings or manufactures churn.

## Revisions, clarification, and failures

The implementation budget is separate from planning: at most `2` implementation revisions per approved plan version (initial implementation is count `0`). It is shared by Gates 2 and 3 and increments only when Orchestrator delegates a repair that may change implementation files. Human/environment waits, verification without product change, review-only reruns, and schema-only retries do not consume it. A materially changed human clarification invalidates the plan, routes `PLAN_INVALIDATED -> AWAITING_HUMAN_CLARIFICATION -> PLAN -> PLAN_REVIEW -> Gate 1`, and resets the implementation counter only for the newly approved plan version while preserving history.

Raise `HUMAN_INTENT_REQUIRED` only when evidence does not uniquely determine the answer **and** reasonable answers materially affect public/acceptance/API/CLI/config semantics, architecture/ownership, compatibility, or security/data/privacy behavior. Consolidate consequential questions. An Implementer cannot silently patch an approved plan.

Every implementation change, including one requested by Reviewer, routes `Implementer revision -> Verifier -> Gate 2 -> Reviewer`; never reviewer-direct approval after a change.

Failure taxonomy: `PROFILE_UNAVAILABLE`, `INVOCATION_FAILED`, `MALFORMED_ARTIFACT`, `AGENT_LOOP_TIMEOUT_OR_LIMIT`, `TOOL_CAPABILITY_FAILURE`. Fail closed for unavailable mandatory profiles/capabilities; preserve state and artifacts on invocation failure; never infer a missing verdict. Permit one schema-only retry only when no product files changed; a second malformed artifact escalates. Preserve partial timeout evidence and do not blindly replay if files may have changed.

## Artifact and context requirements

- **IMPLEMENTATION:** plan version/FAST intake reference; iteration; `COMPLETED | HUMAN_INTENT_REQUIRED | BLOCKED`; steps implemented; changed files/purpose; tests; docs/config; commands actually run (passed/failed/not run); deviations; blockers; residual risks.
- **VERIFICATION:** plan/intake version; implementation iteration; `PASSED | FAILED`; criteria checked; brokered commands/evidence reviewed; findings with both classifications; environment limitations; residual risks. Never call an unexecuted command passed.
- **IMPLEMENTATION REVIEW:** plan version; iteration; `APPROVED | CHANGES REQUESTED`; evidence reviewed; blocking findings; scope; correctness/compatibility/tests/docs assessment; residual risks.

Pass only needed context: Implementer gets the plan/FAST intake, human decisions, relevant repository context, and repair findings; Verifier gets plan/intake, actual scope, implementation artifact, current context, acceptance criteria, and raw brokered evidence; Reviewer gets approved plan, actual scope/diff, implementation and verification artifacts, and relevant source/tests/docs. Artifacts are concise, self-contained, evidence-linked, explicit about unknown/unrun/failed evidence, and free of transcript copying.

## Completion and Git seam

`CHANGE_COMPLETE` means the required coding workflow is complete and ready for human handoff or separately authorized commit preparation. It never authorizes staging, committing, pushing, merging, or deployment. FULL requires Gates 2 and 3; FAST records Gate 3 as `not_applicable` and explicitly completes based on Gate 2.

The completion handoff records `FINAL COMMIT-PREPARATION SUMMARY`: approved plan/FAST intake reference, final changed scope, Gate 2 evidence/verdict, Gate 3 verdict, residual risks, and `Git authorization: No Git mutation is authorized by this orchestration outcome.` A later version-control workflow requires explicit human intent (for example, `Use prepare-commit for task <task-id>`) and independently inspects Git status/diff.

## Model policy

Use conceptual slots (`orchestrator_model`, `planner_model`, `plan_critic_model`, `implementer_model`, `verifier_model`, `reviewer_model`). Model-family diversity is a preference, not a correctness gate; record known configuration and runtime evidence separately and do not fabricate actual model identity or heterogeneous execution.
