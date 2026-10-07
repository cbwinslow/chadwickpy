## 1. Inventory

- [ ] 1.1 List every function in the pinned C source for the six tools and their library code (`ctags`), saved as `tests/reference/c_inventory.txt`
- [ ] 1.2 Write the coverage matrix `docs/about/coverage-matrix.md`: C function -> Python function, or "omitted: reason"; verify no row is blank
- [ ] 1.3 Run the existing suite under `coverage.py` with branch coverage; list Python branches never reached

## 2. cwevent deep verification

- [ ] 2.1 Test every `-f`/`-x` field and option combination against the C tool on a mixed-era sample, tests first
- [ ] 2.2 Sweep every available season 1871-2025 and record zero-difference results or findings
- [ ] 2.3 Add synthetic and fuzzed games targeting unreached branches from 1.3

## 3. Other tools

- [ ] 3.1 Repeat 2.1-2.3 for cwgame, then cwbox, then cwdaily, cwsub, cwcomment

## 4. Performance and wrap-up

- [ ] 4.1 Record single-core and parallel timings with core count for each tool in `docs/about/verification.md`
- [ ] 4.2 Record the owner's decision on single-core speed as an ADR
- [ ] 4.3 Run `uv run pytest`, ruff and mypy; inspect the diff; open a PR
