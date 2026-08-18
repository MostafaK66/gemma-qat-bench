# AGENT-ROLES.md - Orchestration Role Contract

This file is the authoritative role, tool, gate, state, classification, and capability-boundary contract for orchestration workflows in this repository. The task-scoped handoff is an observability record; neither this prose nor its `STATE SNAPSHOT` is a machine-authoritative state store. V3 may introduce one.

## Versioned workflow boundary

- **V1/V1.5:** planning-only. They may stop at `PLAN_APPROVED` after Gate 1; no product implementation is activated.
- **V2.1:** defines the coding protocol contract (INTAKE, FAST/FULL, Gates 2/3, budgets, brokered verification evidence, and failure routing).
- **V2.2:** activates production `ide-custom-agent` specialist profiles/prompts for Implementer, Verifier, and Reviewer under least-privilege boundaries.
- V2 FULL uses the V1/V1.5 plan and Gate 1 contract unchanged, then proceeds through mandatory specialist phases. Mandatory phases fail closed; the Orchestrator never silently substitutes its own specialist judgment unless the human explicitly authorizes a documented degraded workflow.

## Execution modes

### `chat-simulation`

- Role separation exists at the workflow level; isolated contexts and per-role model control are not guaranteed.
- This remains the V1 planning fallback.

### `ide-custom-agent`

- Active profiles live under `.github/agents/`: Planner, Plan Critic, Implementer, Verifier, and Reviewer.
- Planner and Plan Critic declare exactly `list_dir`, `read_file`, `file_search`, and `grep_search`; they do not edit, execute commands, mutate Git, delegate, or write handoffs.
- Implementer declares only `list_dir`, `read_file`, `file_search`, `grep_search`, `insert_edit_into_file`, and `create_file`.
- Verifier and Reviewer are read/search-only and declare exactly `list_dir`, `read_file`, `file_search`, and `grep_search`.
- In the validated JetBrains environment the main Copilot Agent/chat delegates through `run_subagent`, receives artifacts, and alone persists the handoff and enforces routing.
- In `ide-custom-agent` mode, the Orchestrator delegates required specialist phases through `run_subagent`. Specialists do not delegate other specialists.

### `sdk-sub-agent` (future)

- Specialist roles can receive isolated role-specific prompts, tools, skills, models, and reasoning configuration. Parent Orchestrator enforces ordering, budgets, and escalation.

## V2.0 JetBrains capability evidence

- Delegated read/search (`list_dir`, `read_file`, `file_search`, `grep_search`): **validated**.
- Delegated `insert_edit_into_file`: **validated** in a controlled edit probe.
- Delegated `apply_patch`: **not validated; capability insufficient in the probe**.
- Delegated `create_file`: **validated** in a controlled probe.
- Delegated `run_in_terminal`: execution capability **validated**.
- Delegated terminal human-approval enforcement: **not observed; insufficient for a production Verifier**.
- Main-Orchestrator terminal human approval: **observed**.

Do not generalize beyond this evidence. The production Verifier must be read/search-only and receive neither terminal/get-output, edit, Git-mutation, nor `run_subagent` capability.

## Roles and ownership

| Role | Mandate | Product edits? | Tool boundary | Status |
| --- | --- | --- | --- | --- |
| Orchestrator | Own INTAKE, handoff, sequencing, state snapshot, budgets, evidence transfer, gates/routing, and escalation | No, except handoff persistence | Main read/search and handoff persistence; may broker exact repository-prescribed verification commands through the observable JetBrains approval boundary | active |
| Planner | Author the evidence-based plan | No | read/search-only | active V1/V1.5 |
| Plan Critic | Judge the plan at Gate 1 | No | read/search-only | active V1/V1.5 |
| Implementer | Execute approved FULL plan or authorized FAST intake and return implementation artifact | Yes, within approved scope only | `list_dir`, `read_file`, `file_search`, `grep_search`, `insert_edit_into_file`, `create_file`; no terminal, `apply_patch`, delegation, or Git mutation | active V2.2 |
| Verifier | Independently judge Gate 2 from repository, artifacts, and brokered raw evidence | No | read/search-only; no terminal, edit, delegation, or Git mutation | active V2.2 |
| Reviewer | Independently judge Gate 3 from verified implementation | No | read/search-only; no terminal, edit, delegation, or Git mutation | active V2.2 |

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

Active V2 FAST:

```text
INTAKE -> Implementer -> verification-command broker (Orchestrator) -> Verifier -> Gate 2 -> CHANGE_COMPLETE
```

Active V2 FULL:

```text
INTAKE -> Planner -> Plan Critic -> Gate 1 -> PLAN_APPROVED
       -> Implementer -> verification-command broker (Orchestrator) -> Verifier -> Gate 2 -> Reviewer -> Gate 3 -> CHANGE_COMPLETE
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

### Canonical verification evidence ledger (V2)

The Orchestrator owns a task-scoped local/gitignored canonical verification evidence ledger. It is not a machine-authoritative V2 state machine; it is attempt-scoped observability/persistence only. Canonical labels are exactly: `required_command_set_source`, `exact_executed_command`, `execution_result`, `output_handling`, and `permitted_evidence_material`.

- One ledger exists per verification attempt and is bound to: task ID, plan version/FAST intake reference, implementation iteration, verification iteration, and `required_command_set_source`.
- A new implementation iteration requires a new ledger; no prior implementation evidence may satisfy a new Gate 2 attempt.
- Each stable `CMD-001`-style record includes: `command_id`; `exact_executed_command` (character-for-character); `working_directory`; `execution_result`; `exit_code`; `required`; `output_handling`; `permitted_evidence_material`; `required_command_rationale_or_source`.

### Execution broker

The delegated Verifier independently owns Gate 2 judgment but not command execution. The main Orchestrator brokers only exact repository-prescribed quality commands through its observed human approval boundary, captures canonical ledger evidence (`exact_executed_command`, working directory, `execution_result`, exit/result metadata, and permitted material per `output_handling`), and transfers that evidence to Verifier. It must not reinterpret failures, omit evidence, manufacture output, silently skip commands, or substitute its own Gate 2 verdict.

Before Verifier delegation, Orchestrator must structurally validate current-ledger completeness and exact binding integrity (task/plan-or-intake/implementation/verification plus `required_command_set_source`).

After Verifier returns, Orchestrator validates artifact/reference integrity only: every required `command_id` appears exactly once; no missing/duplicate/unknown/stale IDs; all four assessment fields are present (`command_id`, `evidence_quality`, `evidence_assessment`, `rationale`); and no canonical evidence recreation/overwrite appears. Compliant qualitative interpretation in `evidence_assessment`/`rationale` (for example, what evidence supports or fails to establish, or why evidence is sufficient/insufficient) is allowed and is not malformed. Orchestrator MUST reject actual duplication or reconstruction of authoritative canonical field values and any competing ledger. Orchestrator remains structural-only and does not judge interpretation correctness, evidence sufficiency, or Gate 2 verdict.

Permit one schema-only retry only when no product files changed. A second malformed artifact escalates. Never infer verdicts, reconstruct evidence, or blindly rerun after possibly changed implementation.

### Sensitive output handling

No full stdout/stderr is persisted by default. Persist only minimal exact character-preserving non-sensitive excerpts when needed, or protected references provided by tooling/humans. If output is suspected sensitive, never persist raw sensitive content in framework artifacts/prompts; set `output_handling: WITHHELD_SENSITIVE` with a non-sensitive reason. Do not present free-form LLM redaction as unmodified evidence. Do not invent opaque references. Commands embedding secrets require a safe equivalent or human resolution. Withholding alone is not a verdict, but insufficient remaining permitted evidence cannot support `PASSED`.

V2 boundary: this contract remains prose-only. Do not add typed Python schemas, machine-authoritative state machines, or SDK-enforced authority in V2.

## Gate 3 — implementation review

Verdicts are exactly `APPROVED` and `CHANGES REQUESTED`. Reviewer judges the actual verified implementation. `APPROVED` requires scope matching approved intent, sufficient verification evidence, no blocking correctness/safety/compatibility/architecture/test/docs issue, no material unapproved expansion, and recorded non-blocking residual risk. `CHANGES REQUESTED` requires a blocking finding. Review findings may be `IMPLEMENTATION_DEFECT`, `VERIFICATION_EVIDENCE_INSUFFICIENT`, `PLAN_SCOPE_DEVIATION`, `PLAN_ASSUMPTION_INVALIDATED`, or `SECURITY_OR_COMPATIBILITY_RISK`. Reviewer never fixes findings or manufactures churn.

## Revisions, clarification, and failures

The implementation budget is separate from planning: at most `2` implementation revisions per approved plan version (initial implementation is count `0`). It is shared by Gates 2 and 3 and increments only when Orchestrator delegates a repair that may change implementation files. Human/environment waits, verification without product change, review-only reruns, and schema-only retries do not consume it. A materially changed human clarification invalidates the plan, routes `PLAN_INVALIDATED -> AWAITING_HUMAN_CLARIFICATION -> PLAN -> PLAN_REVIEW -> Gate 1`, and resets the implementation counter only for the newly approved plan version while preserving history.

Raise `HUMAN_INTENT_REQUIRED` only when evidence does not uniquely determine the answer **and** reasonable answers materially affect public/acceptance/API/CLI/config semantics, architecture/ownership, compatibility, or security/data/privacy behavior. Consolidate consequential questions. An Implementer cannot silently patch an approved plan.

Every implementation change, including one requested by Reviewer, routes `Implementer revision -> Verifier -> Gate 2 -> Reviewer`; never reviewer-direct approval after a change.

Failure taxonomy: `PROFILE_UNAVAILABLE`, `INVOCATION_FAILED`, `MALFORMED_ARTIFACT`, `AGENT_LOOP_TIMEOUT_OR_LIMIT`, `TOOL_CAPABILITY_FAILURE`. Fail closed for unavailable mandatory profiles/capabilities; preserve state and artifacts on invocation failure; never infer a missing verdict. Permit one schema-only retry only when no product files changed; a second malformed artifact escalates. Preserve partial timeout evidence and do not blindly replay if files may have changed.

## Artifact and context requirements

- **IMPLEMENTATION:** plan version/FAST intake reference; iteration; `COMPLETED | HUMAN_INTENT_REQUIRED | BLOCKED`; steps implemented; changed files/purpose; tests; docs/config; commands actually run (passed/failed/not run); deviations; blockers; residual risks.
- **VERIFICATION:** task ID; plan/intake version; implementation iteration; verification iteration; `PASSED | FAILED`; criteria checked; **Required command evidence assessments** (every required `command_id` exactly once with only `command_id`, `evidence_quality: sufficient | insufficient`, `evidence_assessment`, `rationale`); findings with both classifications; environment limitations; residual risks. Verifier output may qualitatively interpret reviewed canonical evidence only through `evidence_assessment` and `rationale` while referring to `command_id`. This interpretation is non-authoritative and must not restate, reconstruct, or create a competing authoritative representation of canonical field values, including exact commands, working directories, execution results, exit-code values, raw/minimal output excerpts, `output_handling`, `permitted_evidence_material`, protected references, missing canonical values, or another ledger.
- **IMPLEMENTATION REVIEW:** plan version; iteration; `APPROVED | CHANGES REQUESTED`; evidence reviewed; blocking findings; scope; correctness/compatibility/tests/docs assessment; residual risks.

Pass only needed context: Implementer gets the plan/FAST intake, human decisions, relevant repository context, and repair findings; Verifier gets plan/intake, actual scope, implementation artifact, current context, acceptance criteria, and task-scoped read-only review context containing relevant current canonical records plus permitted evidence material (not only IDs); Reviewer gets approved plan, actual scope/diff, implementation and verification artifacts, and relevant source/tests/docs. Artifacts are concise, self-contained, evidence-linked, explicit about unknown/unrun/failed evidence, and free of transcript copying.

## Completion and Git seam

`CHANGE_COMPLETE` means the required coding workflow is complete and ready for human handoff or separately authorized commit preparation. It never authorizes staging, committing, pushing, merging, or deployment. FULL requires Gates 2 and 3; FAST records Gate 3 as `not_applicable` and explicitly completes based on Gate 2.

The completion handoff records `FINAL COMMIT-PREPARATION SUMMARY`: approved plan/FAST intake reference, final changed scope, Gate 2 evidence/verdict, Gate 3 verdict, residual risks, and `Git authorization: No Git mutation is authorized by this orchestration outcome.` A later version-control workflow requires explicit human intent (for example, `Use prepare-commit for task <task-id>`) and independently inspects Git status/diff.

## Model policy

Use conceptual slots (`orchestrator_model`, `planner_model`, `plan_critic_model`, `implementer_model`, `verifier_model`, `reviewer_model`). Record configured and runtime evidence separately.

Configured model map:

- Planner: `Claude Opus 4.6 (copilot)`
- Plan Critic: `GPT-5.6 Terra (copilot)`
- Implementer: `GPT-5.3-Codex (copilot)`
- Verifier: `Claude Sonnet 5 (copilot)`
- Reviewer: `Claude Opus 4.6 (copilot)`

Model evidence boundaries:

- `configured_model`: known from profile configuration.
- `actual_model`: `unknown` unless runtime/UI evidence exposes it.
- `configured_model_family_diversity`: yes for Implementer vs Verifier and Implementer vs Reviewer.
- `heterogeneous_execution_verified`: `unknown` unless runtime evidence proves heterogeneous execution.
