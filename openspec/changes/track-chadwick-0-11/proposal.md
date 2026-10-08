# Proposal: track-chadwick-0-11

## Why

chadwickpy 0.3.0 is verified byte for byte against Chadwick commit `c685ab5` (a development commit
after 0.10.0). Chadwick **0.11.0 was released on 2026-09-10** (40 changes, 421 of 653 C functions
changed). The weekly newest-Chadwick run added in 0.3.0 failed on 2026-10-08 with 4,680 of 5,083 tests
different, which is the check doing its job. The owner's requirement is that chadwickpy returns the
same results as the C tools, including newer versions and datasets, so the port must follow 0.11.0.

## What Changes

Port each upstream change, test first, against the real 0.11.0 tools (tag `v0.11.0`):

- Command line: quiet switch `-q` becomes `-Q` (the C now rejects `-q`), new `-D dir` (where
  TEAMyyyy and the roster files are), help text, version 0.11.0, copyright 2002-2026.
- Play parser: `C/` events, `#` and `!` ignored in preprocessing, DP/RINT forces, catcher putouts on
  strikeouts, `SB` inside advance modifiers, explicit versus inferred batted-ball type, pickoff as the
  trailing half of a CS, `?` no longer an unknown fielder, `/TH` and `/THn` on OA, "99 plays".
- Box scores: validation of team, slot and position in box-score event files, PH and PR entries,
  zero sequence field mitigation, the day/night lookup fix.
- `cwevent`: pinch-runner position 12, `FLD_TEAM_ID` quoting; `cwgame`: fields match current BEVENT,
  game-date field configuration (`-d` formats), finishing pitcher, linescores; `cwsub`: `COUNT_TX`.
- File reading: the record reader and tokenizer that replaced `strtok`; `padj` semantics.
- Re-capture the stored reference outputs from 0.11.0, move CI to build 0.11.0, re-run the whole
  proof (every season, every field and option, coverage, drift fingerprints).

This is a breaking change for scripts that pass `-q` (the C tools break in the same way), so it ships
as **0.4.0**.

## Capabilities

### New Capabilities
<!-- none: port maintenance (skip_specs) -->

### Modified Capabilities
<!-- none -->

## Impact

`src/chadwickpy/`, `tests/`, `.github/workflows/` (the pinned Chadwick), `docs/`, release 0.4.0.
