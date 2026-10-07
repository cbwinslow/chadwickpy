# Decisions

Newest first.

## ADR-002: SportsML output (`cwbox -S`) is deprecated

**Decision (2026-10-07, owner direction).** The SportsML box-score format is labelled deprecated.
It stays in the port as shipped, but is excluded from the completeness and coverage targets.
**Why.** The C `cwbox -S` crashes on nearly every game, so there is no reference output to prove
the port against. **Revisit if:** a user needs SportsML and a working reference appears.

## ADR-001: chadwickpy is only the port; retrosheetpy owns download and prep

**Decision (2026-10-07, owner direction).** `chadwickpy` translates the six Chadwick C tools and
nothing else. Downloading, caching and table shaping live in `retrosheetpy`, which depends on
`chadwickpy`. **Why.** One reason to change per package; the port can be verified against the C
tools in isolation. **Revisit if:** a second consumer needs download logic.
