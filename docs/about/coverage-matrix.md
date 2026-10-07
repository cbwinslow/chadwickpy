---
description: Which of Chadwick's C functions chadwickpy ports, how that was checked, and what is still unreviewed.
---

# Port coverage matrix

Checked against Chadwick commit `c685ab5` (the commit the parity tests use).

## Method

1. `tests/reference/c_inventory.py` lists every function defined in the C library
   (`src/cwlib`) and the six tools (`src/cwtools`), including the per-field functions the tools
   declare through the `DECLARE_FIELDFUNC` macro. The output is `c-inventory.txt`.
2. Each C function is looked up in `src/chadwickpy` by name (the port keeps Chadwick's names,
   without the `cw_` prefix, or as a method). `ok` means a Python definition or a docstring naming
   it exists. `n/a-mem` means a C memory-cleanup function that Python does not need.
3. Output fields are checked a second way, by the tools themselves: the field list printed by
   `-d` is identical to the C tools' for `cwevent`, `cwgame`, `cwdaily`, `cwsub` and `cwcomment`
   (checked 2026-10-07).

## Result (2026-10-07)

| Count | Meaning |
| --- | --- |
| 653 | C functions found in the sources |
| 603 | found by name in the port |
| 1 | C memory cleanup, not needed |
| 49 | not found by name (see below) |

The 49 are mostly numbered output fields that the port builds in a loop instead of one function each
(`assist1`..`assist10`, `putout1`..`3`, `responsible_pitcher1`..`3`), and the tool field list
matches the C tools exactly. One was reviewed by hand: `cw_pitch_strike_inplay` is ported as the
constant `PITCH_STRIKE_INPLAY` in `game.py`, same behaviour.

**Reviewed:** all 49 (see `openspec/changes/verify-port-completeness/assessment.md`): 48 ported in another form, 1 platform gap (Windows wildcard expansion).

**Not yet done:** branch coverage of the port
over the full corpus (task 1.3 of `verify-port-completeness`). Until then, "complete" means
"the output field lists match and every season tested matches", not "every branch is proven".
