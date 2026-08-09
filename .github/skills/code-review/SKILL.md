---
name: code-review
description: Perform high-signal review of Python changes, branches, or pull requests. Use when checking correctness, safety, architecture, tests, compatibility, performance, documentation, and merge readiness.
---

# Code Review

## Review mindset

Review for defects and maintainability risks, not stylistic preference. A useful finding
has a concrete location, plausible impact, and actionable recommendation.

## Priority order

1. correctness / data loss,
2. security / unsafe operations,
3. broken public contracts or compatibility,
4. resource lifecycle / concurrency,
5. error handling / observability,
6. architecture / coupling,
7. missing tests / weak regression protection,
8. performance / reproducibility,
9. maintainability / readability,
10. style.

## Required context

Inspect:

- changed code,
- surrounding callers/contracts,
- relevant tests,
- config and CLI/API behavior,
- exception/logging paths,
- README/docs if behavior is user-visible,
- CI/tool configuration when dependencies/tooling change.

Do not review only the diff when correctness depends on surrounding code.

## What to look for

### Correctness

- wrong branch conditions,
- missing boundary cases,
- incorrect defaults/precedence,
- stale state,
- wrong units/types,
- incomplete parsing/serialization,
- accidental behavior changes.

### Safety

- secrets in code/logs,
- shell injection,
- unsafe file deletion,
- destructive defaults,
- unvalidated untrusted input,
- swallowed exceptions.

### Lifecycle

- subprocesses not stopped,
- files/sockets/sessions not closed,
- cleanup missing on exceptions,
- retries without bounds/backoff,
- timeout behavior that can hang.

### Architecture

- business logic moved into CLI/API adapter,
- infrastructure imported into pure domain code,
- duplicated responsibilities,
- generic utility dumping grounds,
- circular or hidden dependencies,
- new abstractions without a real boundary.

### Tests

- changed behavior lacks coverage,
- tests rely on real network/GPU unnecessarily,
- regression scenario missing,
- assertions coupled to implementation details,
- valid tests weakened to pass.

### Documentation

Check whether commands, flags, config, output, requirements, project tree, or examples
became stale.

## Finding format

Each meaningful finding should include:

- severity: critical/high/medium/low,
- location,
- problem,
- impact/failure scenario,
- recommended fix.

Do not invent findings. If the change looks sound, say so and note any verification or
integration risk that remains.

## Merge readiness

A change is not merge-ready when an applicable quality gate is failing, behavior is
untested, docs/config are materially stale, or a known correctness/safety issue remains.
