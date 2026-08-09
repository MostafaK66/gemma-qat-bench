# GitHub Copilot repository instructions

These instructions are always applicable to work in this repository.

1. Read `AGENTS.md` before making non-trivial changes. Treat it as the engineering and quality contract.
2. Read `llms.txt` for repository orientation, then inspect the relevant source, tests, configuration, CI, and documentation before editing.
3. If `.context/world-state.md` exists, use it only as current local working context; never invent missing state and never put secrets in it.
4. For specialized work, load the matching `.github/skills/<skill>/SKILL.md` and follow its workflow.
5. Reuse the patterns already present in the repository before inventing a new abstraction.
6. Keep production code under `src/<package>/` and tests under `tests/`. Preserve clean responsibility boundaries; do not force every future project to use the same filenames when the domain differs.
7. Keep CLI/API/job entry points thin. Put business logic, orchestration, integrations, metrics, reporting, and configuration in focused modules with explicit responsibilities.
8. Isolate network, subprocess, filesystem, GPU, clock, database, and cloud side effects behind small testable boundaries or injectable dependencies.
9. Use typed, validated configuration and `pathlib.Path`. Prefer immutable data where practical. Use domain-specific exceptions and package logging; do not silently swallow failures.
10. Add or update tests for behavior changes. Unit tests must be deterministic and offline by default; use fakes/fixtures rather than requiring real network, GPU, cloud services, or subprocesses.
11. A bug fix should include a regression test when practical. Do not delete or weaken valid tests merely to make an implementation pass.
12. Before declaring work complete, run the repository quality gates defined by `pyproject.toml`, CI, and the Makefile. For this project that normally means `pytest`, `ruff check src tests`, and `mypy`.
13. Never claim a test, build, benchmark, or command succeeded unless it was actually executed successfully.
14. Update README/config examples/help text when commands, setup, configuration, outputs, architecture, or public behavior change.
15. Do not commit secrets, credentials, model files, benchmark results, caches, virtual environments, provider-specific private state, or IDE user state.
16. Treat destructive commands, production/cloud mutations, force pushes, and history rewrites as high risk; require explicit user intent.
17. For benchmarks, use consistent workloads, warmups when needed, repeated measured runs, reproducibility metadata, and cautious conclusions. Never generalize one hardware result into a universal claim.
18. Prefer the smallest coherent change. Do not mix unrelated refactors with a feature unless they are required for correctness or maintainability.
19. In the final handoff, state what changed, why, files affected, checks actually run, and any remaining assumptions or risks.

Useful task routing:

- project structure/scaffolding → `.github/skills/project-architecture/SKILL.md`
- Python implementation/refactoring → `.github/skills/python-engineering/SKILL.md`
- feature work → `.github/skills/feature-implementation/SKILL.md`
- tests → `.github/skills/testing/SKILL.md`
- debugging → `.github/skills/debugging/SKILL.md`
- review → `.github/skills/code-review/SKILL.md`
- documentation → `.github/skills/documentation/SKILL.md`
- benchmarking → `.github/skills/benchmarking/SKILL.md`

