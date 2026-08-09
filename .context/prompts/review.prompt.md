# High-Signal Code Review

Use this prompt to review a branch, diff, pull request, module, or proposed implementation.

## Review target

`<branch / PR / files / diff>`

## Required review order

Read `AGENTS.md` and `.github/skills/code-review/SKILL.md`, then inspect the changed
code plus the surrounding contracts and tests.

Prioritize findings by:

1. correctness / data loss,
2. security / unsafe operations,
3. broken public contracts,
4. resource lifecycle / concurrency,
5. error handling / observability,
6. architecture / coupling,
7. missing or weak tests,
8. performance / reproducibility,
9. maintainability,
10. style.

## Review rules

- Report only concrete findings supported by the code.
- Include file/line context and impact.
- Explain a realistic failure scenario where useful.
- Distinguish blocking defects from optional improvements.
- Check whether tests actually cover changed behavior.
- Check whether README/config/help text must change.
- Check for secrets, local paths, generated artifacts, and accidental debug code.
- Do not demand abstraction or style churn without a practical benefit.
- If there are no meaningful findings, say so clearly and mention residual testing risk.

## Output

For each finding:

- **Severity:** critical / high / medium / low
- **Location:** file + line/area
- **Problem**
- **Impact**
- **Recommended fix**

Then provide a short overall assessment of architecture, tests, and merge readiness.
