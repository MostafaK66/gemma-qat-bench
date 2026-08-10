# New Project / Major Package Scaffold

Use this prompt when creating a new repository, a substantial new package, or a major
architectural area.

## Goal

Design a production-quality project structure that is simple, testable, maintainable,
and appropriate for the actual domain. Use `AGENTS.md` and
`.github/skills/project-architecture/SKILL.md` as the governing standards.

## Instructions

Before creating files:

1. Determine the project type, runtime, package name, entry points, external systems,
   configuration needs, test strategy, deployment/runtime model, and developer tooling.
2. Inspect any existing repository conventions before introducing a new structure.
3. Separate confirmed requirements from assumptions. Ask focused questions for
   consequential unknowns.
4. Produce a short architecture plan showing responsibilities and dependency direction.

Then create the smallest complete structure that normally includes, when applicable:

```text
src/<package>/          production package
tests/                  mirrored deterministic tests
configs/                tracked example/default config
scripts/                thin operational helpers
.run/                   shared JetBrains run configs
.github/
  copilot-instructions.md
  instructions/
  skills/
    <skill-name>/
      SKILL.md
.context/               reusable task prompts and local world-state template/context
  README.md
  world-state-TEMPLATE.md
  prompts/
AGENTS.md
llms.txt
pyproject.toml
Makefile
README.md
LICENSE
.gitignore
```

Treat these paths deliberately when scaffolding:

- `.github/skills/` -> canonical reusable agent skills
- `.context/prompts/` -> reusable task templates
- `.context/world-state.md` -> local, untracked working context

Do not create empty boilerplate modules. Filenames inside the package must follow actual
responsibilities, not copy another project's domain names.

## Quality requirements

- thin entry points
- explicit configuration and validation
- isolated side effects
- typed public boundaries
- domain-specific errors
- structured logging
- dependency injection where external effects make testing difficult
- offline unit tests by default
- CI running the real quality gates
- complete README with setup/run/test/config/output/troubleshooting
- no secrets or generated runtime artifacts committed

## Deliverable

Return:

1. proposed tree,
2. responsibility of each important module,
3. dependency flow,
4. implementation/scaffolding changes,
5. tests and quality checks actually run,
6. any assumptions or deliberate deviations from the standard structure.
