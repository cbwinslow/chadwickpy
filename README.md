<p align="center">
  <img src="https://raw.githubusercontent.com/cbwinslow/chadwickpy/main/docs/assets/logo.svg" alt="chadwickpy logo" width="96">
</p>

<h1 align="center">chadwickpy</h1>

<p align="center"><b>Retrosheet play-by-play files to data tables. Pure Python, one <code>pip install</code>.</b></p>

<p align="center">
  <a href="https://github.com/cbwinslow/chadwickpy/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/cbwinslow/chadwickpy/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/chadwickpy/"><img alt="PyPI" src="https://img.shields.io/pypi/v/chadwickpy"></a>
  <a href="https://pypi.org/project/chadwickpy/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/chadwickpy"></a>
  <a href="https://pypi.org/project/chadwickpy/"><img alt="Downloads" src="https://img.shields.io/pypi/dm/chadwickpy"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/chadwickpy"></a>
  <a href="https://cbwinslow.github.io/chadwickpy/"><img alt="Docs" src="https://img.shields.io/badge/docs-website-14213d"></a>
</p>

[Retrosheet](https://www.retrosheet.org) publishes every play of every MLB game as text
files. The [Chadwick](https://github.com/chadwickbureau/chadwick) tools turn those files into
tables. **chadwickpy is those same six tools, rewritten in pure Python**: no compiler, no C
library, no dependencies. Output is byte-identical to Chadwick on every Retrosheet season that has game data, 1897 to 2025 (for inputs where the C behaves in a defined way).

```bash
pip install chadwickpy            # or: uvx --from chadwickpy cwevent -h
curl -O https://www.retrosheet.org/events/2010seve.zip
unzip -q 2010seve.zip -d retro2010 && cd retro2010
cwevent -y 2010 -n -f 0,2,3,4,10,14,29,34 2010NYA.EVA > yankees_events.csv
```

```text
"GAME_ID","INN_CT","BAT_HOME_ID","OUTS_CT","BAT_ID","PIT_ID","EVENT_TX","EVENT_CD"
"NYA201004130",1,0,0,"aybae001","petta001","S9/F9S-",20
"NYA201004130",1,0,0,"abreb001","petta001","K",3
"NYA201004130",1,0,1,"huntt001","petta001","8/F8LXD",2
```

## The six tools

| Tool | One row per |
|---|---|
| `cwevent` | event (a play): up to 164 columns |
| `cwgame` | game |
| `cwdaily` | player per game (batting, pitching, fielding) |
| `cwsub` | substitution |
| `cwcomment` | scorer comment |
| `cwbox` | game, as a text or XML box score (SportsML is deprecated: Chadwick's own `-S` crashes) |

Same command names and options as Chadwick. Also usable from Python
(`from chadwickpy.tools.events import event_rows`).

## Good to know

* **Speed**: on one core chadwickpy is roughly 10 to 40 times slower than the C tools. With several files
  (a whole season) it **uses several cores by itself**: a full 2,430-game season takes about 2 seconds
  on a multi-core machine, the same as the C tools on *one* core. The output is identical at every core
  count (checked from 1 to 40). See [the cores guide](https://cbwinslow.github.io/chadwickpy/guides/parallel/).
* Choose the number of workers with `-j <workers>` (`-j 1` is sequential) or the `CHADWICK_JOBS`
  environment variable. By default it follows the CPUs the process may use, including a CPU limit set
  by Docker, Kubernetes or systemd.
* It reads Retrosheet's files; it does not include or download them.
* Pure Python, zero dependencies. Python 3.11 or newer; CI runs Python 3.11 to 3.13 on Linux, and it was
  also checked on 3.14. It should work on macOS and Windows too (on Windows it expands wildcards such as
  `2010*.EV*` itself, as the C tools do), but those are not part of the automated tests.

## Documentation

**<https://cbwinslow.github.io/chadwickpy/>**: getting started, a guide to each tool, Python
usage, recipes, the full option and field reference, how it was verified, and an FAQ.
Machine-readable: [`llms.txt`](https://cbwinslow.github.io/chadwickpy/llms.txt).

## Verification

Output is compared byte for byte (standard output, error messages and exit status) with the real
Chadwick programs, built from commit `c685ab5`:

* every season with game data, 1897 to 2025, all six tools and 16 option sets (2,064 comparisons);
* every output field of every tool on its own and in combination, both output formats, and every
  game-selection option;
* tests aimed at every remaining branch of the code: **99% of the lines and branches are reached**, and
  the rest are listed with the reason they cannot be;
* a weekly check against the newest Chadwick, and a test that fails when any C function changes.

Details and how to run them yourself: [How it was verified](https://cbwinslow.github.io/chadwickpy/about/verification/).
CI builds Chadwick and runs the whole suite on Python 3.11-3.13, failing on any skipped parity test.

## Licence and credit

GPL-3.0-or-later (`LICENSE`). chadwickpy is a derivative work of Chadwick, Copyright (C)
2002-2023 Dr T L Turocy and the Chadwick Baseball Bureau, GPL-2.0-or-later (`COPYING-chadwick`,
`NOTICE`); each ported module keeps that notice. It is independent: Chadwick and Retrosheet do
not endorse or sponsor it, and it ships no Retrosheet data.

Retrosheet's data-use notice asks that anyone using its data say so. If you publish anything
built on it, include:

> The information used here was obtained free of charge from and is copyrighted by
> Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".

## Contributing, questions, security

[CONTRIBUTING.md](CONTRIBUTING.md) · [Discussions](https://github.com/cbwinslow/chadwickpy/discussions) ·
[Issues](https://github.com/cbwinslow/chadwickpy/issues) · [SECURITY.md](SECURITY.md).
The rule of the project: the port stays a translation of Chadwick's C; rules come from the C,
never from tuning output.
