---
name: agent-framework-maintenance
description: Extend or maintain the repository's agent framework assets, including AGENTS routing, reusable skills, reusable prompt templates, and instruction alignment.
---

# Agent Framework Maintenance

Use this skill when adding or updating:

- `.github/skills/*/SKILL.md`
- `.context/prompts/*.prompt.md`
- `.github/instructions/*.instructions.md`
- routing references in `AGENTS.md`, `llms.txt`, and `.github/copilot-instructions.md`

## 1. Load framework context first

Before editing, read:

1. `AGENTS.md`
2. `llms.txt`
3. `.github/copilot-instructions.md`
4. `.context/README.md` (if present)
5. Existing neighboring skills/prompts/instructions that should stay consistent

If a referenced file is missing, continue without fabricating its contents.

## 2. Define scope and ownership

Write down what is changing:

- new skill, prompt, or instruction
- updates to routing/discoverability references
- behavioral constraints versus editorial cleanup

Keep the change small and coherent. Do not mix unrelated refactors.

## 3. Reuse established patterns

Match repository conventions for:

- markdown structure and heading depth
- YAML frontmatter in `SKILL.md` files
- numbered workflow steps in prompt templates
- wording style used in adjacent framework files

Prefer adapting an existing template over inventing a new format.

## 4. Keep guidance executable

Each new skill/prompt should be actionable and specific:

- name exactly which files to inspect first
- define a concrete step order
- include verification expectations
- avoid vague advice that cannot be followed

Do not claim any command was verified unless you actually ran it.

## 5. Validate cross-file consistency

Check that:

- referenced paths exist and match casing
- skill/prompt names align with routing text
- no instructions conflict with higher-priority repository rules
- no stale references remain in framework docs

When discoverability is affected, update references in `AGENTS.md`, `llms.txt`, or
other framework indexes as needed.

## 6. Verification expectations

For framework-only markdown changes, run focused checks that are available in your
environment (for example, targeted searches or repository checks).

When production/test code also changes, run repository quality gates:

```bash
python -m pytest
python -m ruff check src tests
python -m mypy
```

## Done means

The framework extension is internally consistent, follows repository patterns, includes
clear execution steps, and documents only checks that were actually performed.

