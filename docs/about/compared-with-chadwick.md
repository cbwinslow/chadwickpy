---
description: How chadwickpy compares with the original Chadwick C tools - performance, automatic multi-core parallelism, intentional crash differences, and compatibility.
---

# Compared with Chadwick

`chadwickpy` is a function-by-function translation of Chadwick's C source. The rule is
"translate the C, never guess from output", so the output matches wherever the C behaves in a defined way (see [where it differs](#where-it-intentionally-differs)).

| | Chadwick (C) | chadwickpy |
|---|---|---|
| Install | build from source with a C compiler, or a system package | `pip install chadwickpy` |
| Needs | compiler, autotools | Python 3.11+ (zero dependencies) |
| Output | the reference | identical on every season with game data, 1897-2025, for all six tools, for inputs where the C has defined behaviour |
| Speed (single file) | `cwevent` on one team-season: ~0.07 s | ~0.66 s (pure Python) |
| Speed (full season) | `cwevent` 2,430 games: ~2.25 s (1 core) | ~2.34 s (auto-parallelized across cores) |
| Throughput | ~83,000 plays/s | ~80,000 plays/s |
| Commands | `cwevent`, `cwgame`, `cwdaily`, `cwsub`, `cwcomment`, `cwbox` | the same names and options (plus `-j` for concurrency control) |
| Use from Python | via other wrappers | `import chadwickpy` |

## Benchmarks & Performance

The benchmark below compares original Chadwick C (0.10.0) against `chadwickpy` on the complete **2024 MLB Retrosheet season** (30 team event files, 2,430 games, 188,937 plays):

| Configuration | Total Time | Plays / Second | Output Match |
|---|---|---|---|
| **Chadwick (C)** (single core) | 2.25 s | ~83,900 plays/s | Reference (26.8 MB) |
| **chadwickpy** (sequential, `-j 1`) | 20.04 s | ~9,400 plays/s | 100% byte-for-byte identical |
| **chadwickpy** (default auto-parallel) | **2.34 s** | **~80,700 plays/s** | **100% byte-for-byte identical** |

### One core, every tool

Measured on one core (`-j 1`) against the C tools, whole 2025 season, default output, on a busy
40-core machine, so treat the ratios as approximate:

| Tool | C | chadwickpy `-j 1` | Slower by |
|---|---|---|---|
| `cwevent` | 2.4 s | 27.2 s | about 11x |
| `cwgame` | 1.3 s | 40.3 s | about 31x |
| `cwdaily` | 2.3 s | 38.3 s | about 17x |
| `cwsub` | 0.6 s | 14.4 s | about 24x |
| `cwcomment` | 0.5 s | 13.6 s | about 27x |
| `cwbox` | 1.6 s | 34.8 s | about 22x |

Across the seasons measured the ratio ran from about 5x to 38x. The C tools can also be run on several
cores (one process per team file): on the same machine that took `cwevent` about 0.5 s for a season,
so the "matches C" result above is against C on a single core.

### How to reproduce this benchmark

1. Download and unzip the 2024 Retrosheet season files into a folder:
   ```bash
   curl -O https://www.retrosheet.org/events/2024seve.zip
   unzip -q 2024seve.zip -d retro2024 && cd retro2024
   ```
2. Run with standard Chadwick C:
   ```bash
   time cwevent -y 2024 -n 2024*.EV* > c_events.csv
   ```
3. Run with `chadwickpy` (auto-parallel is default):
   ```bash
   time cwevent -y 2024 -n 2024*.EV* > py_events.csv
   ```
4. Check that both CSVs are 100% identical byte-for-byte:
   ```bash
   cmp c_events.csv py_events.csv
   ```

## When to choose which

* **Use chadwickpy** to get going quickly, in notebooks, on Windows, in CI, or anywhere you
  cannot compile software. Full seasons take just ~2.3 seconds on modern multi-core machines out of the box with zero native compilation.
* **Use the C tools** if you process many seasons repeatedly and the speed matters more than
  convenience.

## Using several cores

Output is identical at every core count (checked from 1 to 40 cores, with Python's `fork`, `spawn`
and `forkserver` worker start methods, and inside a Docker container limited to 2 CPUs). Rough times for
8 files of the 2023 season on a busy 40-core host:

| Cores | 1 | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|
| `cwevent`, all fields (seconds; C on one core: 2.2) | 22.5 | 12.1 | 6.6 | 6.3 | 3.7 |

It never starts more workers than there are files. See [using several cores](../guides/parallel.md).

## Where it intentionally differs

* Where the C **crashes or reads memory it should not**, `chadwickpy` stops with a clear error or
  uses a defined value. Examples: a game with no date, a month of 0 or 13, more than 50 line-score
  innings, and `cwbox` text on a game that has no plays (all of Retrosheet's box-score-only seasons
  1901-1907 crash the C `cwbox` text output; `cwbox -X` works in both). The reasons are recorded in
  the project's [design decisions](../DECISIONS.md).
* **SportsML output (`cwbox -S`) is deprecated.** Chadwick's own `-S` crashes on nearly every game,
  so there is nothing to compare it with. The `pb` attribute of `cwbox -X` depends on uninitialised
  memory in the C and is not compared.
* `-j` / `--jobs` and the `CHADWICK_JOBS` variable exist only here (the C tools run one process).
* On Windows, wildcards such as `2010*.EV*` are expanded as Chadwick's Windows build does. Unlike
  that build, a folder in the pattern is kept (`sub\*.EVA`).
* The reference is Chadwick's development commit `c685ab5` (it reports version 0.10.0), not
  the 0.10.0 release tag, whose output differs on 2025 files.
* Inputs that make the C behave in undefined ways are not compared.

## If both are installed

The command names are identical. Whichever directory comes first on `PATH` runs. To always
get this package's version, use `chadwickpy cwevent ...` or `python -m chadwickpy cwevent ...`.
