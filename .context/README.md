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

## Tracked vs local state

Tracked reusable guidance includes:

- `.context/README.md`
- `.context/world-state-TEMPLATE.md`
- `.context/prompts/**`
- `.github/skills/**`
- `.github/copilot-instructions.md`
- `.github/instructions/**`
- `AGENTS.md`
- `llms.txt`

Personal working state should remain untracked:

- `.context/world-state.md`
- `.context/private/`
- `.context/session-notes/`
- local backups or generated caches

Create local world state from the template when useful:

```powershell
if (-not (Test-Path .context\world-state.md)) {
    Copy-Item .context\world-state-TEMPLATE.md .context\world-state.md
} else {
    Write-Host ".context/world-state.md already exists; leaving it unchanged."
}
```

```bash
if [ ! -f .context/world-state.md ]; then
    cp .context/world-state-TEMPLATE.md .context/world-state.md
else
    echo ".context/world-state.md already exists; leaving it unchanged."
fi
```

Never overwrite an existing `.context/world-state.md` with the template. The existing
file may contain important local session history that is intentionally not tracked by Git.

