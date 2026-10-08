# Decisions

Newest first.

## ADR-005: Follow the official Chadwick release exactly (0.11.0), including `-Q`

**Decision (2026-10-08, owner: "same results as the C tools every time, including future versions").**
chadwickpy follows the **released** Chadwick (tag `v0.11.0`, 2026-09-10), not a development commit.
That includes its command line: the quiet switch is `-Q` (`-q` is rejected as "Invalid option", as in
the C), and `-D dir` exists. No `-q` alias. The change ships as **0.4.0** (breaking for scripts that
pass `-q`) with the difference listed in the release notes and the FAQ. **Why.** The project rule is
that the port is a translation of the C and its output is compared with the real tools byte for byte;
an alias would be a deliberate difference that every future comparison has to carve out. A weekly
workflow builds the newest Chadwick and runs the whole suite, which is how 0.11.0 was found (4,680 of
5,083 tests differed on the first run). **Revisit if:** many users ask for a `-q` alias.

## ADR-004: Speed is acceptable for 1.0; workers follow container CPU limits

**Decision (2026-10-07, owner).** (1) The port ships at its current speed: about 10 times slower
than the C program on one core, and within about 1.7 times of the one-core C program with 16
cores (measured on `cwevent`, 8 files of 2023, busy 40-core host). Output is identical at every core
count, so speed is not a correctness question. A faster build (for example Rust) is a later,
separate decision if users ask for it. (2) The automatic worker count honours a Linux container or
service CPU quota (Docker `--cpus`, Kubernetes limits, systemd `CPUQuota=`; cgroup versions 1 and
2) as well as CPU affinity, so a process limited to 2 CPUs on a 64-core host starts 2 workers, not
63. **Why.** Correct, reproducible output is the product; an unbounded worker count only wastes
memory. Checked in real containers: `--cpus=2` gives 2 workers, `--cpus=0.5` gives 1, no limit
gives 39 on a 40-core host; output identical on Python 3.12 (`fork`) and 3.14 (`forkserver`).
**Revisit if:** users report the speed as a blocker, or a quota type is found that is not read.

## ADR-003: Where the port differs from C on purpose

**Decision (2026-10-07).** When the C tool crashes or reads past an array on malformed input, the
port raises a clear error (or defines the value) instead of copying the fault. Cases: a game with no
or unreadable date, a month of 0 or 13, `badj` with no batter, more than 50 line-score innings,
more than 40 positions or 20 double-play players, a pickoff-caught-stealing play naming a base other than 1-3, H or 4 (the C writes outside its array and corrupts neighbouring output fields; the port ignores the write), `cwbox` text on a game with no plays (this is what the real cwbox does on the box-score-only seasons 1901-1907: it crashes, and the port reports an error; `cwbox -X` works in both). The port also
adds `-j`/`--jobs`/`CHADWICK_JOBS`. Dates shorter than ten characters are the exception: #24 made the port print what the C prints. **Chadwick 0.11.0 review (box scores).** `cwbox` text on the box-score-only seasons 1901-1907 still crashes in 0.11.0 (re-checked on the real files): unchanged. A box-score event file with a team outside 0-1, a `bline` slot outside 0-9, a `dline` sequence outside 1-40 or position outside 1-9 used to index outside the arrays (undefined behaviour); 0.11.0 validates them and exits 1 with an error, so the port now matches that exactly (not a deviation). A starter with no position in a CR LF file now loses its record under the 0.11.0 line reader and `cwbox` crashes: the port reports an error. A date with only a month (`2020/01`) still reads an uninitialised day: the port refuses it. **Why.** Matching undefined behaviour would be copying bugs; the
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
