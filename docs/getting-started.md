---
description: Install chadwickpy with pip, uv or pipx, download Retrosheet event files, and run cwevent for the first time. Includes real output and what each column means.
---

# Getting started

## 1. Install

Pick one. All give you the six commands.

=== "pip"

    ```bash
    pip install chadwickpy
    ```

=== "uv (installed tool)"

    ```bash
    uv tool install chadwickpy
    ```

=== "uv (no install, one-off)"

    ```bash
    uvx --from chadwickpy cwevent -h
    ```

=== "pipx"

    ```bash
    pipx install chadwickpy
    ```

Check it worked:

```bash
cwevent -h
chadwickpy cwevent -h     # same tool, always this package's copy
python -m chadwickpy cwevent -h
```

You should see `Chadwick expanded event descriptor, version 0.11.0` and the option list.
`chadwickpy` needs Python 3.11 or newer and nothing else.

## 2. Get Retrosheet data

The tools read Retrosheet *event files*. They are not part of this package. Download a
decade archive and unpack it:

```bash
curl -O https://www.retrosheet.org/events/2010seve.zip
unzip -q 2010seve.zip -d retro2010
cd retro2010
```

On Windows, `cmd.exe` does not expand `*`; chadwickpy does it for you, so `2010*.EV*` works there too.

Inside you will find one event file per team and season (`2010NYA.EVA`: the Yankees'
home games; `.EVN` for National League teams), a `TEAM2010` file and one roster file per
team (`NYA2010.ROS`). The tools look for `TEAM2010` and the roster files in the **folder you
run the command from** (as the real Chadwick does), so run them from inside this folder, as the
`cd` above does. Running from elsewhere gives `Can't find teamfile (team2010)`.

## 3. Run your first command

```bash
cwevent -y 2010 -n -f 0,2,3,4,10,14,29,34 2010NYA.EVA > yankees_events.csv
```

| Part | Meaning |
|---|---|
| `-y 2010` | the season, used to find `TEAM2010` and the roster files |
| `-n` | write the column names in the first row |
| `-f 0,2,3,4,10,14,29,34` | which columns to write (numbers from `cwevent -d`) |
| `2010NYA.EVA` | the event file to read |

The first lines of `yankees_events.csv`:

```text
"GAME_ID","INN_CT","BAT_HOME_ID","OUTS_CT","BAT_ID","PIT_ID","EVENT_TX","EVENT_CD"
"NYA201004130",1,0,0,"aybae001","petta001","S9/F9S-",20
"NYA201004130",1,0,0,"abreb001","petta001","K",3
"NYA201004130",1,0,1,"huntt001","petta001","8/F8LXD",2
```

Each row is one play: the game, the inning, who batted (`BAT_HOME_ID` 0 = visitors),
outs before the play, the batter and pitcher IDs, the play as Retrosheet writes it
(`EVENT_TX`) and a numeric code for it (`EVENT_CD`, 20 = single, 3 = strikeout,
2 = generic out, 23 = home run). Player IDs match Retrosheet's biographical files.

## 4. Use the result

The file is an ordinary CSV, so anything reads it:

```python
import csv

with open("yankees_events.csv", newline="") as f:
    rows = list(csv.DictReader(f))

print(len(rows), "events")  # 6433 events
```

With pandas: `pandas.read_csv("yankees_events.csv")`. More in the
[recipes](guides/recipes.md).

## Next

* Understand the columns: [event data guide](guides/event-data.md).
* Other tools: [games and players](guides/games-and-players.md),
  [substitutions and comments](guides/subs-and-comments.md),
  [box scores](guides/box-scores.md).
* Call it from Python: [Python guide](guides/python-api.md).
