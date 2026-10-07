# Decisions

Newest first.

## ADR-001: chadwickpy is only the port; retrosheetpy owns download and prep

**Decision (2026-10-07, owner direction).** `chadwickpy` translates the six Chadwick C tools and
nothing else. Downloading, caching and table shaping live in `retrosheetpy`, which depends on
`chadwickpy`. **Why.** One reason to change per package; the port can be verified against the C
tools in isolation. **Revisit if:** a second consumer needs download logic.
