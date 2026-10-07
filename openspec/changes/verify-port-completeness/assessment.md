# Port completeness assessment (2026-10-07)

Reference: Chadwick commit `c685ab5`. Method and counts: `docs/about/coverage-matrix.md`,
`docs/about/c-inventory.txt`, `tests/reference/c_inventory.py`.

## 1. C to Python (is anything in the C missing?)

653 C functions found. 603 match a Python definition by name; 1 is memory cleanup (not needed in
Python); 49 had no name match. Each of the 49 was resolved as follows.

| Group | Count | Finding | Evidence |
| --- | --- | --- | --- |
| Output-field functions (`cwevent_*`, `cwgame_*`, `cwdaily_*`, `cwcomment_*`, `cwsub_*`) | 44 | Ported. The C tools declare one function per output field; the port builds repeated fields (assist1..10, putout1..3, responsible_pitcher1..3, removed_runner1..3, home/visitor lob, ter, dp, tp, manager id) in loops or tables. Each field's label exists in the Python field table. | Field label found in `src/chadwickpy` for all 44; `-d` field list identical to the C tools for cwevent, cwgame, cwdaily, cwsub, cwcomment |
| `cw_pitch_strike_inplay`, `cwevent/cwsub_pitches_strikes_inplay` | 3 (1 lib + 2 field) | Ported as the constant `PITCH_STRIKE_INPLAY = frozenset("XY")` in `game.py`, used by `PA_INPLAY_STRIKE_CT`. Same behaviour. | Read C `game.c:1156` and `events.py:527` |
| `cwtools_process_filespec` (3 definitions) | 1 | **Real gap, small.** The C has three platform variants. On Unix it just processes the named file (equal to `process_scorebook`). On Windows and DOS it expands wildcards itself (`_findfirst`, `findfirst`). The port has only the Unix behaviour. | `cwtools.c:184-215`; `cli.py:261` |

Conclusion: nothing functional is missing for Linux and macOS. One platform behaviour (wildcard
expansion on Windows, where `cmd.exe` does not expand `*.EVA`) is not ported.

## 2. Python to C (what does the port add?)

522 Python functions; 45 have no C name match. They are not unexplained extras:

| Group | Functions | Purpose | Value |
| --- | --- | --- | --- |
| C semantics in Python | `_cdiv`, `_cmod`, `_deref`, `_strcmp_eq`, `_c0`, `_ordinal_suffix` (box tools) | Reproduce C integer division and modulo (truncate toward zero), NULL pointer reads, `strcmp` | Required for byte-identical output; keep |
| Parallel and CLI | `_init_worker`, `_process_files_parallel`, `available_cpus`, `main_umbrella` | Process files in parallel (default); `chadwickpy TOOL` entry point | The speed result: one worker 71.5 s, parallel 4.4 s on 40 cores for one season |
| Output helpers | `_tf`, `_render`, `_make_formatter`, `_custom`, `game_rows`, `event_rows` | Python API returning rows; formatting | Extension beyond C; needs its own tests |
| Event-field helpers | `_prev_play_exists`, `_next_play_exists`, `_half_inning_edge`, `_lineup_neighbour`, `_resp` | Implement C field logic that is spread across several C functions | Covered by byte comparison |
| File access | `getpos`, `setpos`, `peek` | Replace C `fgetpos`/`ungetc` style reads | Required |

None of the 45 is dead code that needs removing. The parallel path is the main addition and it is
the code you remembered having bugs; the repo log shows fixes #18 and #19, and the 2023 comparison
(30 files, 190,417 rows) was byte-identical in parallel and single-worker mode.

## 3. What this does not prove

- No branch-coverage measurement yet: we know every C function has a counterpart, not that every
  branch inside each is exercised by the 116 seasons tested.
- Only `cwevent` was re-run today (one season). The other five tools rely on the committed sweep
  records, not on a fresh run.
- Name matching is a lead, not proof. The field-label check covers output columns; it does not
  cover helper logic (parsing, state tracking).
- Fuzzing and rare-play synthetic inputs exist but their reach is unmeasured.

## 4. Recommendations

1. Measure branch coverage of the port over the full corpus (task 1.3); write targeted tests for every unreached branch (tasks 2.3, 3.1).
2. Decide on Windows wildcard expansion: either port it (a few lines using `glob` on `win32`) with a test, or document it as intentionally omitted. Recommend porting it, since users on Windows are the "others can download this" audience.
3. Add a test that fails if a new C function appears upstream without a Python counterpart (run the inventory against a newer Chadwick and diff), so the port does not drift.
4. Re-run all six tools on a fresh multi-era sample as part of CI parity, not only cwevent.
5. Keep parallel as the default and publish the numbers with core counts; decide later whether single-core speed (about 11 times slower than C) warrants Rust.
