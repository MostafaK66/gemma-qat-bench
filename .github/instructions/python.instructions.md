---
applyTo: "src/**/*.py"
---

# Production Python instructions

- Follow `AGENTS.md` and `.github/skills/python-engineering/SKILL.md`.
- Keep each module focused on one responsibility and preserve existing architectural boundaries.
- Keep CLI/API/job entry points thin; move substantive logic into focused application/domain modules.
- Use type hints at public and important internal boundaries.
- Prefer `pathlib.Path`, immutable/validated configuration, explicit dependencies, and domain-specific exceptions.
- Isolate network, subprocess, filesystem, GPU, clock, database, and cloud side effects behind small testable seams when practical.
- Avoid mutable global state, generic `utils.py` dumping grounds, vague names, broad exception swallowing, and hidden cleanup behavior.
- Use package logging for diagnostics; `print` is only for intentional user-facing CLI output.
- Preserve public behavior unless the task explicitly requests a breaking change.
- Any behavior change must be accompanied by appropriate tests and documentation/config updates when affected.
