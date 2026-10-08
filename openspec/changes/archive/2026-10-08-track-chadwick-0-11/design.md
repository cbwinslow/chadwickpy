# Design: track-chadwick-0-11

## Decisions

- **Reference is the released tag `v0.11.0`** (not master, which is 2 commits ahead). The pinned
  commit in `ci.yml` moves from `c685ab5` to the tag's commit.
- **Follow the C exactly, including `-Q`.** `-q` is rejected as the C rejects it. No alias: the
  project rule is that the port is a translation of the C. The change is announced in the release notes.
- **Work in groups that match the upstream commit groups** so each can be tested and reviewed on its own:
  command line, parser, box scores, tool fields, file reading.
- **Evidence loop:** run the whole suite against the real 0.11.0 tools, fix a group, rerun; the
  failing-test list shrinks to zero. Then the corpus run, the field and option sweeps, coverage and
  the drift fingerprints are redone.
- Stored reference outputs (`tests/reference/chadwick*`) are re-captured from the 0.11.0 tools.

## Risks

- Upstream changed how files are read (`strtok` replaced by a tokenizer): odd input may now behave
  differently; the damaged-file and fuzz tests decide.
- Behaviour that was undefined in 0.10.0 may now be defined (or the reverse); the ADR-003 list needs
  re-checking.
