# Orchestration Handoff - <task title>

Task ID:
Created:
Requested execution mode: `chat-simulation` | `ide-custom-agent` | `sdk-sub-agent`
Actual execution mode: `chat-simulation` | `ide-custom-agent` | `sdk-sub-agent`
Source branch/context:

> This is an Orchestrator-owned, task-scoped observability artifact at `.context/handoffs/<task-id>.md`. It is not a machine-authoritative state store; do not invent unknown values. Specialists do not write it.

## INTAKE

```text
INTAKE

Task:

Requested outcome:

Constraints and explicit out-of-scope:

Public-contract / operational impact:
none | ...

Risk classification:
TRIVIAL_MECHANICAL | LOW_RISK | STANDARD | HIGH_RISK

Selected orchestration depth:
FAST | FULL

Evidence-based rationale:

Known ambiguities:
none | ...

Human decisions already supplied:
none | ...

Expected changed-file scope:

Escalation triggers:
```

## STATE SNAPSHOT

> Update on every transition. This compact block is an observability aid only, not a machine-authoritative state store; V3 may replace it.

```text
current_state:
selected_orchestration_depth:
plan_version:
planner_revisions_used:
implementation_revisions_used:
gate_1_verdict:
gate_2_verdict:
gate_3_verdict:
waiting_reason:
last_transition:
```

Use explicit values such as `not_started`, `not_applicable`, and `unknown` rather than inventing data.

## Execution / model / delegation evidence

Record known metadata only; do not infer runtime details.

| Role | Profile (if used) | `configured_model` | `actual_model` (runtime/UI only) | `model_family` (runtime/UI only) | Tool/capability evidence |
| --- | --- | --- | --- | --- | --- |
| Orchestrator |  | `orchestrator_model` |  |  |  |
| Planner |  | `planner_model` |  |  |  |
| Plan Critic |  | `plan_critic_model` |  |  |  |
| Implementer | not activated in V2.1 | `implementer_model` | unknown | unknown |  |
| Verifier | not activated in V2.1 | `verifier_model` | unknown | unknown | read/search-only; no terminal/edit/Git/delegation |
| Reviewer | not activated in V2.1 | `reviewer_model` | unknown | unknown | read/search-only; no terminal required |

- `delegation_verified`:
- `configured_model_family_diversity`:
- `heterogeneous_execution_verified`:
- `fallback_used`:
- `fallback_reason`:
- V2.0 capability limitations / requested vs available:

## Context and artifacts

- Key repository evidence reviewed:
- Applicable instructions/skills:
- Explicit human decisions:
- Acceptance criteria:
- Actual changed-file scope:

Keep passed artifacts concise, self-contained, evidence-linked, and explicit about unknown/unrun/failed evidence. Do not copy whole chat transcripts.

## Plan versions and Gate 1 history

V1/V1.5 planning-only remains valid and may end at `PLAN_APPROVED`. Gate 1 verdicts are exactly `APPROVED` or `CHANGES REQUESTED`.

Planner accounting per planning attempt: iteration 1 = initial plan; iteration 2 = revision 1; iteration 3 = revision 2. The maximum is two Planner revisions and three Planner/Plan Critic cycles. Only a revised plan consumes the Planner revision budget; human clarification waiting by itself does not. Keep Planner revisions separate from implementation revisions. A materially changed clarification may require a new plan version while preserving history.

### Plan version <n>

```text
PLAN

Goal:

Current behavior / evidence:

Owning responsibility:

Files expected to change:

Implementation steps:
1.

Tests / acceptance criteria:

Risks / unknowns:

Out of scope:

Open questions:
```

### Gate 1 / plan review for version <n>

```text
PLAN REVIEW

Verdict:
APPROVED | CHANGES REQUESTED

Blocking findings:
- finding_id:
  classification: EVIDENCE_RESOLVABLE | HUMAN_INTENT_REQUIRED
  decision_question:
  impact_scope:
  evidence_basis:
  required_correction:
  why_not_uniquely_resolved: (required when classification is HUMAN_INTENT_REQUIRED)

Suggestions:

Evidence checked:

Residual risks:
```

| Plan version | Planner iteration / revision | Gate 1 verdict | Finding IDs / classifications | Resulting state |
| --- | --- | --- | --- | --- |
|  | iteration 1 / initial plan |  |  |  |
|  | iteration 2 / revision 1 |  |  |  |
|  | iteration 3 / revision 2 |  |  |  |

## Post-plan clarification / invalidation

- State: `PLAN_INVALIDATED` | `AWAITING_HUMAN_CLARIFICATION` | `not_applicable`
- Triggering specialist/finding:
- Consolidated consequential decision question(s):
- Why evidence is not uniquely resolving:
- Human clarification status / response:
- New plan version required:
- Budget effects: human waiting consumes neither planner nor implementation revision budget.

## Implementation iterations

Implementation revision budget per approved plan version: `2`. Initial implementation is revision count `0`; a repair that may change implementation files increments the shared Gate 2/Gate 3 counter. Verification-only, review-only, schema-only, and human/environment waits do not.

### Implementation iteration <n>

```text
IMPLEMENTATION

Plan version / FAST intake reference:

Implementation iteration:

Disposition:
COMPLETED | HUMAN_INTENT_REQUIRED | BLOCKED

Plan/intake steps implemented:

Files changed + purpose:

Tests added/updated:

Docs/config changes:

Commands actually run:
passed | failed | not run

Deviations from approved plan/intake:

Open blockers:

Residual risks:
```

## Brokered execution evidence

The Orchestrator may broker only exact repository-prescribed commands through its observable JetBrains approval boundary. Preserve canonical evidence and never reinterpret failures or claim unexecuted commands passed.

This ledger is Orchestrator-owned, task-scoped local/gitignored observability/persistence for the current verification attempt. It is not a machine-authoritative V2 state store. Canonical labels are exactly `required_command_set_source`, `exact_executed_command`, `execution_result`, `output_handling`, and `permitted_evidence_material`.

### Verification attempt binding

```text
task_id:
plan_version_or_fast_intake_reference:
implementation_iteration:
verification_iteration:
required_command_set_source:
implementation_fingerprint_algorithm:
implementation_fingerprint:
implementation_fingerprint_scope:
implementation_fingerprint_captured_at:
```

### Fingerprint/check observability

```text
stale_evidence_invalidation_history:
- affected_attempt_or_artifact:
  bound_fingerprint:
  observed_fingerprint:
  detected_at:
  action_taken:

fingerprint_check_events:
- event: post-implementation-scope-pre-commands
  check_time:
  fingerprint_value:
  result: match | mismatch | not_run
  stale_invalidation_applied:
- event: post-commands-pre-verifier
  check_time:
  fingerprint_value:
  result: match | mismatch | not_run
  stale_invalidation_applied:
- event: pre-schema-repair
  check_time:
  fingerprint_value:
  result: match | mismatch | not_run
  stale_invalidation_applied:
- event: post-verifier-pre-gate-2-acceptance
  check_time:
  fingerprint_value:
  result: match | mismatch | not_run
  stale_invalidation_applied:
- event: pre-reviewer
  check_time:
  fingerprint_value:
  result: match | mismatch | not_run
  stale_invalidation_applied:
- event: post-reviewer-pre-gate-3-acceptance
  check_time:
  fingerprint_value:
  result: match | mismatch | not_run
  stale_invalidation_applied:
```

### Canonical command ledger records

| command_id | exact_executed_command (char-for-char) | working_directory | execution_result | exit_code | required | output_handling | permitted_evidence_material | required_command_rationale_or_source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CMD-001 |  |  |  |  |  |  |  |  |

Sensitive policy: no full stdout/stderr by default; persist only minimal exact character-preserving non-sensitive excerpts or supplied protected references. Suspected-sensitive output must use `output_handling: WITHHELD_SENSITIVE` with a non-sensitive reason and must not persist sensitive content. All V2 sensitive-output requirements in `.context/AGENT-ROLES.md` apply, including: no free-form LLM redaction presented as unmodified evidence; opaque references only when actually supplied (no invention); commands embedding secrets require a safe equivalent or human resolution; withholding alone is not a verdict, but insufficient remaining permitted evidence cannot support `PASSED`.

## Gate 2 history — verification

Gate 2 verdicts are exactly `PASSED` or `FAILED`. Verifier owns the judgment, not the execution broker. `finding_kind` and `resolution_class` are separate.

### Verification iteration <n>

```text
VERIFICATION

Task ID:

Plan/intake version:

Implementation iteration:

Verification iteration:

Verdict:
PASSED | FAILED

Acceptance criteria checked:

Required command evidence assessments:
- command_id:
  evidence_quality:
    sufficient | insufficient
  evidence_assessment:
  rationale:

Findings (finding_kind + resolution_class):

Environment limitations:

Residual risks:
```

Verifier artifact constraint: response begins with exactly one plain `VERIFICATION` artifact and contains no preamble, epilogue, Markdown fence, outside text, or second root artifact. Include every required `command_id` exactly once in `Required command evidence assessments`. Include only `command_id`, `evidence_quality`, `evidence_assessment`, and `rationale`; `evidence_quality` is exactly `sufficient` or `insufficient`. Do not reproduce canonical evidence fields (`required_command_set_source`, `exact_executed_command`, `execution_result`, `output_handling`, `permitted_evidence_material`) or protected references. Qualitative interpretation is allowed only in `evidence_assessment`/`rationale` tied to `command_id` (for example, support/failure-to-establish, completeness/absence, sufficiency/insufficiency explanations) and remains non-authoritative; do not duplicate/reconstruct canonical values (including working directories, exit codes, raw/minimal output excerpts, missing canonical values) or create a competing ledger.

### Verifier malformed artifact classification and repair tracking

```text
malformed_artifact_defects:
- OUTSIDE_ARTIFACT_TEXT
- MULTIPLE_ARTIFACTS
- MISSING_REQUIRED_FIELD
- INVALID_ENUM_LITERAL
- INVALID_ASSESSMENT_FIELD_SET
- MISSING_DUPLICATE_UNKNOWN_OR_STALE_COMMAND_ID
- PROHIBITED_CANONICAL_RECONSTRUCTION

schema_repair_attempted:
schema_repair_prompt:
schema_repair_result: not_applicable | succeeded | failed_malformed | blocked_fingerprint_mismatch
schema_repair_retry_budget_consumed:
second_malformed_escalated:
```

## Gate 3 history — implementation review

FAST: `not_applicable`. FULL verdicts are exactly `APPROVED` or `CHANGES REQUESTED`. Any implementation change requested here must return through Verifier and Gate 2 before re-review.

### Implementation review iteration <n>

```text
IMPLEMENTATION REVIEW

Plan version:

Implementation iteration:

Verdict:
APPROVED | CHANGES REQUESTED

Evidence reviewed:

Blocking findings:

Scope assessment:

Correctness / compatibility / tests / docs assessment:

Residual risks:
```

| Review iteration | Gate 3 verdict | Blocking findings | Resulting state |
| --- | --- | --- | --- |
|  |  |  |  |

## Environment/runtime failures

| Failure taxonomy | State/artifacts preserved | Requested capability | Available capability | Routing / next action |
| --- | --- | --- | --- | --- |
| `PROFILE_UNAVAILABLE` |  |  |  | fail closed |
| `INVOCATION_FAILED` |  |  |  | preserve; do not skip role |
| `MALFORMED_ARTIFACT` |  |  |  | one schema-only retry only if no product files changed and fingerprint unchanged; second escalates |
| `AGENT_LOOP_TIMEOUT_OR_LIMIT` |  |  |  | preserve partial evidence; do not blindly replay changed files |
| `TOOL_CAPABILITY_FAILURE` |  |  |  | fail closed when mandatory |

## USAGE ACCOUNTING

```text
Specialist invocations:
- Planner:
- Plan Critic:
- Implementer:
- Verifier:
- Reviewer:

Planner revisions:
Implementation revisions:
Verification reruns:
Review reruns:
Schema-only retries:
Human clarification count:

Started at:
Completed at:
Elapsed time:

Runtime/UI request or quota information:
not exposed | ...

Monetary cost:
not exposed | ...
```

Invocation counts are the default cost proxy. Do not fabricate monetary cost.

## FINAL COMMIT-PREPARATION SUMMARY

- Approved plan / FAST intake reference:
- Final changed-file scope:
- Final Gate 2 verdict and evidence:
- Final Gate 3 verdict: (`not_applicable` for FAST)
- Residual risks:
- Git authorization: **No Git mutation is authorized by this orchestration outcome.**

`CHANGE_COMPLETE` is ready for human handoff or separately authorized commit preparation only. It is not staged, committed, pushed, merged, or deployed. The later version-control workflow requires explicit human intent and independently inspects Git status/diff.

## Final outcome

- Final state: `PLAN_APPROVED` | `CHANGE_COMPLETE` | `AWAITING_ENVIRONMENT_RESOLUTION` | `ESCALATE_TO_HUMAN`
- Why stopped/completed:
- FAST-path completion based on Gate 2 (if applicable):
- Residual risks and human follow-up:
