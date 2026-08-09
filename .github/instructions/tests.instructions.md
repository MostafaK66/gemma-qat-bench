---
applyTo: "tests/**/*.py"
---

# Test instructions

- Follow `AGENTS.md` and `.github/skills/testing/SKILL.md`.
- Keep unit tests deterministic, fast, and offline by default.
- Test observable behavior and meaningful boundaries rather than private implementation details.
- Mirror important source-module responsibilities with corresponding `test_<module>.py` coverage.
- Prefer small fakes/fixtures and injected dependencies for HTTP, subprocess, GPU, clock, downloads, filesystem, database, and cloud behavior.
- Cover happy paths, validation/boundary cases, meaningful failures, cleanup/lifecycle, and regressions.
- A bug fix should add a regression test when practical.
- Do not weaken valid assertions or delete tests merely to make new code pass.
- Avoid real sleeps and execution-order dependence.
- Keep real network/GPU/cloud tests explicitly separated as integration/e2e tests when needed.
