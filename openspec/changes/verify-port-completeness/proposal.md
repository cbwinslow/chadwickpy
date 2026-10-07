# Proposal: verify-port-completeness

## Why

Current evidence (docs/about/verification.md) shows byte-identical output on 116 seasons across six
tools, but that proves the datasets pass, not that every C code path was ported. The owner wants
proof the translation is complete and future-proof, with `cwevent` scrutinized most. Measured
2026-10-07 on one 2023 season: `cwevent` output identical; C 6.7 s, Python 71.5 s on one worker,
4.4 s parallel on 40 cores.

## What Changes

- Build a coverage matrix mapping every C function and branch (parse.c, gameiter.c, game.c, box/roster code, each tool's main) to its Python counterpart, listing unmapped items.
- Extend differential tests: every season 1871-2025 where data exists, every tool, all `cwevent` field/option combinations, plus fuzzed and synthetic inputs for rare paths.
- Fix each discrepancy test-first, mirroring the C.
- Record single-core versus parallel performance with core counts; decide whether a speed change is needed.

Documentation and tests plus fixes found; no new features.

## Capabilities

### New Capabilities
<!-- none: verification work (skip_specs) -->

### Modified Capabilities
<!-- none -->

## Impact

`tests/`, possibly `src/chadwickpy/` fixes, `docs/about/verification.md`, `docs/DECISIONS.md`.
Out of scope: Rust/WASM/TypeScript ports, `retrosheetpy` changes.
