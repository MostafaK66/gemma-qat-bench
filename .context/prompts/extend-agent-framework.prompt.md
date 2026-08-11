# Extend the Agent Framework

Use this prompt to add or update reusable agent-framework assets such as skills,
prompt templates, routing guidance, or path-specific instructions.

## Task

Implement: `<agent-framework change request>`

## Required workflow

1. Read `AGENTS.md`, `llms.txt`, and `.github/skills/agent-framework-maintenance/SKILL.md`.
2. Inspect adjacent framework files to match existing style and structure.
3. Identify exactly which framework artifacts must change and why.
4. Separate confirmed requirements from assumptions; ask one focused clarifying
   question only if ambiguity changes routing, behavior, or safety.
5. Propose the smallest coherent set of edits before making changes.
6. Implement the changes with consistent naming, references, and step ordering.
7. Validate referenced paths, filenames, and routing text across touched files.
8. If code/tests are touched, run repository quality gates.
9. Review for stale references, contradictions, and accidental secrets/local state.

## Acceptance criteria

- new or updated framework files are consistent with existing repository patterns
- instructions are concrete, ordered, and executable
- all referenced paths exist and are correctly named
- no conflicts are introduced with higher-priority repository guidance
- no unrelated refactors or generated artifacts are included
- final response states only checks that were actually executed

## Final handoff format

- **What changed**
- **Why this structure**
- **Files changed**
- **Checks run**
- **Remaining assumptions/risks**

