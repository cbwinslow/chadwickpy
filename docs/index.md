---
description: chadwickpy turns Retrosheet play-by-play files into clean tables (events, games, player-games, substitutions, comments, box scores) with one pip install and no compiler. A pure-Python port of the Chadwick baseball tools.
---

# chadwickpy

**Turn Retrosheet play-by-play files into data tables, with one `pip install`.**

[Retrosheet](https://www.retrosheet.org) publishes every play of every MLB game as text
files. They are compact but hard to read. The [Chadwick](https://github.com/chadwickbureau/chadwick)
tools are the standard way to turn them into tables a researcher can use. `chadwickpy` is
those same six tools, rewritten in pure Python, so you can install them anywhere Python runs:
no compiler, no C library, no dependencies.

<div class="grid cards" markdown>

-   :material-rocket-launch: **[Get started](getting-started.md)**

    Install, download a season, and write your first table in a few minutes.

-   :material-book-open-variant: **[Guides](guides/event-data.md)**

    The six tools, the columns they write, Python usage and worked recipes.

-   :material-console: **[Reference](reference/index.md)**

    Every option and field of every tool, generated from the tools themselves.

</div>

=== "Before (an event file)"

    ```text
    play,1,0,aybae001,12,CBCX,S9/F9S-
    play,1,0,abreb001,12,C11FBS,K
    play,1,0,huntt001,22,F1CBFB1X,8/F8LXD
    ```

=== "After (cwevent)"

    ```text
    "GAME_ID","INN_CT","BAT_HOME_ID","OUTS_CT","BAT_ID","PIT_ID","EVENT_TX","EVENT_CD"
    "NYA201004130",1,0,0,"aybae001","petta001","S9/F9S-",20
    "NYA201004130",1,0,0,"abreb001","petta001","K",3
    "NYA201004130",1,0,1,"huntt001","petta001","8/F8LXD",2
    ```

## Try it in a minute

```bash
pip install chadwickpy                  # or: uvx --from chadwickpy cwevent -h
curl -O https://www.retrosheet.org/events/2010seve.zip
unzip -q 2010seve.zip -d retro2010 && cd retro2010
cwevent -y 2010 -n -f 0,2,3,4,10,14,29,34 2010NYA.EVA > yankees_events.csv
```

That is every event (each pitch-ending play, steal, pickoff and so on) in the Yankees' 2010 home games, as a CSV file.
[Getting started](getting-started.md) explains each step.

## What you get

| Tool | One row per | Use it for |
|---|---|---|
| [`cwevent`](guides/event-data.md) | event (a play) | pitch-by-pitch and play-by-play analysis, run expectancy, batted balls |
| [`cwgame`](guides/games-and-players.md) | game | schedules, scores, parks, umpires, starting pitchers |
| [`cwdaily`](guides/games-and-players.md) | player per game | game logs: batting, pitching and fielding lines |
| [`cwsub`](guides/subs-and-comments.md) | substitution | pinch hitters, pitching changes, defensive swaps |
| [`cwcomment`](guides/subs-and-comments.md) | comment | scorer notes and ejections |
| [`cwbox`](guides/box-scores.md) | game | text, XML or SportsML box scores |

## Why use it

* **Same answers as Chadwick.** Its output was compared with the real tools on every season
  from 1910 to 2025: no differences, for inputs where the C tools behave in a defined way. [How it was checked](about/verification.md).
* **Installs anywhere.** Windows, macOS, Linux, a notebook, a CI job. Python 3.11 or newer.
* **Same commands.** `cwevent`, `cwgame`, `cwdaily`, `cwsub`, `cwcomment` and `cwbox`, with
  Chadwick's options, so existing tutorials and scripts work.
* **Usable from Python.** Import the parser and the row generators directly.
  See the [Python guide](guides/python-api.md).

## Is it for you?

See [who it is for](about/who-is-it-for.md) and how it compares with [other tools](about/alternatives.md).

## What to know first

* On one core it is **about 10 to 40 times slower** than the C tools, depending on the tool (a whole
  season takes 14 to 40 seconds). With several files it uses several cores by itself, which brings a
  season to a few seconds on a multi-core machine. See
  [compared with Chadwick](about/compared-with-chadwick.md) for the measured numbers.
* It reads the data files; it does not download them. Get them from
  [Retrosheet](https://www.retrosheet.org/game.htm) (see the credit notice on the
  [FAQ](about/faq.md)).
* It is a derivative of Chadwick and is licensed GPL-3.0-or-later, with credit to Chadwick.
