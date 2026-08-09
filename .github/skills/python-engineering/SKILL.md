---
name: python-engineering
description: Apply production-quality Python design and implementation standards. Use when creating, modifying, refactoring, or reviewing Python modules, classes, functions, configuration, CLI code, or integrations.
---

# Python Engineering

## Core standards

- Follow the Python version and tooling declared in `pyproject.toml`.
- Type public APIs and important internal boundaries.
- Use modern built-in generic types when supported.
- Prefer `pathlib.Path` for paths.
- Prefer immutable/frozen dataclasses for value/config objects when practical.
- Keep functions cohesive and names domain-specific.
- Keep classes focused on one responsibility.
- Prefer composition and explicit dependencies to global state or deep inheritance.
- Avoid generic dumping-ground modules such as `utils.py`.

## Error handling

- Validate at boundaries and fail early.
- Use domain/application-specific exception types for expected failures.
- Preserve causal context with `raise ... from exc`.
- Catch broad exceptions only at a real boundary where errors are intentionally normalized.
- Never silently swallow exceptions.
- Make error messages actionable and include the relevant path/resource/condition.

## Side-effect boundaries

For network, subprocess, filesystem, GPU, cloud, time, DB, broker, or other external
behavior:

- keep the implementation behind a small explicit boundary,
- inject a callable/protocol/client where it materially improves testing,
- avoid direct external calls from pure metric/domain code,
- ensure resources/processes are closed/stopped in success and failure paths.

Do not over-engineer trivial calls merely for stylistic purity.

## Logging and output

- Use package logging for diagnostics and operational events.
- Reserve `print` for intentional CLI output.
- Do not log credentials, tokens, private keys, or sensitive payloads.
- Log meaningful lifecycle transitions and failures, not every line of control flow.

## API design

- Keep `__init__.py` exports intentional.
- Treat leading-underscore names as implementation details.
- Avoid widening a public API accidentally.
- Preserve backward compatibility unless a breaking change is requested and documented.

## Readability

Prefer:

- named helpers over nested complex expressions,
- guard clauses over deeply nested branches,
- explicit state transitions over clever implicit behavior,
- comments explaining invariants/trade-offs rather than obvious syntax.

Avoid vague names such as `data`, `tmp`, `obj`, `thing`, `helper`, `process`, or `result`
when a domain-specific name exists.

## Dependency additions

Before adding a dependency:

1. check whether the standard library or an existing dependency already solves it,
2. justify the maintenance/runtime cost,
3. add it in `pyproject.toml`,
4. update docs if installation/runtime behavior changes,
5. test the affected path.

## Refactoring threshold

Extract a new module/class when there is a real responsibility boundary, repeated
concept, independent lifecycle, or testability benefit. Do not extract solely to make a
file shorter.

## Completion checks

- [ ] behavior is clear from names and structure,
- [ ] side effects are isolated appropriately,
- [ ] expected failures use clear exceptions,
- [ ] resource cleanup is correct,
- [ ] tests cover changed behavior,
- [ ] lint/type checks pass,
- [ ] docs/config/help are updated when affected.
