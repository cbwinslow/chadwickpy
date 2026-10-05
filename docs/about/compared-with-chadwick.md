---
description: How chadwickpy differs from the original Chadwick C tools - speed (about 25 times slower), where it deliberately differs on crashes, and which Chadwick version it matches.
---

# Compared with Chadwick

`chadwickpy` is a function-by-function translation of Chadwick's C source. The rule is
"translate the C, never guess from output", so the results are the same.

| | Chadwick (C) | chadwickpy |
|---|---|---|
| Install | build from source with a C compiler, or a system package | `pip install chadwickpy` |
| Needs | compiler, autotools | Python 3.11+ |
| Output | the reference | identical on every season 1910-2025, all six tools |
| Speed | `cwevent` on one team-season: 0.075 s | about 1.4 s (about 25 times slower) |
| Commands | `cwevent`, `cwgame`, `cwdaily`, `cwsub`, `cwcomment`, `cwbox` | the same names and options |
| Use from Python | via other wrappers | `import chadwickpy` |

## When to choose which

* **Use chadwickpy** to get going quickly, in notebooks, on Windows, in CI, or anywhere you
  cannot compile software. A season takes seconds to minutes.
* **Use the C tools** if you process many seasons repeatedly and the speed matters more than
  convenience.

## Where it intentionally differs

* Where the C **crashes or reads uninitialised memory**, `chadwickpy` raises `ValueError` or
  uses a defined value. `cwbox -S` segfaults in Chadwick 0.10.0, so SportsML output and the
  `pb` attribute of `cwbox -X` were compared with a patched build.
* The reference is Chadwick's development commit `c685ab5` (it reports version 0.10.0), not
  the 0.10.0 release tag, whose output differs on 2025 files.
* Inputs that make the C behave in undefined ways are not compared.

## If both are installed

The command names are identical. Whichever directory comes first on `PATH` runs. To always
get this package's version, use `chadwickpy cwevent ...` or `python -m chadwickpy cwevent ...`.
