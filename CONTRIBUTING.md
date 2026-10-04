# Contributing

Thanks for helping. Every change goes through a pull request that the maintainer approves.

1. Fork, branch, `uv sync`, then `uv run pytest`, `uvx ruff check .`, `uvx ruff format --check .`,
   `uvx mypy --strict src`.
2. **The port stays a translation of Chadwick's C.** Fix a difference by reading the C and
   mirroring it; never tune a rule to make an output match. Name Chadwick's C function in
   the docstring when you port or change one.
3. Behaviour changes need a test that compares with real Chadwick output (see `tests/`).
4. Use [Conventional Commits](https://www.conventionalcommits.org/) in the PR title
   (`fix:`, `feat:`, `docs:`, `perf:`, `chore:`): versions and the changelog are generated from them.
5. No new runtime dependencies (the package is standard-library only).
6. By contributing you agree your work is licensed AGPL-3.0-or-later.
