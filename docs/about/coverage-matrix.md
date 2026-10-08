---
description: Which of Chadwick's C functions chadwickpy ports, how that was checked, and what is still unreviewed.
---

# Port coverage matrix

Checked against Chadwick 0.11.0 (tag `v0.11.0`, the version the parity tests use). The port was first verified against the development commit `c685ab5` that preceded it (chadwickpy 0.3.0).

## Method

1. `tests/reference/c_inventory.py` lists every function defined in the C library
   (`src/cwlib`) and the six tools (`src/cwtools`), including the per-field functions the tools
   declare through the `DECLARE_FIELDFUNC` macro. The output is `c-inventory.txt`.
2. Each C function is looked up in `src/chadwickpy` by name (the port keeps Chadwick's names,
   without the `cw_` prefix, or as a method). `ok` means the name appears as a whole word in the
   Python source. That is a text search: it does not prove the match is a definition (a call or a
   comment would also match), so `ok` is a pointer for review, not proof of a port. `n/a-mem` means a C memory-cleanup function that Python does not need.
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

## Keeping the matrix honest

The name lookup above is a lead, not evidence (see the note on `ok`). Drift in the C sources is detected by a different, exact method: `tests/test_upstream_drift.py` compares a fingerprint of every C function with `c-function-hashes.txt`, and a weekly workflow runs the whole suite against the newest Chadwick.
