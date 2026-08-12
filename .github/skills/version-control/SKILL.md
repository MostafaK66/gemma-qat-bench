---
name: version-control
description: Safely inspect, prepare, integrate, and report Git work while protecting unrelated local changes and requiring explicit authorization for mutations.
---

# Version Control

Use this skill for Git and branch workflows, including change preparation, commit preparation, branch integration, merge conflict handling, push coordination, and branch cleanup.

## Scope and safety model

- Treat Git mutations as explicit actions that require user intent.
- Preserve unrelated work in the working tree and index.
- Keep local and remote risk visible before destructive or irreversible operations.
- Never claim a Git action, quality gate, or verification passed unless it was actually executed and confirmed.

## 1) Repository inspection before mutation

Before proposing or performing Git mutations, inspect current repository state.

Minimum inspection checklist:

1. current branch (`git branch --show-current` or `git status --short --branch`)
2. full status (`git status`)
3. unstaged diff relevant to task (`git diff` and optionally path-limited diff)
4. staged diff relevant to task (`git diff --cached`)
5. recent history/context (`git log --oneline --decorate --max-count <n>` as needed)
6. remotes when remote operations are relevant (`git remote -v`)

Classify what you see:

- tracked and clean files
- modified tracked files
- staged files
- untracked files
- ignored files
- generated/runtime artifacts
- unrelated user changes

Never assume all files shown by `git status` belong to the current task.

Read-only inspection commands are normally safe, including:

- `git status`
- `git diff`
- `git diff --cached`
- `git log`
- `git branch`
- `git remote`
- `git show`
- `git grep`

## 2) Staging and commits

- Stage only files explicitly confirmed to belong to the requested change.
- Inspect intended content before staging.
- Inspect staged content before committing.
- Keep commits focused and atomic.
- Do not mix unrelated cleanup into the same commit.
- Never claim a file is included in a commit unless verified from staged content and commit output.
- Prefer meaningful commit messages that describe intent and effect.
- Use Conventional Commits when compatible with repository convention; do not override an established repository-specific convention.

Important authorization boundary:

- Commit preparation does not authorize `git add` or `git commit`.
- Staging and committing require explicit user intent.

## 3) Protect existing work

Never discard local work without explicit user authorization.

Do not run destructive operations such as:

- `git reset --hard`
- destructive `git restore`
- destructive checkout operations
- `git clean`
- history rewriting
- forced branch replacement

unless explicitly requested and impact is understood.

Treat untracked files with extra care. Never assume an untracked file should be staged, deleted, restored, ignored, or committed merely because it appears in `git status`.

## 4) Branch operations

Support safe workflows for:

- identifying working and target branches
- creating and switching branches
- fetching remote state and updating branch info
- comparing source and target branches
- merging/integrating branches
- pushing branches
- branch cleanup

Do not assume target branch is `master` or `main`; determine it from user request and repository evidence.

Do not switch branches if doing so risks overwriting or losing local work.

### 4.1) Safe branch-start workflow

Before creating a new working branch, always:

1. inspect current branch
2. inspect `git status`
3. classify tracked, staged, untracked, and unrelated work
4. determine requested base branch from user request and repository evidence
5. verify base branch exists locally
6. inspect remotes when remote state is relevant
7. verify switching to/inspecting base cannot overwrite unrelated local work
8. verify requested new branch does not already exist locally
9. inspect whether same-named remote branch exists when relevant
10. create branch only when base and new branch name are unambiguous

When the user provides an explicit valid branch name, use it exactly.

When the user provides only a work description:

- inspect repository naming conventions when evidence exists
- propose a concise branch name
- if multiple names are plausible, stop and ask the user before creating the branch

Do not overwrite or force-recreate existing local/remote branches.

If branch exists and request did not explicitly authorize resuming/reusing it, stop and report.

### 4.2) Action boundaries for branch start

Treat these as separate actions with separate authorization:

- inspecting a base branch
- synchronizing a base branch
- creating a new local branch
- publishing/pushing a new branch

Request example `Create feature-x from master` authorizes:

- read-only Git inspection
- switching to validated base when safe
- creating requested new local branch
- switching to the new local branch

It does **not** authorize:

- updating the base branch
- `pull`, `merge`, `rebase`, `reset`, `restore`
- `stash` or `clean`
- `commit` or amend
- `push` or upstream creation
- branch deletion
- history rewriting

### 4.3) Base synchronization safety

If local base is behind its remote counterpart, do not silently update it.

Report local-vs-remote base state and proceed without synchronization unless user explicitly requested latest remote base.

When synchronization is explicitly requested:

- use only a safe strategy supported by repository state and explicit intent
- prefer fast-forward-only synchronization when applicable
- never silently rebase or rewrite base history
- if local and remote base diverged, stop and report rather than choosing reconciliation automatically

### 4.4) Working-tree protection during branch start

Before switching/creating branches, preserve:

- tracked local changes
- staged changes
- unrelated untracked files

Do not automatically:

- stash
- reset/restore
- clean
- discard local work

An unrelated untracked path may remain if repository evidence shows it will not be overwritten by branch operations.

### 4.5) Branch creation and verification

Create the new local branch only after checks pass, for example:

- `git switch -c <new-branch> <base-branch>`

Do not use force options.

After creation, verify:

- current branch is requested new branch
- new branch tip is based on intended base commit
- no unrelated tracked/staged work was lost or unexpectedly changed
- unrelated untracked files remain intact
- repository status is understood

Do not push automatically; push/publication is separately authorized.

## 5) Integration readiness workflow

Before integrating source branch into target branch:

1. verify intended source branch
2. verify intended target branch
3. inspect current status and local changes
4. identify unrelated local work
5. inspect remotes when remote operations are requested
6. fetch remote state when appropriate
7. determine source/target ahead-behind relationship
8. verify source branch readiness
9. run repository quality gates when practical

For this repository, normal quality gates are:

- `python -m pytest`
- `python -m ruff check src tests`
- `python -m mypy`

Never claim these passed unless actually executed successfully.

## 6) Merge conflicts

You may resolve conflicts when repository evidence makes intended combined behavior clear.

For each conflict:

1. inspect the conflicting file content and conflict markers
2. determine target-branch intent
3. determine source-branch intent
4. preserve compatible intent from both sides
5. remove markers only after selecting intended combined result
6. maintain coherent architecture and public behavior

Do not blindly choose `ours` or `theirs`.

Use relevant companion skills when needed:

- `.github/skills/python-engineering/SKILL.md`
- `.github/skills/testing/SKILL.md`
- `.github/skills/debugging/SKILL.md`
- `.github/skills/documentation/SKILL.md`

Stop and ask the user if conflict resolution depends on ambiguous product, architecture, data, security, or behavior decisions that cannot be inferred confidently from repository evidence.

After resolving conflicts:

- verify no conflict markers remain
- inspect resulting diff
- rerun relevant quality gates
- report exactly what was resolved

## 7) Push safety

- Do not push automatically unless explicitly requested.
- Before pushing, verify branch, remote, and local result.
- Avoid accidental force pushes.

Never use:

- `git push --force`
- `git push --force-with-lease`

unless user explicitly requests history rewriting and understands impact.

## 8) Branch cleanup safety

Deleting a branch is a separate destructive action.

Only delete local/remote branches when request explicitly includes cleanup.

Before deleting a working branch after integration:

1. verify merge completed successfully
2. verify target branch contains intended changes
3. verify target was pushed when remote integration was requested
4. verify deleting source branch will not drop unique commits/work

For local cleanup, prefer safe deletion semantics where possible.

If `git branch -d <source>` fails, do not automatically escalate to `git branch -D <source>`.

Before any alternative cleanup step, verify independently:

1. target contains the entire source branch history intended for integration
2. source has zero unique commits relative to target
3. remote target contains the integrated source tip when remote integration was part of the workflow

Then inspect the source branch's configured upstream.

When repository evidence confirms cleanup is safe, cleanup was explicitly authorized, and refusal is caused by a stale source upstream that does not contain the source branch's latest commits, it is acceptable to remove only that source-branch upstream association:

- `git branch --unset-upstream <source>`

Afterward, retry ordinary safe deletion:

- `git branch -d <source>`

If safe deletion still fails after the verified upstream adjustment, stop and report the exact Git reason. Do not force-delete automatically.

Never infer remote branch deletion from a merge-only request.

Remote source-branch deletion is separately authorized and should occur only after integration and remote-target verification are complete.

## 9) Rebase/history rewriting

Treat rebase, amend, squash, shared-history cherry-picks, and other history rewriting as high-risk.

- Do not perform them only to make history look cleaner.
- Never rewrite shared history without explicit user intent.

## 10) Pull request preparation

When preparing a PR summary:

- summarize purpose and scope
- highlight important files/components changed
- report verification actually performed
- mention known risks/assumptions
- note intentionally excluded work when relevant
- never expose secrets/sensitive information

## 11) Final Git handoff template

After Git work, clearly report:

- source branch
- target branch
- files/change scope involved
- commits created (if any)
- merge result
- conflicts resolved (if any)
- quality gates actually run
- push result (if requested)
- local branch cleanup (if requested)
- remote branch cleanup (if requested)
- remaining untracked/unrelated changes
- follow-up actions or risks
