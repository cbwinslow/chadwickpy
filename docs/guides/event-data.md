---
description: How to use cwevent in chadwickpy to turn Retrosheet play-by-play into one row per event, with the most useful columns, options, event codes and filters explained.
---

# Event data (`cwevent`)

`cwevent` writes **one row per event**: a plate appearance, a stolen base, a pickoff, a
substitution with no play, and so on. It is the richest of the six tools: 97 standard
columns plus 67 extended ones.

```bash
cwevent -y 2010 -n -f 0,2,3,4,10,14,29,34 2010NYA.EVA
```

## Choosing columns

* `-f LIST` picks standard columns by number, `-x LIST` adds extended ones (they come after).
  Lists are comma-separated and may use ranges: `-f 0-6,29,34`.
* `cwevent -d` prints every number and name. The [reference](../reference/cwevent.md) has the same list.
* With no `-f`, you get Chadwick's default set (`0-6,8-9,12-13,16-17,26-40,43-45,51,58-61`).
* `-n` writes the column names as a first row. Always use it unless you know the order.

### The columns you will use most

| `-f` | Column | Meaning |
|---|---|---|
| 0 | `GAME_ID` | Retrosheet game ID: home team, date, game number (`NYA201004130`) |
| 2 | `INN_CT` | inning |
| 3 | `BAT_HOME_ID` | 0 = visitors batting, 1 = home team batting |
| 4 | `OUTS_CT` | outs before the play |
| 5, 6 | `BALLS_CT`, `STRIKES_CT` | count before the play |
| 7 | `PITCH_SEQ_TX` | the pitch sequence as recorded |
| 8, 9 | `AWAY_SCORE_CT`, `HOME_SCORE_CT` | score before the play |
| 10 | `BAT_ID` | batter |
| 14 | `PIT_ID` | pitcher |
| 26-28 | `BASE1_RUN_ID`, `BASE2_RUN_ID`, `BASE3_RUN_ID` | runners on first, second and third |
| 29 | `EVENT_TX` | the play in Retrosheet notation |
| 34 | `EVENT_CD` | numeric event type (below) |
| 36 | `AB_FL` | counts as an at-bat |
| 37 | `H_CD` | hit value: 1 single, 2 double, 3 triple, 4 home run |
| 43 | `RBI_CT` | runs batted in on the play |

### `EVENT_CD` values

| Code | Event | Code | Event |
|---|---|---|---|
| 2 | generic out | 16 | hit by pitch |
| 3 | strikeout | 17 | interference |
| 4 | stolen base | 18 | error |
| 6 | caught stealing | 19 | fielder's choice |
| 8 | pickoff | 20 | single |
| 9 | wild pitch | 21 | double |
| 10 | passed ball | 22 | triple |
| 14 | walk | 23 | home run |
| 15 | intentional walk | | |

## Choosing games

| Option | Effect |
|---|---|
| `-i ID` | one game, e.g. `-i NYA201004130` |
| `-s 0501 -e 0531` | only games from May 1 to May 31 (`mmdd`) |
| `-y YEAR` | season whose `TEAMyyyy` and roster files to use |

Several files may be given at once; the header is written once:

```bash
cwevent -y 2010 -n -f 0,2,29 2010BOS.EVA 2010NYA.EVA
```

## Output format

Default is quoted, comma-separated text (`-a`). `-ft` writes fixed-width Fortran-style
output. `-q` suppresses the progress messages Chadwick prints to the screen (stderr), which
is useful in scripts.

## Good to know

* The first row of data is the first play, not a game header.
* Event files list only one team's home games (`2010NYA.EVA` has the Yankees at home).
  Combine all 30 files to get the whole league: `cwevent ... 2010*.EV?`.
* A column's exact meaning is Chadwick's. See its
  [documentation](https://chadwick.readthedocs.io/) for details.
