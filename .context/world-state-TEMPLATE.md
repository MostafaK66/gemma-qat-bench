# World State — <project name>
> **Important:** This template is only for creating a new `.context/world-state.md`.
> Before copying it, check whether `.context/world-state.md` already exists.
> Never overwrite an existing world-state file with this template, because the existing
> file may contain important local session context that is intentionally gitignored and
> cannot be recovered from Git.
>
> Last updated: <YYYY-MM-DD HH:MM timezone>
> Local working context — use this template only when `.context/world-state.md` does not already exist.

## Active work

- **Branch:** `<branch-name>`
- **Goal:** `<one-sentence current objective>`
- **Status:** `<not started / investigating / implementing / verifying / blocked / done>`
- **Requested outcome:** `<what must be true when this task is complete>`

## Current understanding

### Confirmed facts
- `<fact supported by code, tests, logs, docs, or user evidence>`

### Assumptions
- `<temporary assumption that still needs confirmation>`

### Unknowns
- `<important unanswered question>`

## Scope

### In scope
- `<module/file/behavior>`

### Out of scope
- `<explicitly excluded work>`

## Architecture / design decisions

| Decision | Rationale | Date |
| --- | --- | --- |
| `<decision>` | `<why this was chosen>` | `<YYYY-MM-DD>` |

## Current implementation status

| Area | Status | Notes |
| --- | --- | --- |
| Source | `<status>` | `<files/modules>` |
| Tests | `<status>` | `<coverage / failing tests>` |
| Config | `<status>` | `<changes>` |
| Docs | `<status>` | `<changes>` |
| CI / tooling | `<status>` | `<changes>` |

## Verification actually performed

```text
<command> → <result>
<command> → <result>
```

Do not write "passed" unless the command was actually run successfully.

## Environment / runtime state

- **Python/runtime:** `<version>`
- **Platform:** `<OS / local / remote>`
- **GPU/accelerator:** `<if relevant>`
- **External services:** `<if relevant>`
- **Important config:** `<non-secret values only>`

## Known blockers / risks

- `<blocker or risk, impact, and what resolves it>`

## Recent meaningful changes

### <YYYY-MM-DD> — <short title>
- `<what changed>`
- `<why>`
- `<verification>`

## Next step

1. `<single most useful next action>`
2. `<following action if known>`

## Before merge / completion checklist

- [ ] Requested behavior is complete.
- [ ] Relevant tests added/updated.
- [ ] Existing tests pass.
- [ ] Lint/type checks pass or exceptions are documented.
- [ ] Config/examples updated if needed.
- [ ] README/help/docs updated if needed.
- [ ] No secrets or runtime artifacts are staged.
- [ ] Final handoff states evidence, assumptions, and remaining risks.
