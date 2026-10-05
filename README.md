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
library, no dependencies. Output is byte-identical to Chadwick on every season from 1910 to 2025 (for inputs where the C behaves in a defined way).

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
| `cwbox` | game, as a text, XML or SportsML box score |

Same command names and options as Chadwick. Also usable from Python
(`from chadwickpy.tools.events import event_rows`).

## Good to know

* **Speed**: Single-core processing is ~0.66 s per team-season. When processing multiple files (such as a full season), `chadwickpy` **automatically parallelizes across available CPU cores**, processing an entire 2,430-game season in **~2.3 seconds** (~80,000 plays/s), matching native C throughput.
* Override parallelism anytime via `-j <workers>` (e.g. `-j 1` for sequential) or the `CHADWICK_JOBS` environment variable.
* It reads Retrosheet's files; it does not include or download them.
* Pure Python (zero dependencies). Python 3.11 or newer (also fully compatible with PyPy 3.10+ and Python 3.13+ JIT). Linux, macOS and Windows.

## Documentation

**<https://cbwinslow.github.io/chadwickpy/>**: getting started, a guide to each tool, Python
usage, recipes, the full option and field reference, how it was verified, and an FAQ.
Machine-readable: [`llms.txt`](https://cbwinslow.github.io/chadwickpy/llms.txt).

## Verification

`tests/` compares every tool with captured real-Chadwick output, and with the real programs
when they are available (`CHADWICK_BIN`, `CHADWICK_SRC`). CI builds Chadwick at commit
`c685ab5` and runs the whole suite on Python 3.11-3.13, failing on any skipped parity test.
Run it yourself: `uv run --with pytest pytest`.

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
