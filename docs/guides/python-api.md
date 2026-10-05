---
description: Call chadwickpy from Python instead of the command line - iterate event rows as dictionaries, read games, and load rosters, with working examples.
---

# Python API

Everything the command-line tools do is available as functions. The layout mirrors Chadwick:
`chadwickpy` has the `cwlib` pieces (parser, games, rosters, box scores) and
`chadwickpy.tools` the `cwtools` programs.

!!! note "Version 0.x"
    The command-line interface follows Chadwick and is stable. The Python functions are a
    faithful translation of Chadwick's C functions, but their signatures may still change
    before 1.0. Pin the version if you depend on them.

## Event rows

`event_rows` yields one dictionary per event, with every `cwevent` column (`-f 0-96 -x 0-66`).
Values are strings, as in the CSV.

```python
from pathlib import Path

from chadwickpy.tools.events import event_rows
from chadwickpy.tools.tools import read_rosters

folder = Path("retro2010")
league = read_rosters(
    (folder / "TEAM2010").read_bytes(),
    "2010",
    lambda name: (folder / name).read_bytes() if (folder / name).exists() else None,
)

rows = event_rows((folder / "2010NYA.EVA").read_bytes(), league)
homers = [r for r in rows if r["EVENT_CD"] == "23"]
print(len(homers), "home runs; first:", homers[0]["BAT_ID"], homers[0]["GAME_ID"])
# 223 home runs; first: johnn001 NYA201004130
```

The rosters supply batting and throwing hands. Pass `league=None` to skip them.

Options match the command line: `game_id="NYA201004130"` for one game, and
`first_date="0501", last_date="0531"` for a date range.

## Games

```python
from chadwickpy.game import read_games

for game in read_games((folder / "2010NYA.EVA").read_bytes()):
    print(game.game_id)
```

A `Game` holds the `info` records, the starters and every event, the same data Chadwick's
`CWGame` struct holds. Docstrings name the C function each Python function translates.

## The other tools

| Tool | Module |
|---|---|
| `cwevent` | `chadwickpy.tools.events` |
| `cwgame` | `chadwickpy.tools.cwgame` |
| `cwdaily` | `chadwickpy.tools.daily` |
| `cwsub` | `chadwickpy.tools.sub` |
| `cwcomment` | `chadwickpy.tools.comment` |
| `cwbox` | `chadwickpy.tools.cwbox` |

See the [library reference](../reference/library.md).
