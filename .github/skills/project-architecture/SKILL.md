---
name: project-architecture
description: Design or scaffold a high-quality Python repository, package, major subpackage, or architectural reorganization. Use when creating a new project, defining module boundaries, restructuring folders, or deciding where new responsibilities belong.
---

# Project Architecture

Design for clarity, testability, and changeability. Preserve the principles of the
repository's current structure without blindly copying its domain-specific filenames.

## Start with requirements

Before creating files, determine:

- what the software does and does not do,
- primary users and entry points,
- runtime/deployment model,
- external systems and side effects,
- configuration sources,
- expected outputs/artifacts,
- persistence/network/GPU/cloud needs,
- test levels,
- packaging/distribution needs,
- IDE/CI/developer workflow.

Separate confirmed facts from assumptions. Ask a focused question if a missing answer
would materially change architecture.

## Default Python structure

For a substantial package, prefer:

```text
project-root/
├── src/<package>/
├── tests/
├── configs/             # when runtime config exists
├── scripts/             # thin helpers, not a second application layer
├── .run/                # shared JetBrains run configs when useful
├── .github/
│   ├── copilot-instructions.md
│   ├── instructions/
│   └── skills/
│       └── <skill-name>/
│           └── SKILL.md
├── .context/            # reusable task prompts and local world-state template/context
│   ├── README.md
│   ├── world-state-TEMPLATE.md
│   └── prompts/
├── AGENTS.md
├── llms.txt
├── pyproject.toml
├── Makefile             # when it improves command discoverability
├── README.md
├── LICENSE
└── .gitignore
```

Use subpackages when a domain area has multiple cohesive modules. Do not create empty
folders merely to match a template.

Key repository conventions for agent assets:

- `.github/skills/` -> reusable native agent skills
- `.context/` -> prompts + local working context

## Module boundaries

Prefer modules/subpackages around responsibilities such as:

- configuration/validation,
- domain entities/value objects,
- pure business/domain logic,
- application orchestration/use cases,
- infrastructure adapters (HTTP, subprocess, DB, filesystem, GPU, cloud),
- metrics/calculation,
- reporting/serialization,
- CLI/API/job adapters,
- observability/error handling.

Exact names depend on the project.

## Dependency direction

Prefer:

```text
CLI/API/job adapters
        ↓
application/use-case layer
        ↓
domain logic + data models
        ↓
small abstractions
```

Infrastructure implements or is injected through those boundaries. Avoid importing
presentation/CLI code from domain modules.

## Entry points

Keep entry points thin. They should parse inputs, resolve config, invoke services, map
known errors, and render results. Complex logic belongs elsewhere.

## Side effects

Isolate external effects so unit tests can replace them with fakes:

- network clients,
- subprocess runners,
- clocks/sleep,
- filesystems where behavior is nontrivial,
- databases/message brokers,
- GPU/system queries,
- cloud APIs.

Do not build a framework around trivial side effects; use the smallest useful seam.

## Configuration

Prefer typed, validated, immutable configuration objects. Keep changeable environment or
runtime values out of source literals. Make precedence between defaults, files,
environment variables, and CLI overrides explicit.

## Tests

Mirror important source responsibilities under `tests/`. Keep ordinary unit tests
offline and deterministic. Put real-service tests in clearly separate integration/e2e
areas when the project needs them.

## Developer experience

A new developer should quickly discover:

- how to create the environment,
- how to install dependencies,
- how to run the application,
- how to run tests/lint/type checks,
- where config lives,
- where output goes,
- how CI validates changes.

Represent these in README, `pyproject.toml`, Makefile, CI, and shared IDE run configs when
useful.

## Avoid

- root-level production modules in a packaged Python project,
- `utils.py` dumping grounds,
- god classes/modules,
- circular imports,
- hidden mutable global state,
- duplicating config across code and scripts,
- business logic in shell scripts or CLI parsers,
- speculative service/repository/factory layers with no real boundary,
- committing runtime artifacts.

## Architecture review checklist

Before accepting a structure:

- [ ] Every important module has one clear responsibility.
- [ ] Dependencies flow in a comprehensible direction.
- [ ] External effects have testable boundaries.
- [ ] Entry points are thin.
- [ ] Config is explicit and validated.
- [ ] Tests can run offline by default.
- [ ] Package/import layout is standard.
- [ ] Tooling and docs make common workflows obvious.
- [ ] Structure fits the actual project rather than a copied template.
