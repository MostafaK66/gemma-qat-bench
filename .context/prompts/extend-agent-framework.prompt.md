# Extend or Maintain the Agent Framework

Use this prompt when adding, modifying, renaming, or removing agent-framework assets
such as skills, reusable prompts, path-specific instructions, or framework docs.

## Task

Implement: `<framework change request>`

## Required workflow

1. Read `AGENTS.md`, `llms.txt`, and
   `.github/skills/agent-framework-maintenance/SKILL.md`.
2. Inspect the current framework before editing:
   - `.github/copilot-instructions.md`
   - `.github/instructions/`
   - `.github/skills/`
   - `.context/README.md`
   - `.context/prompts/`
   - `.context/world-state-TEMPLATE.md`
   - `.context/world-state.md` if it exists
3. Distinguish what is changing across framework layers:
   - repository-wide rules
   - path-specific instructions
   - reusable skills
   - reusable task prompts
   - local world state
4. Perform a consistency-impact analysis before implementation:
   - identify required synchronization targets
   - identify files that must remain untouched
   - separate required updates from optional improvements
5. Propose the smallest coherent change plan before editing.
6. Implement only the requested framework asset changes and required synchronization.
7. Verify references after changes by scanning for stale paths, missing routing updates,
   obsolete entries, and contradictory guidance.
8. Do not stage or commit unless explicitly requested.

## Acceptance criteria

- framework ownership boundaries remain clear
- required routing/documentation references are synchronized
- no unrelated framework cleanup is mixed in
- `.context/world-state.md` is never recreated or overwritten from template
- no missing-file content is fabricated unless requested as part of the change
- final response reports only verification that was actually performed

## Final handoff format

- **Assets created/changed/removed**
- **Routing/docs synchronized**
- **Verification performed**
- **Remaining assumptions/follow-up**

