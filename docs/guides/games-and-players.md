---
description: Use chadwickpy's cwgame for one row per game (teams, park, weather, umpires, starting pitchers) and cwdaily for one row per player per game (batting, pitching and fielding lines).
---

# Games and players (`cwgame`, `cwdaily`)

## `cwgame`: one row per game

```bash
cwgame -y 2010 -n -f 0,1,7,8,10,11 -s 0501 -e 0503 2010NYA.EVA
```

Columns are chosen with `-f`, like `cwevent`. Run `cwgame -d` for the full list. Handy ones:

| `-f` | Meaning |
|---|---|
| 0 | game ID |
| 1 | date |
| 2 | game number (0 = not a doubleheader) |
| 3 | day of week |
| 4 | start time |
| 7, 8 | visiting and home team |
| 9 | game site (park) |
| 10, 11 | starting pitchers (visitor, home) |

`cwgame -d` lists everything it can write: umpires, attendance, weather, final score, hits,
errors, innings, winning, losing and saving pitchers, and both starting lineups.

## `cwdaily`: one row per player per game

```bash
cwdaily -y 2010 -n -f 0,4,5,15,19,21 2010NYA.EVA
```

Each row is one player's game: batting columns start `B_` (`B_AB`, `B_H`, `B_HR`...),
pitching `P_`, and fielding `F_<position>_`, one group per position (`F_SS_PO` is a shortstop's putouts). Default is all 154 columns
(`-f 0-153`).

| `-f` | Column |
|---|---|
| 0 | `GAME_ID` |
| 4 | `TEAM_ID` |
| 5 | `PLAYER_ID` |
| 15 | `B_H` hits |
| 19 | `B_HR` home runs |
| 21 | `B_RBI` |

Because each row is one game, season totals are sums over the rows: see the
[recipes](recipes.md). Games a player did not appear in have no row.
