# Tasks: verify-port-completeness

## 1. Inventory

- [x] 1.1 List every function in the pinned C source (`tests/reference/c_inventory.py` -> `docs/about/c-inventory.txt`, 653 functions)
- [x] 1.2 Review the 49 functions not found by name: 48 ported in another form, 1 platform gap (Windows wildcards); see `assessment.md`
- [x] 1.3 Run the existing suite under `coverage.py` with branch coverage; list Python branches never reached
  - Result 2026-10-07: 96% overall (5489 statements, 181 missed; 2340 branches, 155 partly taken). pytest suite (627 passed) plus a six-season CLI sample (1915, 1950, 1976, 1998, 2007, 2022), worker processes included. Per-file gaps: box.py 32 lines, cli.py 25, parse.py 20, game.py 12, cwbox.py 13, cwgame.py 9; events.py 6.

- [ ] 1.4 C branch inventory: run the gcov-instrumented C tools over the corpus (`tests/reference/gcov_run.py`), list C lines and branches reached and not reached, map each to Python or a documented omission; add to the coverage matrix

## 2. cwevent deep verification

- [~] 2.1 Test every `-f`/`-x` field and option combination against the C tool on a mixed-era sample, tests first
  - Fields done 2026-10-07: `tests/test_event_field_sweep.py` (378 tests, 36 s): each of the 97 standard and 67 extended fields requested alone, ASCII and fixed-width, plus 50 random subsets (half with synthesised rosters), on all 10 fixture files (every era and rule variant). All byte-identical to the real cwevent. Mutation check: breaking `FATE_RUNS_CT` makes 4 of them fail, so the sweep does detect a wrong field.
  - Options done 2026-10-07: `tests/test_event_option_sweep.py` (726 tests, 20 s): game selection (`-i` hit/miss, `-s`/`-e` on, before and after the game date, windows, id plus window) x formats (`-a`, `-n`, `-ft` and pairs) x field lists (`-f`, `-x`, both, all) x one or two files, plus `-d` with other options. stdout, stderr and exit status identical to the real cwevent. Malformed option values were already covered by `test_cli_differential` and `test_cli_targeted_differential`.
  - Still to do for 2.1: the field sweep on real seasons across eras instead of fixtures (feeds 2.2).
- [ ] 2.2 Sweep every available season 1871-2025 and record zero-difference results or findings
- [~] 2.3 Add synthetic and fuzzed games targeting unreached branches from 1.3
  - Play parser done 2026-10-07: `tests/test_parse_targeted_differential.py` (hand-built plays vs the C parser, all agree) reaches every previously unreached `parse.py` line except 184 (read past end of play text) and 1103/1105 (final default batted-ball rule, which the C also runs but an earlier rule already fills in). Left as faithful mirrors of the C; to confirm unreachable or reach them.
  - events.py reviewed 2026-10-07: `_c_format` and `_render` were never called anywhere (src, tests, docs), so removed; 230 event/CLI differential tests pass. The cache checks in `future_runs`/`truncated` (77, 82) and the left-justified `%d` formatter (801) cannot be reached because each value is read once per event and no field uses that format; kept as harmless.
  - 2026-10-07, three subagents (own worktrees, results re-run and merged by me): `test_cli_targeted_differential.py` (cli.py/tools.py: every listed line hit), `test_game_targeted_differential.py` (game.py/cwgame.py: all but 4 lines), `test_box_targeted_differential.py` (box.py/cwbox.py: 42 of 54 hit). 409 targeted tests pass, 17 skipped on purpose (cwbox -S crashes in C). Lint clean.
  - Unreachable or defensive, left in place as faithful to the C: game.py 286; cwgame.py 45, 168; box.py 426; cwbox.py 97, 117, 290, 374, 380 (reasons in the test file headers and the agent reports: guarded earlier, or inputs the library never produces).
  - Open follow-up: a `line` record with 50 innings matches in plain text but `cwbox -X` output differs from C (49 innings match). Probably the C array overflow; confirm.

## 3. Other tools

- [~] 3.1 Repeat 2.1-2.3 for cwgame, then cwbox, then cwdaily, cwsub, cwcomment
  - Fields done 2026-10-07: `tests/test_field_sweep_other_tools.py` (822 tests, 3 min): cwgame (85 standard + 97 extended), cwdaily (154), cwsub (25), cwcomment (10) fields each alone, ASCII with header and fixed-width, plus 10 random subsets per tool, on all 10 fixtures; stdout, stderr and exit status identical to the real tools. Mutation check: breaking one cwdaily helper fails 258 tests.
  - Options done 2026-10-07: `tests/test_option_sweep_other_tools.py` (1728 tests, 69 s: cwgame, cwdaily, cwsub, cwcomment x game selection x formats x field lists x one or two files) and `tests/test_cwbox_option_sweep.py` (96 tests: selection x text/XML x -q x files; XML `pb` attribute removed on both sides, SportsML excluded per ADR-002). All identical to the real tools in stdout, stderr and exit status.
  - Still to do for 3.1: cwbox content on real seasons (the whole-corpus run covers it), then synthetic games for the remaining unreached lines (done in 2.3 by the targeted tests).

## 4. Performance and wrap-up

- [ ] 4.1 Record single-core and parallel timings with core count for each tool in `docs/about/verification.md`
- [ ] 4.2 Record the owner's decision on single-core speed as an ADR
- [ ] 4.3 Run `uv run pytest`, ruff and mypy; inspect the diff; open a PR
- [ ] 4.4 Port or explicitly omit Windows wildcard expansion (`cwtools_process_filespec`), test first
- [x] 4.5 Add an upstream-drift test: inventory a newer Chadwick and fail on C functions with no Python counterpart
  - Done 2026-10-07, redesigned: the name lookup is too loose to detect drift (it counted a brand-new function as ported because its last word, `function`, appears in a docstring; 191 of the 603 name matches rest on generic words such as `help` or `cleanup`). Instead `tests/test_upstream_drift.py` compares a fingerprint of every C function (`docs/about/c-function-hashes.txt`, 653 functions, made by `python tests/reference/c_inventory.py --hashes CHECKOUT`) and names every function added, removed or changed. Checked against a doctored copy of the C source: one added, one renamed (added + removed) and one modified function are each reported. `.github/workflows/upstream-drift.yml` runs the whole suite weekly against the newest Chadwick.
- [~] 4.6 Parallel robustness on any machine (owner request 2026-10-07)
  - Done: `tests/test_parallel_start_methods.py` (7 tests): output identical to `-j 1` under `fork`, `spawn` and `forkserver` start methods and with `-j` 2, 5, 64, 100000 (capped at the file count). Existing: worker-count logic and affinity (`test_worker_count.py`), dead-worker fallback (`test_cli_parallel.py`).
  - To do: real runs restricted with `taskset` to 1-40 cores, output compared with C, timings recorded; decide whether auto mode should also honour a cgroup CPU quota (Docker `--cpus`, Kubernetes limits): `os.sched_getaffinity` and `process_cpu_count` do not see quotas, so on a 64-core host limited to 2 CPUs auto mode would start ~63 workers (slow and memory hungry, not wrong). Cannot be tested on this host (no `cpu.max`).
  - BUG FOUND AND FIXED 2026-10-07 (whole-corpus run, 1908 `cwbox`): on Linux (`fork`), parallel workers inherited the parent's stderr log handler, so every warning (e.g. "Sanity check fails for game ...") printed twice, the first copy early and out of order. stdout was never affected; `-j 1`, `spawn` and `forkserver` were correct. The C prints each once. Test first: `test_warnings_are_printed_once_and_in_order` (fails under fork before the fix, passes after); fix in `_worker_scorebook` (cli.py). The earlier start-method tests missed it because their data produced no warnings and the driver captured output instead of using the real stderr. This bug was present in the published 0.2.0 and 0.2.1.

