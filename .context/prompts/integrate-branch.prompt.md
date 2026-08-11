# Integrate a Working Branch Safely

Use this prompt to integrate a completed source branch into a target branch with explicit safety checks and clear authorization boundaries.

## Task

Integrate: `<source-branch>` into `<target-branch>`

Optional explicit operations (only when requested):

- push target branch
- delete source branch locally
- delete source branch remotely

## Required workflow

1. Read `AGENTS.md`, `llms.txt`, and `.github/skills/version-control/SKILL.md`.
2. Determine source branch from user request and repository evidence.
3. Determine target branch from user request and repository evidence.
4. Inspect repository state:
   - current branch
   - `git status`
   - relevant diffs
   - presence of unrelated local work
5. Protect local/unrelated work before integration actions.
6. Inspect source-vs-target differences and commit relationship.
7. Inspect remotes and fetch current remote state when remote operations are relevant.
8. Verify branch readiness and run applicable repository quality gates when practical.
9. Perform integration using the requested strategy.
10. If conflicts occur:
    - inspect both branch intents
    - resolve only when repository evidence makes intended combined behavior clear
    - stop and ask the user when conflict decisions are ambiguous
11. Inspect resulting diff and rerun relevant quality gates.
12. Verify integration result.
13. Push only if explicitly authorized.
14. Delete local source branch only if explicitly authorized and after verifying no unique work would be lost.
15. Delete remote source branch only if explicitly authorized and after verifying no unique work would be lost.
16. Verify final repository state and report results.

## Conflict decision boundary

If a conflict requires ambiguous business, architecture, security, data, or behavioral decisions that cannot be determined from repository evidence, stop and ask the user.

## Authorization boundaries

Do not assume:

- target branch is `master` or `main`
- push is authorized
- local branch deletion is authorized
- remote branch deletion is authorized

These must be explicitly requested.

## Expected output

- source branch
- target branch
- integration strategy actually used
- commits involved (if relevant)
- conflicts encountered and resolutions
- quality gates actually executed
- push result (if performed)
- local branch deletion result (if performed)
- remote branch deletion result (if performed)
- final `git status`
- remaining unrelated/untracked work
