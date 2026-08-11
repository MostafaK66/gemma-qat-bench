---
name: agent-framework-maintenance
description: Safely add, modify, rename, or remove agent-framework assets while synchronizing only the required references across AGENTS.md, llms.txt, Copilot instructions, skills, prompts, and context documentation.
---

# Agent Framework Maintenance

Use this skill when changing the repository's agent framework assets, including:

- reusable skills under `.github/skills/`
- reusable task prompts under `.context/prompts/`
- path-specific instruction files under `.github/instructions/`
- framework documentation and routing maps

## Source of truth and boundaries

Treat the existing repository framework as the source of truth.

Before editing framework assets, inspect:

1. `AGENTS.md`
2. `llms.txt`
3. `.github/copilot-instructions.md`
4. `.github/instructions/`
5. `.github/skills/`
6. `.context/README.md`
7. `.context/prompts/`
8. `.context/world-state-TEMPLATE.md`
9. `.context/world-state.md` if it exists

Keep framework layers distinct:

- repository-wide engineering rules -> `AGENTS.md`
- path-specific instructions -> `.github/instructions/*.instructions.md`
- reusable specialized skills -> `.github/skills/<skill>/SKILL.md`
- reusable task templates -> `.context/prompts/*.prompt.md`
- local world state -> `.context/world-state.md` (gitignored)

Do not duplicate detailed skill procedures into `AGENTS.md`, `llms.txt`, or `.github/copilot-instructions.md`.

## Consistency-impact analysis (required before edits)

For every framework asset add/change/rename/remove:

1. Identify the ownership layer (rules, instruction, skill, prompt, local state).
2. Identify all references that must be synchronized.
3. Separate required updates from optional improvements.
4. Confirm what should stay untouched.

When adding/removing/renaming skills or prompts, explicitly check for references in:

- routing tables
- repository maps/trees
- prompt examples and usage docs
- framework orientation docs

Never fabricate a missing referenced file unless creating it is part of the requested change.

## Implementation rules

- Make the smallest coherent framework change.
- Update only affected references; avoid unrelated framework cleanup.
- Preserve each layer's intended responsibility.
- Never overwrite `.context/world-state.md` from `.context/world-state-TEMPLATE.md`.
- Never stage or commit changes unless explicitly requested.

## Post-change verification

After edits, scan for framework consistency issues:

- stale paths
- missing/obsolete routing entries
- renamed assets not synchronized
- contradictory guidance between framework docs

Report clearly:

- assets created/changed/removed
- files synchronized and why
- verification performed
- remaining assumptions, risks, or follow-up

