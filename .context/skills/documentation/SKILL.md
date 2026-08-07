---
name: documentation
description: Create or maintain accurate technical documentation, READMEs, setup guides, architecture explanations, configuration references, CLI usage, outputs, troubleshooting, and developer onboarding based on the actual codebase.
---

# Documentation

## Source of truth

Inspect code, configuration, CLI help, tests, scripts, CI, and package metadata before
writing. If existing prose conflicts with executable behavior, verify and document the
actual behavior; do not silently guess.

## README standard

For a substantial project, include applicable sections:

- purpose and scope,
- what the project does and does not measure/do,
- high-level architecture/workflow,
- requirements and platform/tool prerequisites,
- installation,
- quick start,
- full important command reference,
- configuration and precedence,
- outputs/artifacts/metrics,
- project structure and module responsibilities,
- development commands,
- IDE/CI workflow when useful,
- troubleshooting,
- reproducibility/limitations,
- attribution/license.

Adapt to the project. Do not add empty headings just to match a template.

## Command accuracy

Every documented command should match current code/tooling. Verify:

- executable/module name,
- flag spelling and placement,
- path casing,
- config path,
- platform-specific activation syntax,
- expected output location.

Do not document a command as verified unless it was actually run; otherwise present it
as the intended command based on code/config.

## Architecture documentation

Explain responsibility boundaries and data/control flow, not only filenames. Diagrams
should reflect real calls/dependencies and stay simple enough to maintain.

## Examples

Examples should be copy-pasteable, minimal, and safe. Clearly label:

- expensive/cloud/GPU operations,
- destructive commands,
- example benchmark numbers,
- placeholders users must replace.

Never put real secrets, private keys, access tokens, or confidential endpoints in docs.

## Benchmark/performance documentation

When reporting measurements:

- state hardware/environment when known,
- state model/config/workload,
- label numbers as an example run,
- distinguish wall time from model/server timing,
- avoid universal claims from one environment.

## Troubleshooting

Prefer symptom → likely cause → verification → safe fix. Include exact evidence commands
when they are stable and non-destructive.

## Final review

Before finishing documentation:

- compare paths/filenames against repository tree,
- compare commands against CLI/Makefile/pyproject,
- compare config examples against parser/schema,
- remove stale claims,
- ensure a new developer can follow the happy path without chat history.
