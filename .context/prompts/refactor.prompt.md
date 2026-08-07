# Safe Refactor

Use this prompt when improving structure without intentionally changing external behavior.

## Objective

Refactor: `<target>`

## Rules

1. Read `AGENTS.md` and `.context/skills/python-engineering/SKILL.md`.
2. Identify the observable behavior that must remain unchanged.
3. Inspect existing tests first. Add characterization tests if the behavior is not safely
   covered.
4. Name the structural problem precisely: duplication, mixed responsibilities, coupling,
   hidden state, poor naming, untestable side effects, oversized module/class, etc.
5. Make one architectural improvement at a time.
6. Keep public API, CLI behavior, config semantics, error behavior, and output stable
   unless a change is explicitly requested.
7. Prefer moving/extracting responsibility over adding abstract layers with no real use.
8. Remove obsolete code only when tests/evidence show it is safe.
9. Run tests, lint, and type checks after the refactor.
10. Review the diff for behavior changes that were not part of the request.

## Deliverable

Explain:

- what structural problem was solved,
- what behavior was intentionally preserved,
- which tests prove preservation,
- whether any public contract changed,
- checks actually run.
