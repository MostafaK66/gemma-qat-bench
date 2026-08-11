# Prepare a Commit (Without Mutating Git State)

Use this prompt to prepare and review a clean commit scope without staging, committing, or pushing.

## Task

Prepare a commit for: `<change description>`

## Required workflow

1. Read `AGENTS.md`, `llms.txt`, and `.github/skills/version-control/SKILL.md`.
2. Inspect current branch and repository state:
   - current branch
   - `git status`
   - relevant unstaged diff (`git diff`)
   - relevant staged diff (`git diff --cached`)
3. Determine intended commit scope from the user request.
4. Distinguish files into:
   - recommended for commit
   - intentionally excluded unrelated files
   - untracked/generated/runtime artifacts requiring explicit user decision
5. Confirm repository quality gates relevant to the change and report results that were actually executed.
6. Propose an exact commit file list and a concise commit message.
7. Report any risks, assumptions, or missing verification.
8. STOP.

## Authorization boundary (strict)

`prepare-commit` is preparation and review only.

It does **not** authorize:

- `git add`
- staging or unstaging
- `git commit` or amend
- `git push`
- `git rebase`
- `git reset`
- `git restore`
- `git clean`
- branch deletion
- history rewriting

Any Git mutation requires separate explicit user authorization.

## Expected output

- current branch
- intended change scope
- files recommended for inclusion
- files intentionally excluded
- untracked/generated files needing user decision
- quality gates and actual results
- proposed commit message
- remaining risks/assumptions
