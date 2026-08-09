---
applyTo: "README.md,docs/**/*.md,.context/**/*.md,configs/**/*.toml"
---

# Documentation and configuration instructions

- Follow `AGENTS.md` and `.github/skills/documentation/SKILL.md` for documentation changes.
- Ground documentation in the actual code, CLI help, config parser, tests, scripts, and CI.
- Keep commands copy-pasteable and filenames/paths/flags exact.
- Do not invent supported platforms, benchmark numbers, API behavior, requirements, or configuration keys.
- Clearly label example benchmark results and environment-dependent behavior.
- Explain dangerous, destructive, expensive, cloud, or GPU operations before presenting commands.
- Never place credentials, tokens, private keys, secrets, or sensitive environment details in tracked docs/config examples.
- For TOML changes, preserve validation invariants and update tests/docs if user-visible behavior changes.
