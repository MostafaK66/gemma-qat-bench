---
name: testing
description: Design, write, improve, or review deterministic Python tests. Use when adding unit/regression tests, improving fixtures/fakes, testing error paths, or deciding what should be integration-tested.
---

# Testing

## Philosophy

Tests should prove observable behavior and make refactoring safer. Ordinary unit tests
must be fast, deterministic, and offline by default.

## Test structure

- Mirror important source responsibilities with `test_<module>.py` files.
- Put reusable fixtures/fakes in `conftest.py` only when genuinely shared.
- Keep test names behavior-oriented: `test_<condition>_<expected_outcome>`.
- Prefer Arrange → Act → Assert clarity without excessive comments.

## What to cover

For changed behavior, consider:

1. normal/happy path,
2. validation boundaries,
3. empty/minimal/maximal meaningful cases,
4. malformed external responses,
5. external dependency failure,
6. timeout/lifecycle/cleanup behavior,
7. fallback behavior,
8. regression scenario that motivated the change.

Do not chase line coverage at the expense of meaningful contracts.

## External effects

Prefer injected fakes for:

- HTTP sessions/clients,
- subprocess runners/processes,
- downloads,
- clocks/sleep,
- GPU/system commands,
- cloud/database/broker clients.

Prefer a small fake implementing the protocol/behavior you need over a heavily configured
mock that knows private implementation details.

## Assertions

Assert outcomes that matter:

- return values,
- raised domain errors and useful messages,
- state changes,
- externally visible calls/arguments at system boundaries,
- cleanup/termination,
- rendered output contracts.

Avoid assertions on private helper call order unless order is itself the contract.

## Regression fixes

For a bug:

1. reproduce the defect in a test,
2. confirm the test fails for the right reason,
3. implement the fix,
4. confirm the regression test passes,
5. run the broader suite.

If reproducing the failure safely is impossible, document why and test the nearest stable
boundary.

## Timing/concurrency

- Avoid real sleeps in unit tests.
- Inject monotonic clocks/sleep functions when timing logic exists.
- Use deterministic state transitions for lifecycle tests.
- Do not use arbitrary long timeouts to hide races.

## Integration tests

Use real network/GPU/cloud only in explicitly identified integration/e2e tests. Make
requirements and cost clear. Unit CI should not depend on such resources unless the
repository intentionally provisions them.

## Test quality review

Reject tests that:

- only duplicate implementation logic,
- are nondeterministic,
- require internet for normal unit coverage,
- modify developer/global state without cleanup,
- depend on execution order,
- weaken valid assertions to accommodate broken code.

## Verification

For this repository, normally run:

```bash
pytest
pytest <focused-test-path> -q
ruff check src tests
mypy
```

Never report a command as passing unless it was actually executed successfully.


