# Implement a Feature End-to-End

Use this prompt for a new capability or a meaningful behavior change.

## Task

Implement: `<feature/request>`

## Required workflow

1. Read `AGENTS.md`, `llms.txt`, and `.context/skills/feature-implementation/SKILL.md`.
2. Inspect the relevant source, tests, config, CLI/API surface, docs, and CI/tooling.
3. Summarize the current behavior and identify the module that should own the change.
4. Separate confirmed requirements from assumptions. Ask only the smallest necessary
   clarifying question if an important requirement is missing.
5. Propose the smallest coherent design before editing.
6. Implement the feature with clean responsibility boundaries and minimal unrelated
   refactoring.
7. Add/update tests for happy path, validation/boundary behavior, and important failures.
8. Update configuration, examples, CLI help, README, or docstrings when affected.
9. Run the repository quality gates.
10. Review the diff for accidental artifacts, duplicated logic, hidden globals, weak
    names, broad exception handling, and missing cleanup.

## Acceptance criteria

- requested behavior works through the intended public interface
- architecture remains coherent
- side effects are isolated/testable
- tests are deterministic and offline by default
- error messages are actionable
- no secrets or generated runtime artifacts are added
- documentation matches the implementation
- final response states only checks that were actually executed

## Final handoff format

- **What changed**
- **Why this design**
- **Files changed**
- **Tests/checks run**
- **Remaining assumptions/risks**
