## Context

See proposal.md. Pinned C reference: commit `c685ab5` (reports 0.10.0, differs from the release). Existing
differential tests live in `tests/test_*_differential.py` and `tests/reference/`.

## Goals / Non-Goals

**Goals:** a checked-in coverage matrix with zero unexplained gaps; wider differential coverage; documented performance.
**Non-Goals:** other-language ports; new tool features; changing output.

## Decisions

- **Coverage by C function first, branch second.** Inventory with `ctags` on the C source; branch coverage of the Python via `coverage.py` while replaying the full corpus shows which Python paths the corpus never reaches, then synthetic inputs target those.
- **Gaps are findings, not silent skips.** Each unmapped C function is ported, or recorded as intentionally omitted with a reason.
- **`cwevent` first**, then `cwgame`, `cwbox`, then `cwdaily`, `cwsub`, `cwcomment`.
- **Seasons from Retrosheet archives held locally**; sweep scripts already in `tests/reference/` are reused.

## Risks / Trade-offs

- Full 1871-2025 sweeps are long single-core; run parallel and cache C outputs.
- Retrosheet data not redistributed in the repo; sweeps are local/CI-optional, committed fixtures stay small.
- Open question for the owner: is single-core speed (about 11x slower than C) acceptable for 1.0?
