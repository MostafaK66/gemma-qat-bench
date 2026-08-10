# `.context/` — Agentic Working Context

This directory contains reusable task context and local working state for AI coding agents
working on the repository.

Repository-wide engineering rules and native Copilot skills live outside `.context/`.
The `.context/` directory is intentionally focused on reusable task templates and
human-maintained session continuity.

## Related agentic structure

```text
repository-root/
├── .github/
│   ├── copilot-instructions.md
│   ├── instructions/
│   │   ├── python.instructions.md
│   │   ├── tests.instructions.md
│   │   └── documentation.instructions.md
│   └── skills/
│       ├── project-architecture/SKILL.md
│       ├── python-engineering/SKILL.md
│       ├── feature-implementation/SKILL.md
│       ├── testing/SKILL.md
│       ├── debugging/SKILL.md
│       ├── code-review/SKILL.md
│       ├── documentation/SKILL.md
│       └── benchmarking/SKILL.md
│
├── .context/
│   ├── README.md
│   ├── world-state-TEMPLATE.md
│   └── prompts/
│       ├── new-project.prompt.md
│       ├── implement-feature.prompt.md
│       ├── refactor.prompt.md
│       ├── debug-fix.prompt.md
│       ├── review.prompt.md
│       └── documentation.prompt.md
│
├── AGENTS.md
└── llms.txt
```

