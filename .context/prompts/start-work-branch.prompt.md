# Start a Working Branch Safely

Use this prompt to create and switch to a new local working branch from a validated base branch before beginning implementation.

## Task

Start work branch from `<base-branch>` with either:

- explicit branch name: `<new-branch-name>`
- work description only: `<work-description>`

Optional explicit operations (only when requested):

- synchronize local base to latest remote base
- publish/push new branch

## Required loading

1. `AGENTS.md`
2. `llms.txt`
3. `.github/skills/version-control/SKILL.md`

## Required workflow

determine requested work
↓
determine base branch
↓
determine requested/proposed branch name
↓
inspect current Git state
↓
protect tracked/staged/untracked work
↓
verify base branch exists
↓
inspect local base vs remote base when relevant
↓
base synchronization needed?
├── no -> continue
└── yes
↓
explicitly authorized?
├── no -> STOP/report
└── yes -> safe synchronization only
↓
verify proposed branch does not already exist locally
↓
inspect same-named remote branch when relevant
↓
create new local working branch
↓
verify new branch tip/base relationship
↓
verify unrelated work remains intact
↓
push only if explicitly requested
↓
report ready-for-development state

## Parameter handling

- Base branch: required.
- New branch name: optional when user supplies it explicitly.
- Work description: optional when user supplies only intent.
- Base synchronization: optional, only when explicitly requested.
- Branch publication/push: optional, only when explicitly requested.

## Branch naming rules

- If the user gives an explicit valid branch name, use it exactly.
- If the user gives only a work description:
  - inspect repository evidence for naming conventions,
  - do not invent a convention not supported by repository evidence,
  - propose a concise name,
  - if multiple names are reasonable, ask before creating the branch.

## Existing-branch protection

Before creating the branch, verify whether it already exists:

- locally,
- remotely when remote state is relevant.

If it exists:

- do not overwrite or force-create,
- report what exists,
- stop unless the user explicitly asked to resume/reuse that branch.

## Authorization boundaries

A request to create a branch from a base authorizes:

- read-only Git inspection,
- switching to the validated base branch when safe,
- creating the requested new local branch,
- switching to the new branch.

It does **not** authorize:

- base branch updates (`pull`, `merge`, `rebase`, `reset`, `restore`),
- `stash` or `clean`,
- commit/amend,
- push/upstream creation,
- branch deletion,
- history rewriting.

Base synchronization and branch publication require explicit user intent.

## Working-tree safety

Preserve:

- tracked local changes,
- staged changes,
- unrelated untracked files.

Do not automatically stash, reset, restore, clean, or discard work.

An unrelated untracked path may remain when repository evidence shows branch operations will not overwrite it.

## Base synchronization safety

If local base is behind its remote counterpart:

- do not silently update,
- report current local/remote relationship,
- synchronize only when explicitly requested.

When synchronization is explicitly requested:

- prefer safe fast-forward-only behavior when applicable,
- never silently rebase or rewrite base history,
- if local/remote base diverged, stop and report instead of choosing reconciliation automatically.

## Post-creation verification

After creating the branch, verify:

- current branch is the requested new branch,
- branch tip is based on intended base commit,
- no unintended tracked/staged changes appeared,
- unrelated untracked files remain intact,
- repository state is understood.

Do not push automatically.

If push/publication is explicitly requested, treat it as a separate authorized step and verify intended remote/upstream.

## Expected output

- original branch
- requested work description
- base branch
- local base commit
- remote base commit when inspected
- base ahead/behind state
- whether synchronization was required
- whether synchronization was authorized/performed
- requested or proposed branch name
- whether that branch already existed locally/remotely
- new branch creation result
- new branch tip
- push/upstream result, only if explicitly requested
- unrelated/untracked work preserved
- final `git status --short --branch`
- whether repository is READY FOR DEVELOPMENT
