---
description: Worked chadwickpy recipes - build a whole season file, find home run leaders, load events into SQLite or pandas, filter by date or game, and handle errors.
---

# Recipes

All examples use the 2010 archive from [Getting started](../getting-started.md), run from
inside the unzipped folder.

## A whole season in one file

Each event file holds one team's home games. Give all of them at once:

```bash
cwevent -Q -y 2010 -n -f 0,2,3,4,10,14,29,34 2010*.EV? > season_2010.csv
```

`2010*.EV?` matches the American League (`.EVA`) and National League (`.EVN`) files. The header
is written once. On a typical machine this takes about 20 seconds for `cwevent` and about a minute for `cwdaily` over all 30 teams (see [speed](../about/compared-with-chadwick.md)).

## Home run leaders

`cwdaily` has one row per player per game, so season totals are sums:

```bash
cwdaily -Q -y 2010 -n -f 0,5,19 2010*.EV? > batting.csv
```

```python
import csv
from collections import Counter

hr = Counter()
with open("batting.csv", newline="") as f:
    for row in csv.DictReader(f):
        hr[row["PLAYER_ID"]] += int(row["B_HR"])

print(hr.most_common(3))
```

Output:

```text
[('bautj002', 54), ('pujoa001', 42), ('konep001', 39)]
```

José Bautista's 54 led the majors in 2010. The count matches the official total.

## SQL with SQLite (no extra install)

```python
import csv
import sqlite3

con = sqlite3.connect(":memory:")
with open("season_2010.csv", newline="") as f:
    reader = csv.reader(f)
    columns = next(reader)
    con.execute(f"create table ev ({', '.join(columns)})")
    con.executemany(f"insert into ev values ({','.join('?' * len(columns))})", reader)

# strikeouts by pitcher (EVENT_CD 3)
query = "select PIT_ID, count(*) k from ev where EVENT_CD = '3' group by 1 order by k desc limit 3"
print(con.execute(query).fetchall())
```

Output (Jered Weaver, Felix Hernandez and Tim Lincecum were the 2010 strikeout leaders):

```text
[('weavj003', 233), ('hernf002', 232), ('linct001', 231)]
```

Values are text; compare with quotes (`'3'`) or `cast(... as integer)`.

## pandas or DuckDB

```python
import pandas as pd

events = pd.read_csv("season_2010.csv")
```

DuckDB reads the file directly: `duckdb.sql("select * from 'season_2010.csv' limit 5")`.

## One game, or a range of dates

```bash
cwevent -Q -y 2010 -n -f 0,2,29 -i NYA201004130 2010NYA.EVA     # one game
cwevent -Q -y 2010 -n -f 0,2,29 -s 0601 -e 0630 2010NYA.EVA      # June only
```

## Quiet output in scripts

`-Q` turns off the progress lines Chadwick prints. Send errors to a file with
`2> errors.txt` so a bad line in an event file does not get lost.
