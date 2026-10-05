---
description: Use chadwickpy's cwsub to list every substitution (pinch hitters, pitching changes) and cwcomment to extract scorer comments and ejections from Retrosheet event files.
---

# Substitutions and comments (`cwsub`, `cwcomment`)

## `cwsub`: one row per substitution

```bash
cwsub -y 2007 -n 2007TST.EVA
```

Sample (default columns):

```text
"GAME_ID","INN_CT","BAT_HOME_ID","SUB_ID","SUB_HOME_ID","SUB_LINEUP_ID","SUB_FLD_CD","REMOVED_ID",...
"TOR200705310",6,0,"terrl001",0,1,11,"erstd001",8,36,...
```

`SUB_ID` is the player who came in, `REMOVED_ID` the one who left, `SUB_FLD_CD` the
position (11 = pinch hitter, 12 = pinch runner, 1 = pitcher...) and the count and pitch
columns say when it happened. `cwsub -d` lists the fields; `-f` selects them.

## `cwcomment`: scorer notes

```bash
cwcomment -y 2007 -n 2007TST.EVA
```

Each row is one comment line from the file (for example an injury note), with the game, the
event it follows and, for ejections, who was ejected and why.

```text
"GAME_ID","EVENT_ID","COMMENT_TX","EJECT_PERSON_ID",...
"TOR200705310",36,"$Erstad hurt ankle swinging and missing at 2-1 pitch. Popping sound heard from dugout",...
```

Both tools take the same filters as the others: `-i`, `-s`, `-e`, `-y`, `-q`, `-n`.
