# Tasks: verify-port-completeness

## 1. Inventory

- [x] 1.1 List every function in the pinned C source (`tests/reference/c_inventory.py` -> `docs/about/c-inventory.txt`, 653 functions)
- [x] 1.2 Review the 49 functions not found by name: 48 ported in another form, 1 platform gap (Windows wildcards); see `assessment.md`
- [x] 1.3 Run the existing suite under `coverage.py` with branch coverage; list Python branches never reached
  - Result 2026-10-07: 96% overall (5489 statements, 181 missed; 2340 branches, 155 partly taken). pytest suite (627 passed) plus a six-season CLI sample (1915, 1950, 1976, 1998, 2007, 2022), worker processes included. Per-file gaps: box.py 32 lines, cli.py 25, parse.py 20, game.py 12, cwbox.py 13, cwgame.py 9; events.py 6.

- [ ] 1.4 C branch inventory: run the gcov-instrumented C tools over the corpus (`tests/reference/gcov_run.py`), list C lines and branches reached and not reached, map each to Python or a documented omission; add to the coverage matrix

## 2. cwevent deep verification

- [ ] 2.1 Test every `-f`/`-x` field and option combination against the C tool on a mixed-era sample, tests first
- [ ] 2.2 Sweep every available season 1871-2025 and record zero-difference results or findings
- [~] 2.3 Add synthetic and fuzzed games targeting unreached branches from 1.3
  - Play parser done 2026-10-07: `tests/test_parse_targeted_differential.py` (hand-built plays vs the C parser, all agree) reaches every previously unreached `parse.py` line except 184 (read past end of play text) and 1103/1105 (final default batted-ball rule, which the C also runs but an earlier rule already fills in). Left as faithful mirrors of the C; to confirm unreachable or reach them.
  - events.py reviewed 2026-10-07: `_c_format` and `_render` were never called anywhere (src, tests, docs), so removed; 230 event/CLI differential tests pass. The cache checks in `future_runs`/`truncated` (77, 82) and the left-justified `%d` formatter (801) cannot be reached because each value is read once per event and no field uses that format; kept as harmless.
  - 2026-10-07, three subagents (own worktrees, results re-run and merged by me): `test_cli_targeted_differential.py` (cli.py/tools.py: every listed line hit), `test_game_targeted_differential.py` (game.py/cwgame.py: all but 4 lines), `test_box_targeted_differential.py` (box.py/cwbox.py: 42 of 54 hit). 409 targeted tests pass, 17 skipped on purpose (cwbox -S crashes in C). Lint clean.
  - Unreachable or defensive, left in place as faithful to the C: game.py 286; cwgame.py 45, 168; box.py 426; cwbox.py 97, 117, 290, 374, 380 (reasons in the test file headers and the agent reports: guarded earlier, or inputs the library never produces).
  - Open follow-up: a `line` record with 50 innings matches in plain text but `cwbox -X` output differs from C (49 innings match). Probably the C array overflow; confirm.

## 3. Other tools

- [ ] 3.1 Repeat 2.1-2.3 for cwgame, then cwbox, then cwdaily, cwsub, cwcomment

## 4. Performance and wrap-up

- [ ] 4.1 Record single-core and parallel timings with core count for each tool in `docs/about/verification.md`
- [ ] 4.2 Record the owner's decision on single-core speed as an ADR
- [ ] 4.3 Run `uv run pytest`, ruff and mypy; inspect the diff; open a PR
- [ ] 4.4 Port or explicitly omit Windows wildcard expansion (`cwtools_process_filespec`), test first
- [ ] 4.5 Add an upstream-drift test: inventory a newer Chadwick and fail on C functions with no Python counterpart
