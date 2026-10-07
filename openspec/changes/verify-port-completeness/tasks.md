## 1. Inventory

- [x] 1.1 List every function in the pinned C source (`tests/reference/c_inventory.py` -> `docs/about/c-inventory.txt`, 653 functions)
- [x] 1.2 Review the 49 functions not found by name: 48 ported in another form, 1 platform gap (Windows wildcards); see `assessment.md`
- [x] 1.3 Run the existing suite under `coverage.py` with branch coverage; list Python branches never reached
  - Result 2026-10-07: 96% overall (5489 statements, 181 missed; 2340 branches, 155 partly taken). pytest suite (627 passed) plus a six-season CLI sample (1915, 1950, 1976, 1998, 2007, 2022), worker processes included. Per-file gaps: box.py 32 lines, cli.py 25, parse.py 20, game.py 12, cwbox.py 13, cwgame.py 9; events.py 6.

## 2. cwevent deep verification

- [ ] 2.1 Test every `-f`/`-x` field and option combination against the C tool on a mixed-era sample, tests first
- [ ] 2.2 Sweep every available season 1871-2025 and record zero-difference results or findings
- [~] 2.3 Add synthetic and fuzzed games targeting unreached branches from 1.3
  - Play parser done 2026-10-07: `tests/test_parse_targeted_differential.py` (hand-built plays vs the C parser, all agree) reaches every previously unreached `parse.py` line except 184 (read past end of play text) and 1103/1105 (final default batted-ball rule, which the C also runs but an earlier rule already fills in). Left as faithful mirrors of the C; to confirm unreachable or reach them.
  - Still to do: unreached lines in box.py, cli.py, game.py, cwbox.py, cwgame.py, events.py (77->79, 82->84, 801, 825, 842-845).

## 3. Other tools

- [ ] 3.1 Repeat 2.1-2.3 for cwgame, then cwbox, then cwdaily, cwsub, cwcomment

## 4. Performance and wrap-up

- [ ] 4.1 Record single-core and parallel timings with core count for each tool in `docs/about/verification.md`
- [ ] 4.2 Record the owner's decision on single-core speed as an ADR
- [ ] 4.3 Run `uv run pytest`, ruff and mypy; inspect the diff; open a PR
- [ ] 4.4 Port or explicitly omit Windows wildcard expansion (`cwtools_process_filespec`), test first
- [ ] 4.5 Add an upstream-drift test: inventory a newer Chadwick and fail on C functions with no Python counterpart
