# Create or Update Technical Documentation

Use this prompt for README work, architecture docs, usage guides, configuration docs,
runbooks, or API documentation.

## Documentation target

`<file/topic>`

## Required workflow

1. Read `AGENTS.md` and `.context/skills/documentation/SKILL.md`.
2. Inspect the implementation, config, CLI help, tests, scripts, and CI that define the
   documented behavior.
3. Treat executable code/config as the source of truth when prose is stale.
4. Do not invent commands, flags, supported environments, benchmark results, APIs, or
   architecture.
5. Write for a new developer who should be able to install, run, test, configure,
   troubleshoot, and understand the project without chat history.
6. Keep examples copy-pasteable and paths/filenames exact.
7. Call out limitations, assumptions, expensive operations, external dependencies, and
   reproducibility concerns where relevant.
8. Prefer diagrams/tables only when they materially improve understanding.
9. Re-read the final document against the code for contradictions.

## Expected sections for a substantial README

- purpose and scope
- key features
- architecture/workflow
- requirements
- installation
- quick start
- CLI/API usage
- configuration
- outputs/metrics
- project structure
- development/test/lint/type-check commands
- IDE/CI notes when useful
- troubleshooting
- reproducibility/limitations
- attribution/license

Adapt the sections to the actual project; do not add empty boilerplate headings.
