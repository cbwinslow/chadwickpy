# Design: verify-port-completeness

## Context

See proposal.md. Pinned C reference: commit `c685ab5` (reports 0.10.0, differs from the release). Existing
differential tests live in `tests/test_*_differential.py` and `tests/reference/`.

## Goals / Non-Goals

**Goals:** a checked-in coverage matrix with zero unexplained gaps; wider differential coverage; documented performance.
**Non-Goals:** other-language ports; new tool features; changing output.

## Decisions

- **Coverage by C function first, branch second.** Inventory with `ctags` on the C source; branch coverage of the Python via `coverage.py` while replaying the full corpus shows which Python paths the corpus never reaches, then synthetic inputs target those.
- **C branches too, not only C functions.** A function name match cannot show that every branch inside it was ported. Run the instrumented C tools over the same corpus (`tests/reference/gcov_run.py`), list the C lines and branches the corpus reaches, and map each reached C branch to the Python code that handles it; C branches the corpus never reaches get a synthetic input or a documented reason. Python branch coverage (above) is the reverse check.
- **Gaps are findings, not silent skips.** Each unmapped C function is ported, or recorded as intentionally omitted with a reason.
- **`cwevent` first**, then `cwgame`, `cwbox`, then `cwdaily`, `cwsub`, `cwcomment`.
- **Seasons from Retrosheet archives held locally**; sweep scripts already in `tests/reference/` are reused.

## Risks / Trade-offs

- Full 1871-2025 sweeps are long single-core; run parallel and cache C outputs.
- Retrosheet data not redistributed in the repo; sweeps are local/CI-optional, committed fixtures stay small.
- Open question for the owner: is single-core speed (about 11x slower than C) acceptable for 1.0?
- **Never edit the code under test while a long comparison runs.** The sweep scripts import the live editable install; a temporary mutation check in the middle of the 2026-10-07 whole-corpus run produced two false mismatches (1928 `cwdaily`). Run mutation checks before or after, or in a separate checkout.
