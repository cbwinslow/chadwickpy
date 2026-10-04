# chadwickpy

[![CI](https://github.com/cbwinslow/chadwickpy/actions/workflows/ci.yml/badge.svg)](https://github.com/cbwinslow/chadwickpy/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/chadwickpy)](https://pypi.org/project/chadwickpy/)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://cbwinslow.github.io/chadwickpy/)

A pure-Python port of the [Chadwick](https://github.com/chadwickbureau/chadwick) baseball
tools: `cwevent`, `cwgame`, `cwdaily`, `cwsub`, `cwcomment` and `cwbox`. They read
[Retrosheet](https://www.retrosheet.org) event files and write the same tables Chadwick
does. No compiler, no C library, no dependencies: `pip install chadwickpy`.

The code is a function-by-function translation of Chadwick's C. Its output is
byte-identical to the real tools on every season from 1910 to 2025 (all six tools; see
[Verification](#verification)), apart from the [differences](#differences-from-chadwick) below.

## Install and use

```bash
pip install chadwickpy        # or: uv tool install chadwickpy
cwevent -y 2010 -f 0-96 2010NYA.EVA > 2010NYA.csv
cwgame -y 2010 2010NYA.EVA
chadwickpy cwbox -y 2010 2010NYA.EVA   # same tool, always this package's version
python -m chadwickpy cwdaily -y 2010 2010NYA.EVA
```

The command names and options are Chadwick's; see its
[documentation](https://chadwick.readthedocs.io/). If the C programs are also installed,
whichever comes first on `PATH` runs; `chadwickpy TOOL` always runs this package.
Roster (`.ROS`, `TEAMyyyy`) files are read from the event file's directory, as in Chadwick.

The library is importable too. The layout follows Chadwick's: `chadwickpy` (the `cwlib`
parts: parser, game, file, roster, box score, game iterator) and `chadwickpy.tools` (the
`cwtools` programs).

## Speed

About 25 times slower than the C (`cwevent` on one team-season: 0.075 s in C, about
1.4 s here). That is the price of needing nothing but Python. Whole seasons still run in
seconds to minutes.

## Differences from Chadwick

- Where the C crashes or reads uninitialised memory this port raises `ValueError` or uses
  a defined value. `cwbox -S` (it segfaults in Chadwick 0.10.0) and the `pb` attribute of
  `cwbox -X` are compared against a patched build.
- The reference is Chadwick's development commit `c685ab5` (it reports 0.10.0), not the
  released v0.10.0 tag, whose output differs on 2025 files.
- Inputs that make the C behave in undefined ways are not compared.

## Verification

`tests/` runs every tool against captured real-Chadwick output and, when Chadwick is
available, against the real programs (set `CHADWICK_BIN` and `CHADWICK_SRC`, or build
Chadwick at `c685ab5`; CI does). Season-sweep drivers in `tests/reference/` compare whole
seasons; they need the Retrosheet decade zips. Run: `uv run pytest`.

## Licence and credit

AGPL-3.0-or-later (`LICENSE`). This package is a derivative work of Chadwick, Copyright
(C) 2002-2023 Dr T L Turocy and the Chadwick Baseball Bureau, GPL-2.0-or-later
(`COPYING-chadwick`, `NOTICE`); each ported module keeps that notice. chadwickpy is
independent: it is not endorsed or sponsored by Chadwick or Retrosheet, and ships no
Retrosheet data.

Retrosheet's data-use notice asks that anyone using its data say so. If you publish
anything built on it, include:

> The information used here was obtained free of charge from and is copyrighted by
> Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".

## Contributing and security

See `CONTRIBUTING.md` and `SECURITY.md`. A rule of this project: the port stays a
translation of Chadwick's C. Rules are taken from the C, never guessed from output.
