# Constitution for IDE/Agent Usage

- Obey repository instructions (`.github/copilot-instructions.md`, `SPEC.md`, `README.md`, `DISCLAIMER.md`).
- Stay within the documented scope: this is a prototype; do not add execution engines or dashboards unless requested.
- Default to ASCII; avoid introducing non-ASCII characters unless necessary.
- Prefer `apply_patch` for single-file edits; avoid destructive commands and do not revert user changes.
- Keep changes minimal and explain rationale succinctly; add comments only when code is non-obvious.
- Do not commit secrets or confidential data; assume inputs are non-production.
- When adding CLIs or scripts, keep dependencies light and outputs deterministic where possible.
- Run relevant checks/tests when added; otherwise state what was not run and why.
- Ask for confirmation before large structural changes or new dependencies.
- Append to evidence logs; do not overwrite prior entries.