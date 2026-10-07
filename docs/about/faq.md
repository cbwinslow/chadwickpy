---
description: Answers to common questions about chadwickpy - what data it needs, Retrosheet credit, speed, Windows, uv, licence, relation to Chadwick and pychadwick, and how to report problems.
---

# FAQ

**What is it?**
A pure-Python version of Chadwick's `cwevent`, `cwgame`, `cwdaily`, `cwsub`, `cwcomment` and
`cwbox` tools, which read Retrosheet play-by-play files.

**Do I need Chadwick installed?**
No. `chadwickpy` replaces it.

**Where do I get the data?**
From [Retrosheet](https://www.retrosheet.org/game.htm). `chadwickpy` does not include or
download data. See [Getting started](../getting-started.md).

**Do I have to credit Retrosheet?**
Retrosheet asks that anyone using its data say so. If you publish work built on it, include:
*"The information used here was obtained free of charge from and is copyrighted by Retrosheet.
Interested parties may contact Retrosheet at www.retrosheet.org."*

**Can I install it with uv?**
Yes: `uv tool install chadwickpy`, or run once without installing: `uvx --from chadwickpy cwevent -h`.

**Does it work on Windows and macOS?**
It is pure Python with no dependencies, so yes. CI tests Linux with Python 3.11-3.13.

**How does its speed compare to the original C tools?**
Single-file parsing runs at ~0.66 s per team file (pure Python). For full multi-file seasons, `chadwickpy` automatically runs files in parallel (one worker per usable CPU, leaving one free on machines with more than four, and never more workers than files), processing an entire 2,430-game season in **a few seconds** on a multi-core machine. That matches the C tools running on *one* core; the C tools are also faster when run on several cores. See [compared with Chadwick](compared-with-chadwick.md) for detailed benchmarks.

**Is it the same as `pychadwick`?**
No. Other Python projects wrap Chadwick's C library and need it built. `chadwickpy` is a
separate rewrite with no C at all.

**What licence is it under?**
GPL-3.0-or-later. It is a derivative of Chadwick (GPL-2.0-or-later, Copyright 2002-2023
Dr T L Turocy and the Chadwick Baseball Bureau), which is credited in `NOTICE` and in each
source file. It is independent: Chadwick and Retrosheet do not endorse it.

**How do I report a bug or a difference from Chadwick?**
Open an [issue](https://github.com/cbwinslow/chadwickpy/issues) with the event file lines, the
command, and the output you expected. For security problems, see `SECURITY.md`.

**How do I contribute?**
See [CONTRIBUTING](https://github.com/cbwinslow/chadwickpy/blob/main/CONTRIBUTING.md). The rule
of the project: fix differences by reading Chadwick's C, never by tuning output.
