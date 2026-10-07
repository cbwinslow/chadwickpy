# chadwickpy constitution

## What it is
A pure-Python, standard-library-only translation of the Chadwick Baseball Bureau's
C tools: `cwevent`, `cwgame`, `cwbox`, `cwdaily`, `cwsub`, `cwcomment`. **Only that.**
Nothing here downloads data or prepares it for a database; that is `retrosheetpy`.

## Boundaries
```text
chadwickpy   = port of the C tools (this repo). No network, no downloads, no DB.
retrosheetpy = downloads Retrosheet files, caches them, parses via chadwickpy, shapes tables.
mlb-baseball = ingests into PostgreSQL; uses the original C tools until ADR-299 is superseded.
```
Dependency direction: `mlb-baseball` -> `retrosheetpy` -> `chadwickpy`. Never the reverse.

## Invariants
1. **Translation, not reinvention.** Port line by line (or the equivalent); mirror the C, never tune a rule to make an output match. Name the C function in each docstring.
2. **Output equals the real tools byte for byte**, proven by differential tests against Chadwick built at the pinned commit.
3. **Complete, not just sufficient.** Passing current datasets is not proof; every C function and branch is mapped to Python or listed as intentionally omitted with a reason.
4. **Test first.** A discrepancy becomes a failing test before the fix.
5. **Standard library only** at runtime; Python 3.11-3.13.
6. **Honest speed claims.** Report single-core and parallel numbers with the core count.
7. `cwevent` gets the most scrutiny, then `cwgame`, `cwbox`, then the rest.

## Workflow
OpenSpec: `/opsx:propose` -> `/opsx:apply` -> `/opsx:archive`. ADRs in `docs/DECISIONS.md` (newest first).
Conventional Commits; PRs only; CI must pass.

## Phases
- **Now:** prove completeness and correctness (`verify-port-completeness`).
- **Next:** speed (single-core), release 1.0, then evaluate Rust/WebAssembly or TypeScript against this repo's verified corpus.
- **Later:** none committed.
