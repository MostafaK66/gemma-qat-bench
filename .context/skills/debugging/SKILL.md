---
name: debugging
description: Diagnose and fix runtime errors, failing tests, regressions, bad output, lifecycle failures, integration problems, or performance anomalies using evidence-first root-cause analysis.
---

# Debugging

## Principle

Do not patch symptoms before understanding the fault path. Treat logs, failing tests,
stack traces, config, and reproducible commands as evidence.

## Workflow

1. Capture the exact observed behavior and expected behavior.
2. Reproduce it if safe and practical.
3. Identify the failing boundary: input/config, domain logic, orchestration, network,
   subprocess, filesystem, GPU/system, rendering, etc.
4. Trace inputs and state through that boundary.
5. Form the smallest plausible hypotheses.
6. Test hypotheses with focused inspection/commands/tests.
7. Distinguish confirmed facts from inference.
8. Add a regression test where practical.
9. Implement the smallest root-cause fix.
10. Run focused and broad verification.

## Evidence hierarchy

Prefer:

1. deterministic failing test/reproduction,
2. exact stack trace/error response,
3. code path + validated config,
4. logs with timestamps/context,
5. environment/tool versions,
6. hypothesis.

Do not promote a hypothesis to root cause without supporting evidence.

## Common areas to inspect

- config precedence and path resolution,
- malformed/missing external response fields,
- timeouts and retries,
- process startup/shutdown,
- leaked resources,
- port/file locks,
- missing tool/runtime dependencies,
- stale cache/artifact assumptions,
- version/API mismatch,
- CPU/GPU capability mismatch,
- incorrect fallback behavior,
- hidden state between tests/runs.

## Fix quality

A good fix:

- addresses the earliest correct fault boundary,
- preserves valid behavior,
- produces an actionable error when recovery is impossible,
- cleans up resources,
- adds regression coverage,
- does not mask unrelated failures with broad exception handling.

## Performance anomalies

When debugging performance, hold workload/config/hardware constant before attributing a
difference to code/model changes. Separate prompt/prefill time, generation time, wall
clock, startup/load time, and measurement overhead.

## Final handoff

State:

- confirmed root cause (or clearly labeled leading hypothesis),
- supporting evidence,
- exact fix,
- regression test,
- verification commands/results,
- remaining risk/follow-up.
