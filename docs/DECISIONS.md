# Decisions

Newest first.

## ADR-003: Where the port differs from C on purpose

**Decision (2026-10-07).** When the C tool crashes or reads past an array on malformed input, the
port raises a clear error (or defines the value) instead of copying the fault. Cases: a game with no
or unreadable date, a month of 0 or 13, `badj` with no batter, more than 50 line-score innings,
more than 40 positions or 20 double-play players, `cwbox` text on a game with no plays. The port also
adds `-j`/`--jobs`/`CHADWICK_JOBS`. **Why.** Matching undefined behaviour would be copying bugs; the
tests record both outputs so any change shows. Real seasons are unaffected (byte-identical).
**Revisit if:** a user needs the exact C output on such input.

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
