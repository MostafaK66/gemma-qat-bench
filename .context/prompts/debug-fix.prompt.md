# Debug and Fix a Defect

Use this prompt for a failing test, runtime error, regression, incorrect output, or
unexpected behavior.

## Problem

- **Observed behavior:** `<exact error/output>`
- **Expected behavior:** `<expected>`
- **Reproduction:** `<command/input/environment>`
- **Recent change:** `<if known>`

## Required workflow

1. Read `AGENTS.md`, `llms.txt`, and `.context/skills/debugging/SKILL.md`.
2. Reproduce the problem or inspect the strongest available evidence before changing
   code.
3. Separate symptoms from root cause.
4. Form the smallest plausible hypotheses and test them with code/tests/logs/config.
5. Trace the data/control path across the relevant boundary; do not patch only the final
   symptom if the fault originates earlier.
6. Add a failing regression test when practical.
7. Implement the smallest root-cause fix.
8. Run the focused test, then the broader quality suite.
9. Check error handling, resource cleanup, retries/timeouts, and observability when
   relevant.
10. Do not claim a root cause unless evidence supports it.

## Deliverable

- **Root cause** — confirmed or explicitly labeled most-likely hypothesis
- **Evidence**
- **Fix**
- **Regression coverage**
- **Commands/checks run**
- **Remaining risk / follow-up**
