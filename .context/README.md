# `.context/` — Agentic Working Context

This directory contains reusable context for AI coding agents working on the repository.
It separates **always-relevant engineering rules** from **task-specific procedures** and
**personal session state**.

## Contents

```text
.context/
├── README.md
├── world-state-TEMPLATE.md
├── prompts/
│   ├── new-project.prompt.md
│   ├── implement-feature.prompt.md
│   ├── refactor.prompt.md
│   ├── debug-fix.prompt.md
│   ├── review.prompt.md
│   └── documentation.prompt.md
└── skills/
    ├── project-architecture/SKILL.md
    ├── python-engineering/SKILL.md
    ├── feature-implementation/SKILL.md
    ├── testing/SKILL.md
    ├── debugging/SKILL.md
    ├── code-review/SKILL.md
    ├── documentation/SKILL.md
    └── benchmarking/SKILL.md
```

## Tracked vs local state

Tracked files are reusable team/project guidance:

- `README.md`
- `world-state-TEMPLATE.md`
- `prompts/**`
- `skills/**`

Personal working state should remain untracked:

- `.context/world-state.md`
- `.context/private/`
- `.context/session-notes/`
- local backups or generated caches

Create your local state from the template when useful:

```bash
cp .context/world-state-TEMPLATE.md .context/world-state.md
```

On Windows PowerShell:

```powershell
Copy-Item .context\world-state-TEMPLATE.md .context\world-state.md
```

Do not store credentials, API keys, private keys, tokens, secrets, or sensitive data in
world state.

## How the layers work

### 1. Always-on instructions

- `.github/copilot-instructions.md`
- `AGENTS.md`

These define the repository-wide quality contract and should apply to nearly every task.

### 2. Orientation

- `llms.txt`

This is the fast repository map: purpose, important modules, quality commands, runtime
commands, and architectural boundaries.

### 3. Skills

`.context/skills/*/SKILL.md` files contain detailed procedures for specialized work.
The root `AGENTS.md` has a routing table telling agents which skill to load.

Use skills when the task matches their description; do not load every skill for every
request.

### 4. Prompt files

`.context/prompts/*.prompt.md` are reusable task templates. They are useful when starting
feature work, debugging, refactoring, code review, documentation, or a new project.

### 5. World state

`.context/world-state.md` is optional human-readable continuity between sessions. It
contains active goal, branch, decisions, blockers, verification, and next steps—not the
full chat transcript.

## PyCharm / JetBrains + GitHub Copilot

GitHub Copilot in JetBrains supports repository custom instructions, prompt files, and
agent customizations. For this repository:

1. Open the GitHub Copilot Chat panel.
2. Open **Settings / Customizations** from the Copilot panel.
3. Ensure workspace/repository instructions are enabled so
   `.github/copilot-instructions.md` is applied.
4. Add or manage the reusable prompt files from `.context/prompts/` if your Copilot
   version requires explicit registration.
5. Add `.context/skills/` as the project skill location when the Customizations UI allows
   a workspace skills directory.
6. Keep customizations at **Workspace** scope for project-specific behavior; use
   **Personal** scope only for preferences you want across unrelated repositories.

The root `AGENTS.md` provides a second, model-agnostic contract for agent-capable tools.

### Compatibility note

GitHub's documented standard project-skill locations include `.github/skills`,
`.claude/skills`, and `.agents/skills`. This repository keeps the richer engineering
workspace under `.context/` because it combines skills, prompts, and local state in one
clear place. The always-on Copilot instructions explicitly route agents to these skills,
and JetBrains Customizations can be used to register them directly.

If a future Copilot version requires one of the standard skill locations for automatic
skill discovery, either register `.context/skills` in the IDE or add thin adapters under
a supported standard location rather than duplicating the full skill content.

## Recommended session startup

For a non-trivial task, an agent should orient itself using:

```text
.github/copilot-instructions.md
        ↓
AGENTS.md
        ↓
llms.txt
        ↓
.context/world-state.md (if present)
        ↓
relevant skill
        ↓
relevant source + tests + config + docs
```

## Recommended session shutdown

After meaningful progress, update or propose an update to `.context/world-state.md` with:

- current goal/status,
- decisions made,
- files/areas changed,
- commands/tests actually run,
- blockers/risks,
- next concrete step.

Keep it short and factual.
