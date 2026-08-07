---
name: feature-implementation
description: Implement a new capability or behavior change end to end with correct ownership, tests, configuration, documentation, and verification. Use for feature work that touches one or more production modules.
---

# Feature Implementation

## 1. Discover the existing contract

Inspect the nearest relevant:

- source modules,
- tests,
- configuration,
- public API/CLI,
- exceptions/logging,
- README/docs,
- CI/tool configuration.

Search for an existing pattern before adding a new one.

## 2. Define the behavior

Write down internally:

- input and expected output,
- validation rules,
- failure behavior,
- owning module/responsibility,
- external side effects,
- compatibility constraints,
- test cases needed.

If an ambiguity would change architecture or public behavior, ask a focused question.

## 3. Choose the smallest coherent design

Prefer extending the module that already owns the responsibility. Create a new module
only when there is a real boundary such as a new integration, lifecycle, domain concept,
or independently testable service.

Keep entry points thin and orchestration separate from integration details.

## 4. Implement with testable boundaries

- Keep pure logic independent of external resources.
- Inject external clients/runners/clocks where useful.
- Validate configuration/input early.
- Use domain-specific exceptions.
- Ensure cleanup in all paths.
- Avoid unrelated refactors.

## 5. Test the behavior

At minimum consider:

- happy path,
- invalid input/config,
- external failure normalization,
- boundary values,
- cleanup/resource lifecycle,
- backward compatibility/regression.

Unit tests should remain offline unless the task explicitly concerns an integration test.

## 6. Update user/developer surfaces

If the feature changes any of these, update them in the same change:

- README usage,
- CLI help,
- config examples,
- output format,
- public docstrings,
- Makefile/run config,
- CI dependency/tooling.

## 7. Verify

Run the focused test first, then repository quality gates. For this project, normally:

```bash
pytest
ruff check src tests
mypy
```

Run an actual runtime/benchmark command only when the environment is available and the
operation is appropriate/cost-conscious.

## 8. Self-review

Check the diff for:

- duplicated logic,
- vague naming,
- accidental public API growth,
- hidden mutable state,
- broad exception swallowing,
- missing cleanup,
- test implementation coupling,
- stale docs,
- secrets/local paths/runtime artifacts.

## Done means

The feature works through the intended public interface, is covered by meaningful tests,
fits the architecture, has accurate docs/config, and has evidence from checks actually
run.
