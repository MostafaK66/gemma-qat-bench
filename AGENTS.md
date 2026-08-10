# AGENTS.md — Engineering Contract for AI Coding Agents

This file defines the repository-wide engineering contract for AI coding agents.
It is intentionally stricter than a normal style guide: agents should use it as a
quality gate when designing, implementing, debugging, reviewing, documenting, or
refactoring code.

The current repository is `gemma-qat-bench`, but the architectural rules below are
written so the same framework can be reused in future Python projects whose domain
modules and filenames differ.

---

## 1. Instruction hierarchy

Before making a non-trivial change, load context in this order:

1. `.github/copilot-instructions.md` — short, always-on Copilot rules.
2. `AGENTS.md` — this engineering contract.
3. `llms.txt` — repository orientation and current architecture map.
4. `.context/world-state.md` if it exists — local, human-maintained current work.
5. The most relevant `.github/skills/<skill>/SKILL.md` for the task.
6. The relevant source, tests, config, CI, and documentation files.

If `.context/world-state.md` does not exist, continue without it. Never invent its
contents.

When instructions conflict, prefer the more specific instruction that is applicable
to the file/task, unless it would violate correctness, security, or an explicit user
request.

---

## 2. Project identity

`gemma-qat-bench` is a Python package and CLI for reproducible QAT-vs-non-QAT GGUF
benchmarking with `llama.cpp`.

Current high-level flow:

```text
configuration
    ↓
llama.cpp build
    ↓
model resolution/download
    ↓
llama-server lifecycle
    ↓
HTTP inference
    ↓
VRAM + timing capture
    ↓
metric aggregation
    ↓
QAT-vs-baseline report
```

The repository is deliberately structured so external effects are isolated and core
logic remains easy to test offline.

---

## 3. Architectural invariants

These rules apply to new code unless there is a strong, documented reason to deviate.

### 3.1 Use a `src/` package layout

Production Python belongs under:

```text
src/<importable_package>/
```

Tests belong under:

```text
tests/
```

Do not put importable production modules in the repository root.

### 3.2 Organize by responsibility, not by accidental size

Prefer focused modules with one clear reason to change. Separate concerns such as:

- configuration and validation
- domain models
- external process/build integration
- remote/network clients
- persistence or model/file resolution
- orchestration/application services
- metrics/calculation
- reporting/rendering
- CLI/API entry points
- logging/error handling

The exact filenames will differ between projects. Preserve the separation of concerns,
not the current filenames mechanically.

### 3.3 Keep entry points thin

`cli.py`, `__main__.py`, API handlers, job entry points, and equivalent adapters should:

1. parse/validate inputs,
2. resolve configuration,
3. call application/domain services,
4. render/return results,
5. translate known failures into useful exit codes or responses.

Do not place substantial business logic in an entry point.

### 3.4 Isolate side effects

Network calls, filesystem mutation, subprocess execution, GPU queries, databases,
message brokers, clocks, and other external dependencies should live behind small,
explicit interfaces or injectable callables where practical.

Core logic should not require a real network, GPU, cloud account, subprocess, or
external service just to be unit tested.

### 3.5 Prefer immutable validated configuration

For structured configuration:

- use typed dataclasses or equivalent typed models,
- prefer immutable/frozen values where practical,
- validate invariants at construction/loading time,
- fail early with domain-specific errors,
- use `pathlib.Path` for filesystem paths,
- keep environment/project-specific values in config rather than hardcoding them.

### 3.6 Make dependencies directional

Preferred dependency direction:

```text
entry points / adapters
        ↓
application orchestration
        ↓
domain logic / metrics / models
        ↓
small abstractions
```

Infrastructure implementations may depend on domain abstractions. Domain logic should
not import CLI or presentation code.

Avoid circular imports and hidden singleton state.

### 3.7 Design public APIs intentionally

- Keep `__init__.py` exports small and deliberate.
- Do not expose internals merely because they are convenient.
- Prefix private helpers with `_` where appropriate.
- Preserve backward compatibility unless the requested change explicitly allows a
  breaking change.

---

## 4. Target repository shape

For a substantial Python project, default toward this shape and adapt names to the
actual domain:

```text
project-root/
│
├── src/
│   └── <package>/
│       ├── __init__.py
│       ├── __main__.py             # only when module execution is useful
│       ├── exceptions.py
│       ├── _logging.py             # when package-specific logging is needed
│       ├── config.py
│       ├── <domain modules>.py
│       ├── <integration modules>.py
│       ├── <orchestration modules>.py
│       └── cli.py                   # when a CLI exists
│
├── tests/
│   ├── conftest.py
│   └── test_<module>.py             # mirrors important source modules
│
├── configs/                         # tracked example/default config
├── scripts/                         # thin operational/reference scripts only
├── .run/                            # shared JetBrains/PyCharm run configs
├── .github/
│   ├── copilot-instructions.md
│   ├── instructions/
│   ├── skills/
│   │   ├── project-architecture/
│   │   │   └── SKILL.md
│   │   ├── python-engineering/
│   │   │   └── SKILL.md
│   │   ├── feature-implementation/
│   │   │   └── SKILL.md
│   │   ├── testing/
│   │   │   └── SKILL.md
│   │   ├── debugging/
│   │   │   └── SKILL.md
│   │   ├── code-review/
│   │   │   └── SKILL.md
│   │   ├── documentation/
│   │   │   └── SKILL.md
│   │   └── benchmarking/
│   │       └── SKILL.md
│   └── workflows/
├── .context/
│   ├── README.md
│   ├── world-state-TEMPLATE.md
│   └── prompts/
├── AGENTS.md
├── llms.txt
├── pyproject.toml
├── Makefile                         # when useful for repeatable developer tasks
├── README.md
├── LICENSE
└── .gitignore
```

Do not create empty directories or boilerplate files with no real purpose. A small
project may need fewer modules. A large project may need subpackages. The governing
principle is clean responsibility boundaries plus predictable developer tooling.

---

## 5. Python engineering standards

For Python code:

- Target the Python version declared in `pyproject.toml`.
- Add type hints to public functions/methods and important internal boundaries.
- Prefer modern built-in generic syntax (`list[str]`, `dict[str, int]`) when supported.
- Prefer dataclasses for simple immutable data carriers.
- Prefer `pathlib.Path` over manual path-string manipulation.
- Prefer explicit dependencies over module-level mutable globals.
- Prefer small named helpers over dense clever expressions.
- Keep functions cohesive and usually short enough to understand without scrolling
  through unrelated responsibilities.
- Keep classes focused. Split a class that coordinates unrelated capabilities.
- Avoid premature abstraction. Extract an abstraction after a real boundary or repeated
  concept is visible.
- Avoid magic constants; use named constants or configuration.
- Avoid broad `except Exception` unless it is intentionally normalizing a boundary error;
  preserve the original exception with `raise ... from exc`.
- Use domain-specific exception types for expected application failures.
- Never silently swallow failures.
- Use package logging for operational information; reserve `print` for intended CLI
  output.
- Never log secrets, tokens, credentials, private keys, or sensitive payloads.
- Write comments for *why*, invariants, or non-obvious trade-offs—not to narrate obvious
  code.
- Keep docstrings accurate and concise. Public APIs and non-obvious modules deserve them.

Naming must be descriptive and domain-specific. Avoid names such as `data`, `tmp`,
`thing`, `helper`, `utils`, `manager2`, `process()`, or `do_work()` unless the concept is
truly generic and well-defined.

---

## 6. Change workflow — mandatory

For every non-trivial coding task, follow this sequence.

### Step 1 — Understand before editing

Inspect:

- the requested behavior,
- relevant source modules,
- existing tests,
- configuration,
- public API/CLI behavior,
- error handling,
- documentation,
- CI/tool configuration.

Search for existing patterns before creating a new pattern.

### Step 2 — State the design internally before implementation

Determine:

- what responsibility changes,
- which module owns it,
- what remains unchanged,
- whether a new abstraction is actually necessary,
- what tests prove the change,
- what failure modes matter.

For a large or ambiguous request, ask focused questions rather than inventing
requirements.

### Step 3 — Make the smallest coherent change

Prefer a complete vertical slice over scattered partial edits. Do not mix unrelated
cleanup into a feature unless the cleanup is required for correctness or maintainability.

### Step 4 — Add or update tests with the implementation

A behavior change without an appropriate test is incomplete unless testing is genuinely
impossible; if so, explain why.

### Step 5 — Run quality gates

At minimum, run the repository equivalents of:

```bash
pytest
ruff check src tests
mypy
```

Use `pyproject.toml`, CI, and the Makefile as the source of truth for exact commands.
Do not claim tests passed unless they were actually run successfully.

### Step 6 — Update developer-facing artifacts

Update the relevant README/config example/docstring/help text when behavior, setup,
commands, configuration, output, or architecture changes.

### Step 7 — Handoff clearly

Summarize:

- what changed,
- why,
- files affected,
- tests/quality commands run and their result,
- any remaining assumptions, risks, or follow-up.

---

## 7. Testing contract

Use `.github/skills/testing/SKILL.md` for detailed test work.

Universal expectations:

- Unit tests are deterministic and offline by default.
- Test behavior, not implementation trivia.
- Mirror important source modules with corresponding test modules.
- Cover the happy path, validation boundaries, and meaningful failure paths.
- Use fixtures/fakes for network, subprocess, clock, filesystem, GPU, and external
  services when appropriate.
- Prefer dependency injection to monkeypatching deep implementation internals.
- A regression fix must include a regression test when practical.
- Do not weaken or delete a valid test merely to make a new implementation pass.
- Keep integration/e2e tests explicitly separated when they require real external
  resources.
- Avoid nondeterministic sleeps. Inject clocks/sleep functions or poll deterministic
  state where possible.

When changing a public contract, update both tests and documentation.

---

## 8. Configuration and CLI contract

- Configuration files should be human-readable, validated, and documented.
- CLI flags may override configuration, but precedence must be deterministic.
- Help text must describe actual behavior.
- Error messages should be actionable: include the failing resource/path/condition and
  the likely corrective action where known.
- Do not silently choose a dangerous or expensive default.
- External resource identifiers, ports, paths, timeouts, model IDs, URLs, and thresholds
  belong in configuration when users may need to change them.

---

## 9. Reproducibility and benchmark rules

For performance, ML, data, or benchmark code:

- Compare variants under the same workload unless the experiment explicitly studies a
  workload difference.
- Record enough environment/configuration metadata to interpret results.
- Warm up when one-time initialization would bias measurements.
- Use repeated measured runs for noisy performance data.
- Report both central tendency and spread when useful.
- Distinguish server-reported timing from client wall-clock timing.
- Do not turn one benchmark result into a universal product/model claim.
- Do not modify benchmark methodology merely to obtain a desired result.

Use `.github/skills/benchmarking/SKILL.md` for benchmark-specific changes.

---

## 10. Documentation contract

Documentation must be executable in spirit: commands, paths, flags, filenames, and
examples should match the code.

A high-quality README should usually contain:

- project purpose and scope,
- architecture/workflow,
- requirements,
- installation,
- quick start,
- all important run/test/build commands,
- configuration,
- outputs,
- project structure,
- development workflow,
- troubleshooting,
- limitations/reproducibility notes,
- license/attribution where relevant.

Never invent benchmark numbers, supported platforms, API behavior, or environment
requirements that are not supported by code or evidence.

---

## 11. Security and safety

- Never add credentials, tokens, secrets, private keys, personal access tokens, or
  environment-specific confidential data to tracked files.
- Never suggest committing `.env` files containing secrets.
- Validate untrusted input at system boundaries.
- Avoid shell injection: prefer argument lists to shell command strings.
- Do not add `shell=True` without a demonstrated need and explicit safety reasoning.
- Pin or constrain dependencies appropriately for the project; do not add dependencies
  for trivial functionality.
- Treat destructive commands (`rm -rf`, deleting cloud resources, production writes,
  force pushes, history rewrites) as high-risk and require explicit user intent.

---

## 12. Refactoring rules

A refactor should improve structure while preserving observable behavior unless a
behavior change is explicitly requested.

Before refactoring:

1. identify the behavior contract,
2. ensure tests cover it,
3. isolate the structural problem,
4. change one architectural concern at a time.

After refactoring:

- public behavior remains stable,
- tests stay meaningful,
- complexity is lower or responsibility boundaries are clearer,
- dead code and obsolete compatibility layers are removed when safe,
- documentation reflects any new structure.

Do not introduce abstractions whose only benefit is making the code look more
"enterprise".

---

## 13. Code review priority

When reviewing code, prioritize findings in this order:

1. correctness and data loss,
2. security and unsafe operations,
3. broken public contracts/backward compatibility,
4. concurrency/resource lifecycle issues,
5. error handling and observability,
6. architecture/coupling,
7. tests and missing edge cases,
8. performance/reproducibility,
9. maintainability/readability,
10. style.

Report concrete findings with file/line context and impact. Do not manufacture issues to
fill a review.

---

## 14. Anti-patterns — do not introduce

- giant "god" modules or classes,
- business logic in CLI/API entry points,
- hidden mutable global state,
- generic `utils.py` dumping grounds,
- duplicated config literals across modules,
- broad exception swallowing,
- unbounded retry loops,
- tests that require internet/GPU/cloud for ordinary unit coverage,
- mocks that assert every private call rather than observable behavior,
- copy-pasted implementations where a stable shared concept already exists,
- speculative abstractions with no current use,
- comments/docstrings that contradict the code,
- generated files committed when they are runtime artifacts and should be ignored.

---

## 15. Definition of Done

A task is complete only when all applicable items are true:

- [ ] Requested behavior is implemented.
- [ ] Architecture remains coherent and responsibilities are correctly placed.
- [ ] Public interfaces/configuration are deliberate and validated.
- [ ] Unit/regression tests cover the change.
- [ ] Existing tests still pass.
- [ ] Lint/type checks pass or any known failure is explicitly explained.
- [ ] External resources are cleaned up correctly.
- [ ] Logging/errors are actionable and do not expose secrets.
- [ ] README/config/examples/help text are updated when affected.
- [ ] No unrelated artifacts, secrets, local paths, model files, results, caches, or IDE
      user state are committed.
- [ ] Final handoff states what was verified rather than assuming success.

---

## 16. Skill routing

Load the most relevant skill for detailed procedures:

| Task | Skill |
| --- | --- |
| Design/scaffold a new project or major package | `.github/skills/project-architecture/SKILL.md` |
| Write or refactor Python production code | `.github/skills/python-engineering/SKILL.md` |
| Implement a feature end-to-end | `.github/skills/feature-implementation/SKILL.md` |
| Create or improve tests | `.github/skills/testing/SKILL.md` |
| Diagnose and fix a bug | `.github/skills/debugging/SKILL.md` |
| Review a change/PR | `.github/skills/code-review/SKILL.md` |
| README/docs/API documentation | `.github/skills/documentation/SKILL.md` |
| Performance/ML benchmark work | `.github/skills/benchmarking/SKILL.md` |

### Reusable task templates

Reusable task templates live under:

`.context/prompts/<name>.prompt.md`

They define how to frame a particular interaction, while
`.github/skills/<skill>/SKILL.md` defines how that category of work should be performed.

Native Copilot Prompt Files may be unavailable in enterprise-managed environments.
Therefore, do not require `/PROMPT_NAME` support.

When the user explicitly asks to use, apply, or follow a named prompt, load the matching
template from `.context/prompts/`.

Examples:

- `use the debug-fix prompt` -> `.context/prompts/debug-fix.prompt.md`
- `use the implement-feature prompt` -> `.context/prompts/implement-feature.prompt.md`
- `use the refactor prompt` -> `.context/prompts/refactor.prompt.md`
- `use the review prompt` -> `.context/prompts/review.prompt.md`
- `use the documentation prompt` -> `.context/prompts/documentation.prompt.md`
- `use the new-project prompt` -> `.context/prompts/new-project.prompt.md`

When applicable, use both the task template and the relevant native skill:

```text
user request
    ↓
.context/prompts/<task>.prompt.md
    ↓
.github/skills/<skill>/SKILL.md
    ↓
repository source + tests + config + docs
```

---

## 17. Session state protocol

`.context/world-state.md` is optional personal working memory and is gitignored.

Before creating it, always check whether it already exists.

If `.context/world-state.md` already exists:

- read and preserve the existing file,
- never replace it with `.context/world-state-TEMPLATE.md`,
- update only the sections that materially changed,
- preserve useful existing decisions, verification evidence, blockers, and history.

If `.context/world-state.md` does not exist, create it from
`.context/world-state-TEMPLATE.md`.

Never blindly copy the template over an existing world-state file. Because the file is
gitignored, overwriting it may destroy local session context that Git cannot restore.

When meaningful work changes the current goal, design decision, blocker, environment,
or next step, propose/update the relevant section of `world-state.md`. Keep it concise;
it is a human-readable bridge between coding sessions, not a dump of chat history.

Never put secrets or sensitive credentials in world state.

---

