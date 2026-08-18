# Repair Verifier Schema Output (No Product Change)

Use this prompt only for a single schema-only retry after a malformed Gate 2 verifier artifact where product files did not change.

## Required inputs from Orchestrator

- task ID
- orchestration depth
- current plan version / FAST intake reference
- implementation iteration
- verification iteration
- current implementation fingerprint binding (`implementation_fingerprint_algorithm`, `implementation_fingerprint`, `implementation_fingerprint_scope`, `implementation_fingerprint_captured_at`)
- prior malformed VERIFICATION artifact text
- exact malformed structural defect codes
- required VERIFICATION schema text
- task-scoped read-only verification context (same evidence scope as prior attempt)

## Preconditions and budget

- Recalculate implementation fingerprint before repair delegation.
- Repair is allowed only if fingerprint is unchanged from the bound attempt fingerprint.
- If fingerprint changed: mark prior evidence stale, do not run repair, do not consume schema-retry budget, fail closed/escalate per contract.
- Retry budget is unchanged: at most one no-product-change schema-only retry.
- A second malformed artifact fails closed and escalates.

## Operating contract

- Repair structure only and re-emit exactly one compliant `VERIFICATION` artifact.
- No product changes, no verification command execution, no scope changes, no specialist delegation.
- No new evidence, no evidence reconstruction, no canonical field recreation, no explanation of repair process.
- Do not add preamble, epilogue, Markdown fence, second root artifact, or any outside text.

## Required output

Return exactly one plain `VERIFICATION` artifact conforming to the required schema and current binding context.
