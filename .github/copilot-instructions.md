# GitHub Copilot repository instructions

These instructions are always applicable to work in this repository.

This file is the concise always-on Copilot entry point; `AGENTS.md` is the
repository-wide engineering contract. When guidance differs, follow the most
specific applicable instruction while respecting correctness, security, and
the user's explicit request.

1. Read `AGENTS.md` before making non-trivial changes. Treat it as the repository-wide engineering and quality contract.
2. Read `llms.txt` for repository orientation, then inspect the relevant source, tests, configuration, CI, and documentation before editing.
3. If `.context/world-state.md` exists, use it only as current local working context. Never invent missing state, never overwrite an existing world-state from the template, and never put secrets in it.
4. For specialized work, load the matching `.github/skills/<skill>/SKILL.md` and follow its workflow.
5. When working on files matched by `.github/instructions/*.instructions.md`, follow the applicable path-specific instructions in addition to this file and `AGENTS.md`.
6. Reuse patterns already present in the repository before inventing a new abstraction.
7. Keep production code under `src/<package>/` and tests under `tests/`. Preserve clean responsibility boundaries; do not mechanically force future projects to use the same domain filenames.
8. Keep CLI/API/job entry points thin. Put business logic, orchestration, integrations, metrics, reporting, and configuration in focused modules with explicit responsibilities.
9. Isolate network, subprocess, filesystem, GPU, clock, database, cloud, and other external side effects behind small testable boundaries or injectable dependencies where practical.
10. Use typed, validated configuration and `pathlib.Path`. Prefer immutable data where practical. Use domain-specific exceptions and package logging; do not silently swallow failures.
11. Add or update tests for behavior changes. Unit tests must be deterministic and offline by default; use fakes/fixtures rather than requiring real network, GPU, cloud services, or subprocesses.
12. A bug fix should include a regression test when practical. Do not delete or weaken valid tests merely to make an implementation pass.
13. Before declaring work complete, run the repository quality gates defined by `pyproject.toml`, CI, and the Makefile. For this project that normally means:
    - `python -m pytest`
    - `python -m ruff check src tests`
    - `python -m mypy`
14. Never claim a test, build, benchmark, or command succeeded unless it was actually executed successfully. If a gate cannot be executed in the current environment, say so explicitly and list the command the human should run instead of assuming success.
15. Update README/config examples/help text when commands, setup, configuration, outputs, architecture, or public behavior change.
16. Do not commit secrets, credentials, model files, benchmark results, caches, virtual environments, provider-specific private state, local working state, or IDE user state.
17. Treat destructive commands, production/cloud mutations, force pushes, history rewrites, and similar irreversible operations as high risk and require explicit user intent.
18. For benchmarks, use consistent workloads, warmups when needed, repeated measured runs, reproducibility metadata, and cautious conclusions. Never generalize one hardware result into a universal claim.
19. Prefer the smallest coherent change. Do not mix unrelated refactors with a feature unless they are required for correctness or maintainability.
20. In the final handoff, state what changed, why, files affected, checks actually run, and any remaining assumptions or risks.

## Useful task routing

- project structure/scaffolding → `.github/skills/project-architecture/SKILL.md`
- Python implementation/refactoring → `.github/skills/python-engineering/SKILL.md`
- feature work → `.github/skills/feature-implementation/SKILL.md`
- tests → `.github/skills/testing/SKILL.md`
- debugging → `.github/skills/debugging/SKILL.md`
- review → `.github/skills/code-review/SKILL.md`
- documentation → `.github/skills/documentation/SKILL.md`
- agent-framework maintenance → `.github/skills/agent-framework-maintenance/SKILL.md`
- benchmarking → `.github/skills/benchmarking/SKILL.md`
- multi-role orchestration (V1/V1.5 planning or V2.2 FAST/FULL) → `.github/skills/orchestration/SKILL.md`
- version control / Git workflows → `.github/skills/version-control/SKILL.md`

If a routed skill or prompt file does not exist, fall back to the relevant guidance
in `AGENTS.md` and proceed. Never fabricate the contents of a missing file.

## Reusable task templates

Native Copilot Prompt Files may be unavailable in some enterprise-managed environments.

Reusable task templates therefore live under:

```text
.context/prompts/
```

Examples:

- `use the debug-fix prompt` → `.context/prompts/debug-fix.prompt.md`
- `use the implement-feature prompt` → `.context/prompts/implement-feature.prompt.md`
- `use the refactor prompt` → `.context/prompts/refactor.prompt.md`
- `use the review prompt` → `.context/prompts/review.prompt.md`
- `use the documentation prompt` → `.context/prompts/documentation.prompt.md`
- `use the extend-agent-framework prompt` → `.context/prompts/extend-agent-framework.prompt.md`
- `use the prepare-commit prompt` → `.context/prompts/prepare-commit.prompt.md`
- `use the integrate-branch prompt` → `.context/prompts/integrate-branch.prompt.md`
- `use the start-work-branch prompt` → `.context/prompts/start-work-branch.prompt.md`
- `use the orchestrate prompt` → `.context/prompts/orchestrate.prompt.md`
- `use the plan prompt` → `.context/prompts/plan.prompt.md`
- `use the critique-plan prompt` → `.context/prompts/critique-plan.prompt.md`
- `use the new-project prompt` → `.context/prompts/new-project.prompt.md`

For orchestration, preserve V1/V1.5 planning-only behavior. V2.1 contracts and V2.2 active
specialist-profile routing are defined in `.context/AGENT-ROLES.md` and
`.context/handoff-TEMPLATE.md`; `CHANGE_COMPLETE` never authorizes Git mutation.
