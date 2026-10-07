# chadwickpy — agent contract

Read `openspec/project.md` first. Contribution rules: `CONTRIBUTING.md`.

- Work through OpenSpec changes; use `superpowers:test-driven-development` for every fix.
- The port stays a translation of Chadwick's C (project.md invariants 1-3).
- Record decisions in `docs/DECISIONS.md`; update docs in the same change.
- Verification: `uv run pytest`, `uvx ruff check .`, `uvx ruff format --check .`, `uvx mypy --strict src`.
