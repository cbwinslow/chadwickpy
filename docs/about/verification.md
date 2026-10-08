---
description: How chadwickpy output is proven identical to the real Chadwick tools - every season with game data from 1897 to 2025, every field and option, 99% of the code exercised, a weekly check against the newest Chadwick - and how to run the checks yourself.
---

# How it was verified

A translation is only useful if it gives the same answers. The checks compare `chadwickpy` with the
real Chadwick programs, built from the 0.11.0 release (tag `v0.11.0`), on **standard output, error messages and exit
status**, byte for byte.

## What was checked

| Check | Result |
|---|---|
| **Every season with play-by-play, 1908 to 2025** (118 seasons), all six tools, 16 option sets each, against Chadwick 0.11.0 | 1,888 comparisons, 22 GB of output, no differences |
| **The box-score-only seasons, 1897 to 1907** (Retrosheet has no plays for these) | 176 comparisons; all identical except `cwbox` text on 1901-1907, where the C program crashes (also in 0.11.0) and chadwickpy reports an error |
| **Every output field of every tool**, on its own and in random combinations, ASCII and fixed-width | `cwevent` 97 standard + 67 extended fields; `cwgame` 85 + 97; `cwdaily` 154; `cwsub` 25; `cwcomment` 10; all identical, on fixtures from every era and rule variant |
| **Every game-selection and format option** (`-i`, `-s`, `-e`, `-a`, `-n`, `-ft`, `-f`, `-x`, `-d`, `-Q`, `-D`, `-X`), alone and combined | about 2,500 combinations, all identical; malformed values too |
| **The play parser** against Chadwick's own parser | thousands of generated plays covering every modifier, plus hand-built plays for the rare branches |
| **Synthetic and damaged games**, and the **write side** (re-writing event files) | identical wherever the C behaves in a defined way |
| **Parallel runs** | identical output on 1 to 40 cores, with `fork`, `spawn` and `forkserver` workers, with any `-j`, and inside a Docker container limited to 2 CPUs on Python 3.14 |

## How complete is it

* **99% of the code was exercised by the tests** when measured on version 0.3.0 (5,592 statements and
  2,382 branches); version 0.4.0 added tests for every ported Chadwick 0.11.0 change and 5,163 tests pass
  against the real 0.11.0 tools. The few lines never reached are listed in the project's task record, each with the reason (for example a
  guard for a state the earlier code already rejects), apart from the deprecated SportsML output.
* **The other direction was measured too:** the real C tools were rebuilt with coverage
  instrumentation and run over the same data. The corpus exercised about 76% of all C lines overall and
  98-99% of each of the five main tools' code; the rest is library code that no tool calls (checked by
  separate C test programs) or SportsML. The C functions no run called are listed in
  [`c-functions-not-run-by-corpus.txt`](c-functions-not-run-by-corpus.txt).
* **Every C function is accounted for.** All 653 are either ported or recorded as not needed, see the
  [coverage matrix](coverage-matrix.md). Windows wildcard expansion, the one platform feature that was
  missing, is now ported.
* **Future-proofing.** A fingerprint of every C function is stored in the repository. A test fails if a
  newer Chadwick adds, removes or changes any of them, and a workflow builds the newest Chadwick every
  week and runs the whole test suite against it.

## Where the output differs on purpose

Where the C program crashes or reads memory it should not, chadwickpy stops with a clear error or
uses a defined value instead of copying the fault. SportsML output (`cwbox -S`) is deprecated because
Chadwick's own version crashes. Every such case is recorded in the project's
[design decisions](../DECISIONS.md) and pinned by a test that records both outputs.

## Run them yourself

```bash
git clone https://github.com/cbwinslow/chadwickpy
cd chadwickpy
uv run --with pytest pytest          # compares with captured Chadwick output
```

To compare against the live C tools, build Chadwick at the pinned commit and set `CHADWICK_BIN` (the
folder with `cwevent`) and `CHADWICK_SRC`. CI does exactly this on Python 3.11, 3.12 and 3.13, and fails
if any parity test is skipped.

The season-sweep scripts in `tests/reference/` need the Retrosheet decade archives
(`https://www.retrosheet.org/events/2010seve.zip` and so on; the 1897-1907 box scores are
`https://www.retrosheet.org/events/1900box.zip` and similar).

## Any number of cores

The parallel run was checked by restricting the process to 1, 2, 3, 4, 5, 8, 16 and 40 cores
(`taskset`) on 8 files of the 2023 season with every `cwevent` field: the output is byte-identical to
the C program every time. Rough timings on a busy host: the C program 2.2 s on one core; chadwickpy
22.5 s on one core, 12.1 s on two, 6.6 s on four, 3.7 s on sixteen. It never starts more workers than
there are files. Output is also identical when workers are started with `fork`, `spawn` or
`forkserver`, and with any `-j` value. See [using several cores](../guides/parallel.md).

## Timings per tool

All six tools on 8 files of the 2023 season with the default fields, on a busy 40-core host
(seconds; output identical to the C program in every case). The C programs take well under a second;
chadwickpy is a pure-Python translation and is slower, most of all on a single core.

| Tool | C, 1 core | chadwickpy, 1 core | chadwickpy, 8 cores |
| --- | --- | --- | --- |
| cwevent | 0.3 | 7.3 | 2.1 |
| cwgame | 0.4 | 10.2 | 3.1 |
| cwdaily | 0.6 | 11.3 | 3.3 |
| cwsub | 0.1 | 4.6 | 1.6 |
| cwcomment | 0.1 | 4.7 | 1.4 |
| cwbox | 0.4 | 10.8 | 2.7 |

With every `cwevent` field requested the single-core gap is smaller (about 10 times).
